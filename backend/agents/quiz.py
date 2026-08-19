import os
import time
import chess
import chess.engine
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH")


def get_best_move(fen, depth=12):
    """Ask Stockfish for the best move in a given position."""
    board = chess.Board(fen)
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    try:
        result = engine.play(board, chess.engine.Limit(depth=depth))
        best_move_san = board.san(result.move)
        return best_move_san
    finally:
        engine.quit()


def generate_quiz_question(blunder, model="openai/gpt-oss-120b"):
    """
    Turns a blunder into a quiz question: shows the position before the mistake
    and asks what the player should play, without revealing the answer.
    """
    prompt = f"""You are a chess coach creating a quiz question from a student's real game.

POSITION (FEN): {blunder['fen_before']}
Move number: {blunder['move_number']}
Player to move: {blunder['player']}

The student actually played "{blunder['move']}" here, which was a mistake.

Write a short, engaging quiz prompt (2-3 sentences) describing the position in words
(mention material balance, king safety, or piece activity if relevant) and ask
"What would you play here?" — DO NOT reveal the best move or hint at the answer.
Keep it encouraging and game-show-like in tone.
"""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=150
    )
    return response.choices[0].message.content


def grade_quiz_answer(blunder, user_answer, best_move, model="openai/gpt-oss-120b"):
    """
    Compares the user's answer to Stockfish's best move and gives feedback.
    """
    prompt = f"""You are a chess coach grading a student's quiz answer.

Position (FEN): {blunder['fen_before']}
The student's actual mistake in the real game was: {blunder['move']}
The student's quiz answer just now was: {user_answer}
Stockfish's best move in this position is: {best_move}

Grade the student's answer:
- If their answer matches or is close in spirit to the best move, praise them enthusiastically.
- If their answer matches their ORIGINAL mistake, gently point out they repeated it and explain briefly why the best move is better.
- If it's a different move than both, explain briefly whether it's reasonable or not, and reveal the best move.

Keep it to 3-4 sentences, encouraging tone.
"""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    # Test with a sample blunder
    sample_blunder = {
        "move_number": 7,
        "player": "ihatechopperew",
        "move": "Bf4",
        "eval_before": 72,
        "eval_after": -350,
        "eval_drop": 422,
        "fen_before": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4"
    }

    print("Generating quiz question...\n")
    question = generate_quiz_question(sample_blunder)
    print(question)
    print()

    best_move = get_best_move(sample_blunder["fen_before"])
    print(f"[DEBUG - Stockfish's actual best move: {best_move}]\n")

    user_answer = input("Your answer: ")

    print("\nGrading...\n")
    feedback = grade_quiz_answer(sample_blunder, user_answer, best_move)
    print(feedback)