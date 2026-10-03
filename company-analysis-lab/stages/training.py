"""Analyst Training Mode: the end-of-stage quiz and the spaced-repetition review page."""

from __future__ import annotations

import secrets

import streamlit as st

from lab import data as D
from lab import questions as Q
from lab import storage, ui
from lab import visualization as viz
from stages.common import AppContext

SELF_OPTIONS = ["Covered it", "Partially", "Missed it"]
SELF_OUTCOME = {"Covered it": "correct", "Partially": "partial", "Missed it": "wrong"}


def quiz_context(app: AppContext, stage: int | None = None) -> Q.QuizContext:
    ctx = Q.QuizContext(app.profile, app.values, app.currency, app.progress)
    peer_id = app.progress.get("stages", {}).get("8", {}).get("answers", {}).get("peer_id")
    if peer_id:
        try:
            ctx.peer_profile = D.load_profile(peer_id)
            ctx.peer_values = D.load_working(peer_id)[0]
        except (OSError, ValueError, KeyError):
            pass
    return ctx


def new_quiz(questions: list[Q.Question]) -> dict:
    return {"id": secrets.token_hex(4), "questions": [q.to_dict() for q in questions], "responses": {}, "results": {}, "self": {}, "graded": False, "finished": False, "created": storage.now_iso()}


def _fmt_answer(q: Q.Question, value) -> str:
    if value is None:
        return "–"
    if q.kind == "mc":
        return q.options[int(value)]
    if q.kind == "numeric":
        return f"{float(value):,.2f} {q.unit}".strip()
    return str(value)


def render_quiz(quiz: dict, key_prefix: str, learner: dict, on_save, source: str) -> bool:
    """Render a quiz (form → graded results → self-assessment → recorded). Returns True when finished."""
    questions = [Q.Question.from_dict(d) for d in quiz["questions"]]

    if not quiz["graded"]:
        with st.form(f"{key_prefix}-form"):
            for i, q in enumerate(questions):
                st.markdown(ui.level_badge(q.level, Q.LEVEL_NAMES[q.level], q.review), unsafe_allow_html=True)
                st.markdown(f"**Q{i + 1}.** {q.prompt}")
                k = f"{key_prefix}-a{i}"
                if q.kind == "mc":
                    st.radio("Answer", q.options, index=None, key=k, label_visibility="collapsed")
                elif q.kind == "numeric":
                    st.number_input(f"Your answer{f' ({q.unit})' if q.unit else ''}", value=None, format="%.4f", step=None, key=k)
                else:
                    st.text_area("Your answer", key=k, height=110, placeholder="Write 2–5 sentences. You will compare it with a model answer.")
                st.write("")
            submitted = st.form_submit_button("Submit answers", type="primary", icon=":material/send:")
        if submitted:
            responses, missing = {}, []
            for i, q in enumerate(questions):
                raw = st.session_state.get(f"{key_prefix}-a{i}")
                if q.kind == "mc":
                    responses[str(i)] = q.options.index(raw) if raw is not None else None
                elif q.kind == "numeric":
                    responses[str(i)] = raw
                else:
                    responses[str(i)] = (raw or "").strip()
                if responses[str(i)] in (None, "") or (q.kind == "text" and len(responses[str(i)].split()) < 5):
                    missing.append(i + 1)
            if missing:
                st.warning(f"Answer every question first (missing or too short: Q{', Q'.join(map(str, missing))}). Guessing is fine — that's how the app learns what to review.")
                return False
            quiz["responses"] = responses
            quiz["results"] = {str(i): Q.grade(q, responses[str(i)]) for i, q in enumerate(questions)}
            quiz["graded"] = True
            on_save()
            st.rerun()
        return False

    auto = [(i, q) for i, q in enumerate(questions) if q.kind != "text"]
    n_right = sum(1 for i, _ in auto if quiz["results"].get(str(i)))
    st.markdown(f"**Score on auto-graded questions: {n_right} / {len(auto)}**")
    for i, q in enumerate(questions):
        with st.container(border=True):
            st.markdown(ui.level_badge(q.level, Q.LEVEL_NAMES[q.level], q.review) + f" <span class='al-small'>Concept: {ui.esc(Q.concept_label(q.concept))}</span>", unsafe_allow_html=True)
            st.markdown(f"**Q{i + 1}.** {q.prompt}")
            resp = quiz["responses"].get(str(i))
            if q.kind == "text":
                st.markdown(f"*Your answer:* {ui.esc(resp)}", unsafe_allow_html=True)
                st.info(f"**Model answer:** {q.model_answer}", icon=":material/lightbulb:")
                if quiz["finished"]:
                    st.caption(f"Your self-assessment: {quiz['self'].get(str(i), '–')}")
                else:
                    st.radio("How well did your answer cover the model answer?", SELF_OPTIONS, index=None, horizontal=True, key=f"{key_prefix}-self{i}")
            else:
                ok = quiz["results"].get(str(i))
                verdict = "✅ Correct" if ok else "❌ Not quite"
                st.markdown(f"{verdict} — your answer: **{ui.esc(_fmt_answer(q, resp))}**", unsafe_allow_html=True)
                if not ok:
                    st.markdown(f"Correct answer: **{ui.esc(_fmt_answer(q, q.answer))}**", unsafe_allow_html=True)
                if q.explanation:
                    st.caption(q.explanation)

    if quiz["finished"]:
        return True

    selfs = {str(i): st.session_state.get(f"{key_prefix}-self{i}") for i, q in enumerate(questions) if q.kind == "text"}
    ready = all(v is not None for v in selfs.values())
    if st.button("Record results", type="primary", disabled=not ready, key=f"{key_prefix}-record", icon=":material/save:"):
        quiz["self"] = selfs
        for i, q in enumerate(questions):
            if q.kind == "text":
                outcome = SELF_OUTCOME[selfs[str(i)]]
            else:
                outcome = "correct" if quiz["results"].get(str(i)) else "wrong"
            Q.record(learner, q.concept, outcome)
        learner["quiz_counter"] = learner.get("quiz_counter", 0) + 1
        learner.setdefault("history", []).append({"when": storage.now_iso(), "source": source, "score": n_right, "of": len(auto)})
        quiz["finished"] = True
        storage.save_learner(learner)
        on_save()
        st.rerun()
    if not ready:
        st.caption("Rate each free-text answer against the model answer, then record your results.")
    return False


def render_stage_quiz(app: AppContext, stage: int) -> None:
    state = app.state(stage)
    st.subheader("Analyst Training — check your understanding")
    st.caption("Five questions from Level 1 (identify) to Level 5 (analyst reasoning). Concepts you miss come back in later quizzes (spaced repetition).")
    quiz = state.get("quiz")
    if not quiz:
        qs = Q.build_quiz(stage, quiz_context(app, stage), app.learner, seed=secrets.randbits(32))
        quiz = state["quiz"] = new_quiz(qs)
        app.save()
    finished = render_quiz(quiz, f"quiz-{stage}-{quiz['id']}", app.learner, app.save, source=f"{app.company_id} stage {stage}")
    if finished:
        if not state.get("quiz_completed_once"):
            state["quiz_completed_once"] = True
            app.save()
            st.rerun()
        if st.button("Practise with a new set of questions", key=f"quiz-{stage}-again", icon=":material/refresh:"):
            state["quiz"] = None
            app.save()
            st.rerun()


def render_review(app: AppContext) -> None:
    ui.header(app.profile, "Analyst Training · Spaced repetition", "Concept review", "Concepts you answered wrongly come back here until you master them (Leitner boxes 1→5).",
              [f"Quizzes taken: {app.learner.get('quiz_counter', 0)}", f"Concepts tracked: {len(app.learner.get('concepts', {}))}"])
    table = Q.concept_table(app.learner)
    if table.empty:
        st.info("No quiz results yet. Complete a stage with Analyst Training Mode switched on.", icon=":material/school:")
        return
    due = Q.due_concepts(app.learner)
    c1, c2, c3 = st.columns(3)
    c1.metric("Due for review", len(due), border=True)
    c2.metric("Needs review", int((table["Status"] == "Needs review").sum()), border=True)
    c3.metric("Mastered", int((table["Status"] == "Mastered").sum()), border=True)

    weak = table[table["Attempts"] > 0].head(12)
    ui.plotly(viz.value_bars([(r["Concept"], float(r["Accuracy %"])) for _, r in weak.iterrows()], "Accuracy by concept (weakest first)", "% correct"), key="review-acc")
    ui.table_view(table.drop(columns=["_key"]), "All tracked concepts", hide_index=True, column_config={"Accuracy %": st.column_config.ProgressColumn("Accuracy %", min_value=0, max_value=100, format="%.0f%%")})

    st.subheader("Review session")
    session = app.learner.get("review_session")
    if session and not session.get("finished"):
        render_quiz(session, f"review-{session['id']}", app.learner, lambda: storage.save_learner(app.learner), source="review")
        return
    if session and session.get("finished"):
        render_quiz(session, f"review-{session['id']}", app.learner, lambda: storage.save_learner(app.learner), source="review")
    label = "Start a review session" if due else "Practise my weakest concepts"
    if st.button(label, type="primary", icon=":material/replay:", key="review-start"):
        # every tracked concept has been met before, so any stage's template may test it
        qs = Q.build_review(quiz_context(app), app.learner, n=5, seed=secrets.randbits(32))
        if not qs:
            st.info("Nothing to review yet.")
            return
        app.learner["review_session"] = new_quiz(qs)
        storage.save_learner(app.learner)
        st.rerun()
