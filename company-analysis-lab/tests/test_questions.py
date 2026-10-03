import pytest

from lab import data as D
from lab import questions as Q
from lab import storage


@pytest.mark.parametrize("company", ["ubs", "llb", "swiss_life", "swiss_re", "prismalife"])
def test_every_stage_builds_five_progressive_questions(company):
    p = D.load_profile(company)
    v, _ = D.load_starter(company)
    ctx = Q.QuizContext(p, v, p["currency"])
    learner = storage.empty_learner()
    for stage in range(1, 11):
        qs = Q.build_quiz(stage, ctx, learner, seed=stage)
        assert [q.level for q in qs] == [1, 2, 3, 4, 5]
        for q in qs:
            assert q.prompt and q.concept
            if q.kind == "mc":
                assert 0 <= q.answer < len(q.options) and len(set(q.options)) == len(q.options)
            if q.kind == "numeric":
                assert q.answer == q.answer  # not NaN
            if q.kind == "text":
                assert q.model_answer


def test_grading():
    mc = Q.Question("x", 1, 1, "c", "mc", "?", ["a", "b"], 1)
    assert Q.grade(mc, 1) and not Q.grade(mc, 0)
    num = Q.Question("y", 1, 2, "c", "numeric", "?", answer=10.0, abs_tol=0.1)
    assert Q.grade(num, 10.05) and not Q.grade(num, 11) and not Q.grade(num, None)
    assert Q.grade(Q.Question("z", 1, 5, "c", "text", "?"), "anything") is None


def test_spaced_repetition_brings_back_wrong_concepts():
    learner = storage.empty_learner()
    Q.record(learner, "dupont", "wrong")
    Q.record(learner, "growth_cagr", "correct")
    assert Q.due_concepts(learner) == []  # due after one more quiz
    learner["quiz_counter"] = 1
    assert Q.due_concepts(learner) == ["dupont"]
    Q.record(learner, "dupont", "correct")
    Q.record(learner, "dupont", "correct")
    Q.record(learner, "dupont", "correct")
    learner["quiz_counter"] = 50
    assert "dupont" not in Q.due_concepts(learner)  # mastered (box ≥ 4)
    table = Q.concept_table(learner)
    assert set(table["_key"]) == {"dupont", "growth_cagr"}


def test_review_questions_replace_easy_levels():
    p = D.load_profile("ubs")
    v, _ = D.load_starter("ubs")
    learner = storage.empty_learner()
    Q.record(learner, "dupont", "wrong")
    learner["quiz_counter"] = 1
    qs = Q.build_quiz(6, Q.QuizContext(p, v, "USD"), learner, seed=3)
    assert len(qs) == 5
    assert qs[0].review and qs[0].concept == "dupont"
    review = Q.build_review(Q.QuizContext(p, v, "USD"), learner, n=3, seed=1)
    assert review and all(q.review for q in review)


def test_question_roundtrip():
    q = Q.Question("x", 1, 1, "c", "mc", "?", ["a", "b"], 0, explanation="e")
    assert Q.Question.from_dict(q.to_dict()) == q
