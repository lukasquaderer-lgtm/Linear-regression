import React, { useEffect, useState } from "react";
import * as Q from "../lib/questions.js";
import * as CA from "../lib/ca.js";
import { Btn, Callout, Checklist, Choice, NumberField, TextArea, Table, Metric, PageHeader } from "./ui.jsx";
import { Chart, C } from "./charts.jsx";

const SELF = ["Covered it", "Partially", "Missed it"];
const SELF_OUTCOME = { "Covered it": "correct", Partially: "partial", "Missed it": "wrong" };

export function quizContext(app) {
  const peerId = app.doc.stages?.[8]?.answers?.peerId;
  const peer = peerId ? app.companies.find((c) => c.profile.id === peerId) : null;
  return {
    profile: app.profile,
    values: app.ds,
    currency: app.currency,
    name: app.profile.short_name,
    sector: app.profile.sector,
    peerProfile: peer?.profile || null,
    peerValues: peer ? app.datasetFor(peerId) : null,
  };
}

export const newQuiz = (questions) => ({ id: Math.random().toString(36).slice(2, 10), questions, responses: {}, results: {}, self: {}, graded: false, finished: false, created: new Date().toISOString() });

const fmtAnswer = (q, v) => {
  if (v === null || v === undefined || v === "") return "–";
  if (q.kind === "mc") return q.options[+v];
  if (q.kind === "numeric") return `${(+v).toLocaleString("en-US", { maximumFractionDigits: 2 })} ${q.unit || ""}`.trim();
  return String(v);
};

function LevelBadge({ q }) {
  return (
    <div className="q-badges">
      <span className="badge">Level {q.level} · {Q.LEVEL_NAMES[q.level]}</span>
      {q.review && <span className="badge badge-warn">Spaced-repetition review</span>}
      <span className="muted small">Concept: {Q.conceptLabel(q.concept)}</span>
    </div>
  );
}

/** A quiz: answer → graded results → self-assessment → recorded. */
export function Quiz({ quiz, onChange, onRecord }) {
  const [resp, setResp] = useState(quiz.responses || {});
  const [self, setSelf] = useState(quiz.self || {});
  const [warn, setWarn] = useState(null);
  const qs = quiz.questions;

  if (!quiz.graded) {
    const submit = () => {
      const missing = qs.map((q, i) => (resp[i] === undefined || resp[i] === null || resp[i] === "" || (q.kind === "text" && String(resp[i]).split(/\s+/).filter(Boolean).length < 5) ? i + 1 : null)).filter(Boolean);
      if (missing.length) return setWarn(`Answer every question first (missing or too short: Q${missing.join(", Q")}). Guessing is fine — that is how the app learns what to review.`);
      const results = Object.fromEntries(qs.map((q, i) => [i, Q.grade(q, resp[i])]));
      onChange({ ...quiz, responses: resp, results, graded: true });
    };
    return (
      <div className="quiz">
        {qs.map((q, i) => (
          <div key={i} className="q">
            <LevelBadge q={q} />
            <p className="q-prompt"><strong>Q{i + 1}.</strong> {q.prompt}</p>
            {q.kind === "mc" && <Choice name={`q-${quiz.id}-${i}`} vertical options={q.options.map((o, j) => ({ value: j, label: o }))} value={resp[i]} onChange={(v) => setResp({ ...resp, [i]: v })} />}
            {q.kind === "numeric" && <NumberField id={`q-${quiz.id}-${i}`} label={`Your answer${q.unit ? ` (${q.unit})` : ""}`} value={resp[i] ?? null} onChange={(v) => setResp({ ...resp, [i]: v })} />}
            {q.kind === "text" && <TextArea id={`q-${quiz.id}-${i}`} label="Your answer" rows={3} placeholder="Write 2–5 sentences. You will compare it with a model answer." value={resp[i] || ""} onChange={(v) => setResp({ ...resp, [i]: v })} />}
          </div>
        ))}
        {warn && <Callout tone="warn">{warn}</Callout>}
        <Btn kind="primary" onClick={submit}>Submit answers</Btn>
      </div>
    );
  }

  const auto = qs.map((q, i) => [q, i]).filter(([q]) => q.kind !== "text");
  const right = auto.filter(([, i]) => quiz.results[i]).length;
  const textIdx = qs.map((q, i) => (q.kind === "text" ? i : null)).filter((i) => i !== null);
  const ready = textIdx.every((i) => self[i]);
  return (
    <div className="quiz">
      <p className="score">Score on auto-graded questions: <strong>{right} / {auto.length}</strong></p>
      {qs.map((q, i) => (
        <div key={i} className={`q graded ${q.kind === "text" ? "" : quiz.results[i] ? "right" : "wrong"}`}>
          <LevelBadge q={q} />
          <p className="q-prompt"><strong>Q{i + 1}.</strong> {q.prompt}</p>
          {q.kind === "text" ? (
            <>
              <p><em>Your answer:</em> {quiz.responses[i]}</p>
              <Callout tone="info" title="Model answer">{q.modelAnswer}</Callout>
              {quiz.finished ? (
                <p className="muted small">Your self-assessment: {quiz.self?.[i] || "–"}</p>
              ) : (
                <Choice label="How well did your answer cover the model answer?" options={SELF} value={self[i]} onChange={(v) => setSelf({ ...self, [i]: v })} />
              )}
            </>
          ) : (
            <>
              <p>
                <span className={quiz.results[i] ? "verdict ok" : "verdict bad"}>{quiz.results[i] ? "Correct" : "Not quite"}</span> — your answer: <strong>{fmtAnswer(q, quiz.responses[i])}</strong>
              </p>
              {!quiz.results[i] && <p>Correct answer: <strong>{fmtAnswer(q, q.answer)}</strong></p>}
              {q.explanation && <p className="muted small">{q.explanation}</p>}
            </>
          )}
        </div>
      ))}
      {!quiz.finished && (
        <>
          {!ready && <p className="muted small">Rate each free-text answer against the model answer, then record your results.</p>}
          <Btn kind="primary" disabled={!ready} onClick={() => onRecord({ ...quiz, self }, right, auto.length)}>Record results</Btn>
        </>
      )}
    </div>
  );
}

function recordQuiz(learner, quiz, source, right, of) {
  quiz.questions.forEach((q, i) => {
    const outcome = q.kind === "text" ? SELF_OUTCOME[quiz.self[i]] : quiz.results[i] ? "correct" : "wrong";
    Q.record(learner, q.concept, outcome);
  });
  learner.quizCounter = (learner.quizCounter || 0) + 1;
  learner.history = [...(learner.history || []), { when: new Date().toISOString(), source, score: right, of }];
}

export function StageQuiz({ app, n }) {
  const quiz = app.doc.stages?.[n]?.quiz;
  useEffect(() => {
    if (!quiz) {
      const qs = Q.buildQuiz(n, quizContext(app), app.learner, (Math.random() * 2 ** 31) | 0);
      app.update((d) => ((d.stages[n] ||= {}).quiz = newQuiz(qs)));
    }
  }, [quiz]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!quiz) return null;
  return (
    <section className="section quiz-section">
      <div className="section-head">
        <h2>Analyst Training — check your understanding</h2>
      </div>
      <p className="muted">Five questions from Level 1 (identify) to Level 5 (analyst reasoning). Concepts you miss come back in later quizzes (spaced repetition).</p>
      <Quiz
        key={quiz.id}
        quiz={quiz}
        onChange={(q) => app.update((d) => (d.stages[n].quiz = q))}
        onRecord={(q, right, of) => {
          app.updateLearner((l) => recordQuiz(l, q, `${app.profile.id} stage ${n}`, right, of));
          app.update((d) => {
            d.stages[n].quiz = { ...q, finished: true };
            d.stages[n].quizCompletedOnce = true;
          });
        }}
      />
      {quiz.finished && (
        <Btn onClick={() => app.update((d) => (d.stages[n].quiz = null))}>Practise with a new set of questions</Btn>
      )}
    </section>
  );
}

export function StageFooter({ app, n, criteria }) {
  const s = app.doc.stages?.[n] || {};
  const done = criteria.every(([, ok]) => ok);
  const passed = CA.stagePassed(app.doc, n, app.training);
  const next = CA.STAGES[n];
  return (
    <div className="stage-foot">
      <section className="section">
        <div className="section-head"><h2>Stage checklist</h2></div>
        <Checklist items={criteria} />
        {!s.completed && (
          <>
            <Btn kind="primary" id={`complete-${n}`} disabled={!done} onClick={() => app.update((d) => {
              const st = (d.stages[n] ||= {});
              st.completed = true;
              st.completedAt = new Date().toISOString();
            })}>Complete stage</Btn>
            {!done && <p className="muted small">Finish every item above to complete the stage.</p>}
          </>
        )}
        {s.completed && <Callout tone="success">Stage {n} completed.</Callout>}
      </section>
      {s.completed && app.training && <StageQuiz app={app} n={n} />}
      {s.completed && n < 10 && passed && (
        <Btn kind="primary" icon="arrow" id={`next-${n}`} onClick={() => app.go(n + 1)}>Continue to Stage {n + 1}: {next.en}</Btn>
      )}
      {s.completed && n < 10 && !passed && app.training && <Callout tone="info">Finish the Analyst Training quiz above to unlock the next stage.</Callout>}
    </div>
  );
}

// -------------------------------------------------------------------- review page

export function Review({ app }) {
  const L = app.learner;
  const table = Q.conceptTable(L);
  const due = Q.dueConcepts(L);
  const session = L.reviewSession;
  const start = () => {
    const qs = Q.buildReview(quizContext(app), L, 5, (Math.random() * 2 ** 31) | 0);
    if (!qs.length) return;
    app.updateLearner((l) => (l.reviewSession = newQuiz(qs)));
  };
  return (
    <div className="page">
      <PageHeader kicker="Analyst Training · Spaced repetition" title="Concept review" sub="Concepts you answered wrongly come back here until you master them (Leitner boxes 1 → 5)." chips={[`Quizzes taken: ${L.quizCounter || 0}`, `Concepts tracked: ${Object.keys(L.concepts || {}).length}`]} />
      {!table.length ? (
        <Callout tone="info">No quiz results yet. Complete a stage with Analyst Training Mode switched on, then come back here.</Callout>
      ) : (
        <>
          <div className="metrics">
            <Metric label="Due for review" value={due.length} />
            <Metric label="Needs review" value={table.filter((r) => r.status === "Needs review").length} />
            <Metric label="Mastered" value={table.filter((r) => r.status === "Mastered").length} />
          </div>
          <Chart spec={C.bars(table.filter((r) => r.attempts).slice(0, 12).map((r) => [r.concept, r.accuracy ?? 0]), "Accuracy by concept (weakest first)", "% correct")} label="Accuracy by concept" />
          <Table
            columns={[
              { key: "concept", label: "Concept" },
              { key: "attempts", label: "Attempts", num: true },
              { key: "wrong", label: "Wrong", num: true },
              { key: "accuracy", label: "Accuracy", num: true, render: (r) => (r.accuracy === null ? "–" : `${r.accuracy.toFixed(0)} %`) },
              { key: "box", label: "Box (1–5)", num: true },
              { key: "status", label: "Status", render: (r) => <span className={`badge ${r.status === "Mastered" ? "badge-ok" : r.status === "Needs review" ? "badge-warn" : ""}`}>{r.status}</span> },
            ]}
            rows={table.map((r) => ({ ...r, _key: r.key }))}
          />
          <section className="section">
            <div className="section-head"><h2>Review session</h2></div>
            {session && (
              <Quiz
                key={session.id}
                quiz={session}
                onChange={(q) => app.updateLearner((l) => (l.reviewSession = q))}
                onRecord={(q, right, of) => app.updateLearner((l) => {
                  recordQuiz(l, q, "review", right, of);
                  l.reviewSession = { ...q, finished: true };
                })}
              />
            )}
            {(!session || session.finished) && <Btn kind="primary" id="review-start" onClick={start}>{due.length ? "Start a review session" : "Practise my weakest concepts"}</Btn>}
          </section>
        </>
      )}
    </div>
  );
}
