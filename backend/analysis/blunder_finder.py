import os
import chess
import chess.engine
import chess.pgn
import io
from dotenv import load_dotenv

load_dotenv()
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH")

MATE_SCORE_CAP = 1000  # cap mate scores so they don't distort math

# Speed vs accuracy tradeoff for Stockfish analysis.
# depth=12 (the old value) is noticeably slower on Render's free-tier CPU.
# depth=8 is still plenty strong to catch real blunders (300+ cp swings),
# since a genuine blunder is usually obvious even at shallow depth.
ANALYSIS_DEPTH = 8

def get_score(info):
    """Extract a usable centipawn score, capping mate scores instead of using huge numbers."""
    score = info["score"].relative
    if score.is_mate():
        mate_in = score.mate()
        return MATE_SCORE_CAP if mate_in > 0 else -MATE_SCORE_CAP
    return score.score()

def analyze_game(pgn_text, player_username, blunder_threshold=200):
    """
    Steps through a game, evaluating each position with Stockfish.
    Only flags blunders made by `player_username`.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    board = game.board()

    white_player = game.headers.get("White", "")
    black_player = game.headers.get("Black", "")

    blunders = []
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

    # Limit Stockfish to a single thread and small hash table. On Render's
    # free tier (shared, limited CPU/RAM), letting Stockfish assume it has
    # more resources than it actually gets can slow things down rather than
    # speed them up.
    try:
        engine.configure({"Threads": 1, "Hash": 16})
    except Exception:
        pass  # some engine builds don't expose these options, safe to skip

    try:
        for ply, move in enumerate(game.mainline_moves(), 1):
            mover_is_white = board.turn == chess.WHITE
            mover_name = white_player if mover_is_white else black_player

            info_before = engine.analyse(board, chess.engine.Limit(depth=ANALYSIS_DEPTH))
            score_before = get_score(info_before)

            move_san = board.san(move)
            board.push(move)

            info_after = engine.analyse(board, chess.engine.Limit(depth=ANALYSIS_DEPTH))
            score_after = -get_score(info_after)  # flip to same player's perspective

            if score_before is not None and score_after is not None:
                eval_drop = score_before - score_after
                if eval_drop >= blunder_threshold and mover_name.lower() == player_username.lower():
                    blunders.append({
                        "move_number": (ply + 1) // 2,
                        "player": mover_name,
                        "move": move_san,
                        "eval_before": score_before,
                        "eval_after": score_after,
                        "eval_drop": eval_drop,
                        "fen_before": board.fen()
                    })
    finally:
        engine.quit()

    return blunders


if __name__ == "__main__":
    sample_pgn = (
        '[Event "Test"]\n'
        '[White "TestWhite"]\n'
        '[Black "TestBlack"]\n'
        "\n"
        "1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7#\n"
    )
    results = analyze_game(sample_pgn, player_username="TestBlack", blunder_threshold=200)
    print(f"Found {len(results)} blunders\n")
    for b in results:
        print(f"Move {b['move_number']} ({b['player']}): {b['move']} | "
              f"Eval: {b['eval_before']} -> {b['eval_after']} (drop: {b['eval_drop']})")