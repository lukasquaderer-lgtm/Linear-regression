"""End-to-end tests of the Streamlit app with streamlit.testing (no browser needed)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from lab import storage

APP = str(Path(__file__).resolve().parent.parent / "app.py")
COMPANIES = ["ubs", "llb", "gkb", "swiss_life", "swiss_re", "prismalife", "roche", "novartis", "hilti"]


def run_app():
    at = AppTest.from_file(APP, default_timeout=90)
    at.run()
    assert not at.exception, at.exception
    return at


def test_starts_on_stage_1_with_later_stages_locked():
    at = run_app()
    nav = {b.key: b for b in at.button if b.key and b.key.startswith("nav-")}
    assert not nav["nav-1"].disabled
    assert all(nav[f"nav-{i}"].disabled for i in range(2, 11))


@pytest.mark.parametrize("company", COMPANIES)
def test_every_stage_renders_for_every_company(company, monkeypatch):
    monkeypatch.setenv("ANALYST_LAB_UNLOCK_ALL", "1")
    learner = storage.empty_learner()
    learner["settings"]["last_company"] = company
    storage.save_learner(learner)
    at = run_app()
    for i in range(1, 11):
        at.button(key=f"nav-{i}").click().run()
        assert not at.exception, f"{company} stage {i}: {at.exception}"
    at.button(key="nav-review").click().run()
    assert not at.exception


def test_stage1_quiz_gates_stage2():
    at = run_app()
    txt = "The bank earns fees from wealthy private clients and interest on mortgages in Liechtenstein and Switzerland."
    for k in ["what_it_does", "how_money", "segments", "customers", "markets", "advantages", "threats"]:
        at.text_area(key=f"s1-{k}").input(txt)
    at.text_area(key="s1-summary").input(
        "LLB is the largest bank in Liechtenstein. It earns fees and interest income. Its clients are private and corporate clients. It operates in Liechtenstein, Switzerland and Austria."
    )
    next(b for b in at.button if b.label == "Submit my answers").click().run()
    assert any("Compare with the analyst reference" in s.value for s in at.subheader)
    at.button(key="complete-1").click().run()
    assert at.button(key="nav-2").disabled, "training mode: quiz must be finished first"
    for r in at.radio:
        if r.key and r.key.startswith("quiz-1-"):
            r.set_value(r.options[0])
    for n in at.number_input:
        if n.key and n.key.startswith("quiz-1-"):
            n.set_value(1.0)
    for t in at.text_area:
        if t.key and t.key.startswith("quiz-1-"):
            t.input("Scale is durable; I would track net new money and the fee margin over five years.")
    next(b for b in at.button if b.label == "Submit answers").click().run()
    for r in at.radio:
        if r.key and "-self" in r.key:
            r.set_value("Covered it")
    at.run()
    next(b for b in at.button if b.label == "Record results").click().run()
    assert not at.exception
    assert not at.button(key="nav-2").disabled
    learner = storage.load_learner()
    assert learner["quiz_counter"] == 1 and learner["concepts"]


def test_training_mode_off_skips_quiz():
    learner = storage.empty_learner()
    learner["settings"]["training_mode"] = False
    learner["settings"]["last_company"] = "llb"
    storage.save_learner(learner)
    progress = storage.load_progress("llb")
    storage.stage_state(progress, 1)["completed"] = True
    storage.save_progress(progress)
    at = run_app()
    assert not at.button(key="nav-2").disabled


def test_export_import_roundtrip():
    progress = storage.load_progress("ubs")
    storage.stage_state(progress, 1)["answers"]["summary"] = "hello"
    storage.save_progress(progress)
    blob = storage.export_bundle("ubs")
    storage.reset_company("ubs")
    assert storage.load_progress("ubs")["stages"] == {}
    assert storage.import_bundle(blob) == "ubs"
    assert storage.load_progress("ubs")["stages"]["1"]["answers"]["summary"] == "hello"
    with pytest.raises(ValueError):
        storage.import_bundle("{}")


def test_review_page_runs_a_spaced_repetition_session():
    from lab import questions as Q

    learner = storage.empty_learner()
    Q.record(learner, "dupont", "wrong")
    Q.record(learner, "growth_cagr", "wrong")
    learner["quiz_counter"] = 1
    storage.save_learner(learner)
    at = run_app()
    at.button(key="nav-review").click().run()
    assert not at.exception
    assert any(m.label == "Due for review" and m.value == "2" for m in at.metric)
    at.button(key="review-start").click().run()
    assert not at.exception
    for r in at.radio:
        if r.key and r.key.startswith("review-"):
            r.set_value(r.options[0])
    for n in at.number_input:
        if n.key and n.key.startswith("review-"):
            n.set_value(10.8)
    for t in at.text_area:
        if t.key and t.key.startswith("review-"):
            t.input("Leverage explains it because ROE equals ROA times leverage here.")
    next(b for b in at.button if b.label == "Submit answers").click().run()
    for r in at.radio:
        if r.key and "-self" in r.key:
            r.set_value("Partially")
    at.run()
    next(b for b in at.button if b.label == "Record results").click().run()
    assert not at.exception
    after = storage.load_learner()
    assert after["quiz_counter"] == 2
    assert after["concepts"]["dupont"]["attempts"] >= 2
