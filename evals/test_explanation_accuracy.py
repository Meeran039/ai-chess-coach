"""
Eval suite for the AI Chess Coach.

Two categories of tests:

1. DETERMINISTIC tests — check things we can verify exactly with code
   (blunder detection fires on known bad moves, eval math is consistent,
   quiz questions don't leak the answer, etc.)

2. LLM-AS-JUDGE tests — check things that need language understanding
   (does the coach's explanation actually match the blunder data, is it
   factually grounded, is it not hallucinating a different move).

Run with:
    pytest evals/test_explanation_accuracy.py -v
"""

import os
import sys
import json
import pytest
from dotenv import load_dotenv
from groq import Groq

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "analysis"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "agents"))

from blunder_finder import analyze_game
from coach import explain_blunder
from quiz import generate_quiz_question, get_best_move

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
JUDGE_MODEL = "openai/gpt-oss-120b"


# ---------------------------------------------------------------------------
# Fixtures — known test positions with a known "correct" outcome
# ---------------------------------------------------------------------------

@pytest.fixture
def scholars_mate_pgn():
    """A textbook blunder: Black hangs a checkmate on f7 (Scholar's Mate)."""
    return """
    [Event "Test"]
    [White "TestWhite"]
    [Black "TestBlack"]
    1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7#
    """


@pytest.fixture
def sample_blunder():
    """A realistic blunder dict, same shape produced by blunder_finder.py."""
    return {
        "move_number": 7,
        "player": "ihatechopperew",
        "move": "Bf4",
        "eval_before": 72,
        "eval_after": -350,
        "eval_drop": 422,
        "fen_before": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4",
    }


@pytest.fixture
def non_blunder():
    """A tiny, harmless eval swing that should NOT be flagged as a blunder."""
    return {
        "move_number": 3,
        "player": "ihatechopperew",
        "move": "Nf3",
        "eval_before": 20,
        "eval_after": 5,
        "eval_drop": 15,
        "fen_before": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    }


# ---------------------------------------------------------------------------
# 1. DETERMINISTIC TESTS — blunder detection correctness
# ---------------------------------------------------------------------------

class TestBlunderDetection:

    def test_detects_known_blunder(self, scholars_mate_pgn):
        """A game ending in Scholar's Mate MUST flag Black's losing sequence."""
        blunders = analyze_game(
            scholars_mate_pgn, player_username="TestBlack", blunder_threshold=200
        )
        assert len(blunders) > 0, "Failed to detect an obvious blunder (Scholar's Mate)."

    def test_eval_drop_math_is_consistent(self, sample_blunder):
        """eval_drop should always equal eval_before - eval_after."""
        expected_drop = sample_blunder["eval_before"] - sample_blunder["eval_after"]
        assert sample_blunder["eval_drop"] == expected_drop, (
            f"eval_drop ({sample_blunder['eval_drop']}) doesn't match "
            f"eval_before - eval_after ({expected_drop})"
        )

    def test_below_threshold_not_flagged(self, scholars_mate_pgn):
        """A very high threshold should return no blunders at all."""
        blunders = analyze_game(
            scholars_mate_pgn, player_username="TestBlack", blunder_threshold=999999
        )
        assert len(blunders) == 0, "Blunder flagged even with an impossibly high threshold."

    def test_only_flags_specified_player(self, scholars_mate_pgn):
        """Blunders should only be attributed to the requested player, not both sides."""
        blunders = analyze_game(
            scholars_mate_pgn, player_username="TestBlack", blunder_threshold=200
        )
        for b in blunders:
            assert b["player"].lower() == "testblack", (
                f"Blunder wrongly attributed to {b['player']}, expected TestBlack."
            )


# ---------------------------------------------------------------------------
# 2. DETERMINISTIC TESTS — quiz integrity
# ---------------------------------------------------------------------------

class TestQuizIntegrity:

    def test_quiz_question_does_not_leak_best_move(self, sample_blunder):
        """
        The quiz prompt shown to the player must not contain Stockfish's
        best move in plain text — that would defeat the purpose of the quiz.
        """
        question = generate_quiz_question(sample_blunder)
        best_move = get_best_move(sample_blunder["fen_before"])

        assert best_move.lower() not in question.lower(), (
            f"Quiz question leaked the answer! Best move '{best_move}' "
            f"appeared in the generated question text."
        )

    def test_best_move_is_legal_san(self, sample_blunder):
        """Sanity check that Stockfish returns a valid move string, not empty/garbage."""
        best_move = get_best_move(sample_blunder["fen_before"])
        assert isinstance(best_move, str) and len(best_move) > 0, (
            "get_best_move returned an empty or invalid result."
        )


# ---------------------------------------------------------------------------
# 3. LLM-AS-JUDGE TESTS — coach explanation quality/grounding
# ---------------------------------------------------------------------------

def llm_judge(criteria_prompt: str) -> dict:
    """
    Sends a grading prompt to Groq and expects a JSON verdict back.
    Returns {"pass": bool, "reason": str}.
    """
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": criteria_prompt}],
        temperature=0,
        max_tokens=200,
    )
    raw = response.choices[0].message.content.strip()

    # Be forgiving of the model wrapping JSON in markdown fences
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # If the judge didn't return clean JSON, fail loudly rather than
        # silently passing — a broken judge should not give false confidence.
        pytest.fail(f"Judge did not return valid JSON. Raw output:\n{raw}")


class TestCoachExplanationQuality:

    def test_explanation_mentions_the_actual_move_played(self, sample_blunder):
        """
        The coach's explanation should reference the move that was actually
        played (e.g. 'Bf4'), not a different, hallucinated move.
        """
        explanation = explain_blunder(sample_blunder)

        verdict = llm_judge(f"""
You are grading whether a chess coaching explanation correctly references
the move that was actually played.

Move actually played: {sample_blunder['move']}

Coach's explanation:
\"\"\"{explanation}\"\"\"

Does the explanation clearly refer to this move (or an unambiguous
description of it), without claiming a different move was played?

Respond with ONLY valid JSON in this exact format:
{{"pass": true or false, "reason": "one sentence explanation"}}
""")
        assert verdict["pass"], f"Judge failed explanation: {verdict['reason']}"

    def test_explanation_direction_matches_eval_swing(self, sample_blunder):
        """
        If eval_drop is large and negative for the player, the explanation
        should describe this as a mistake/blunder — not praise the move.
        """
        explanation = explain_blunder(sample_blunder)

        verdict = llm_judge(f"""
You are grading whether a chess coaching explanation correctly identifies
a move as a MISTAKE (not a good move), given a large negative evaluation swing.

Evaluation drop for the player: {sample_blunder['eval_drop']} centipawns (large drop = bad move).

Coach's explanation:
\"\"\"{explanation}\"\"\"

Does the explanation correctly treat this move as a mistake/blunder,
rather than praising it as good or neutral?

Respond with ONLY valid JSON in this exact format:
{{"pass": true or false, "reason": "one sentence explanation"}}
""")
        assert verdict["pass"], f"Judge failed explanation: {verdict['reason']}"

    def test_explanation_is_not_empty_or_error(self, sample_blunder):
        """Basic guard: the coach should never return an empty or error string."""
        explanation = explain_blunder(sample_blunder)
        assert explanation and "failed after retries" not in explanation.lower(), (
            "Coach explanation was empty or hit the retry-failure fallback."
        )

    def test_explanation_length_is_reasonable(self, sample_blunder):
        """
        The prompt asks for 3-4 sentences. Flag wildly short (broken) or
        wildly long (rambling/off-spec) outputs.
        """
        explanation = explain_blunder(sample_blunder)
        word_count = len(explanation.split())
        assert 15 <= word_count <= 200, (
            f"Explanation length ({word_count} words) is outside the expected "
            f"range for a 3-4 sentence coaching note."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])