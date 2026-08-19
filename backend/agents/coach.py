import os
import time
from groq import Groq
from dotenv import load_dotenv

import sys
sys.path.append("rag")
from retriever import get_relevant_theory

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def call_groq_with_retry(model, prompt, max_retries=4):
    """Calls Groq with retry logic in case of rate limits or transient errors."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=350
            )
            return response.choices[0].message.content
        except Exception as e:
            wait_time = 5 * (attempt + 1)  # 5s, 10s, 15s, 20s — increasing backoff
            print(f"  [Retry {attempt+1}/{max_retries}] Error: {e} — waiting {wait_time}s")
            time.sleep(wait_time)
    return "[Coach explanation failed after retries]"


def explain_blunder(blunder, model="openai/gpt-oss-120b"):
    """
    Takes a blunder dict (from blunder_finder.py) and generates a plain-English
    coaching explanation, grounded in retrieved chess theory (RAG).
    """
    query = f"Move {blunder['move']} caused an evaluation drop of {blunder['eval_drop']} centipawns"
    theory_chunks = get_relevant_theory(query, n_results=2)
    theory_context = "\n\n".join(theory_chunks)

    prompt = f"""You are a friendly, encouraging chess coach explaining a mistake to an improving player.

BLUNDER DETAILS:
- Move played: {blunder['move']} (by {blunder['player']})
- Move number: {blunder['move_number']}
- Evaluation before: {blunder['eval_before']} centipawns
- Evaluation after: {blunder['eval_after']} centipawns
- Evaluation drop: {blunder['eval_drop']} centipawns
- Position (FEN) before the move: {blunder['fen_before']}

RELEVANT CHESS THEORY (use this to ground your explanation, don't just repeat it verbatim):
{theory_context}

Explain in 3-4 sentences, in plain simple language, WHY this move was likely a mistake, referencing the theory where relevant. Be encouraging, not harsh. If you can guess a likely tactical reason (fork, pin, hanging piece, etc.) based on the eval swing size, mention it as a possibility, but be clear it's an educated guess since you don't have the exact follow-up moves.
"""

    return call_groq_with_retry(model, prompt)


if __name__ == "__main__":
    sample_blunder = {
        "move_number": 7,
        "player": "ihatechopperew",
        "move": "Bf4",
        "eval_before": 72,
        "eval_after": -350,
        "eval_drop": 422,
        "fen_before": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4"
    }

    explanation = explain_blunder(sample_blunder)
    print("Coach's explanation:\n")
    print(explanation)