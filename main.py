import sys
import time
sys.path.append("mcp_server")
sys.path.append("analysis")
sys.path.append("agents")

from lichess_server import get_latest_games
from blunder_finder import analyze_game
from coach import explain_blunder

USERNAME = "ihatechopperew"

def run():
    games = get_latest_games(USERNAME, num_games=1)
    print(f"Fetched {len(games)} real games for {USERNAME}\n")

    for i, game in enumerate(games, 1):
        white = game["white"]["username"]
        black = game["black"]["username"]
        pgn = game.get("pgn", "")

        print(f"=== Analyzing Game {i}: {white} vs {black} ===\n")

        blunders = analyze_game(pgn, player_username=USERNAME, blunder_threshold=300)

        if not blunders:
            print("No major blunders found (nice game!)\n")
        else:
            print(f"Found {len(blunders)} blunder(s). Getting coaching explanations...\n")
            for b in blunders:
                print(f"--- Move {b['move_number']} ({b['player']}): {b['move']} "
                      f"| Eval: {b['eval_before']} -> {b['eval_after']} (drop: {b['eval_drop']}) ---")
                explanation = explain_blunder(b)
                print(explanation)
                print()
                time.sleep(2)  # avoid hitting Groq rate limits

if __name__ == "__main__":
    run()