import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "analysis"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "agents"))

import requests
from fastmcp import FastMCP
from blunder_finder import analyze_game
from coach import explain_blunder
from quiz import generate_quiz_question, get_best_move

mcp = FastMCP("Chess Coach")


def _get_archives(username):
    url = f"https://api.chess.com/pub/player/{username}/games/archives"
    headers = {"User-Agent": "ai-chess-coach-app (contact: your_email@example.com)"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["archives"]


def _get_latest_games(username, num_games=5):
    archives = _get_archives(username)
    latest_archive_url = archives[-1]
    headers = {"User-Agent": "ai-chess-coach-app (contact: your_email@example.com)"}
    response = requests.get(latest_archive_url, headers=headers)
    response.raise_for_status()
    games = response.json()["games"]
    return games[-num_games:]


@mcp.tool()
def fetch_recent_games(username: str, num_games: int = 3) -> str:
    """Fetch a summary of a Chess.com player's most recent games."""
    games = _get_latest_games(username, num_games)
    summary = []
    for i, game in enumerate(games, 1):
        white = game["white"]["username"]
        black = game["black"]["username"]
        summary.append(f"Game {i}: {white} vs {black}")
    return "\n".join(summary) if summary else "No recent games found."


@mcp.tool()
def find_blunders(username: str, num_games: int = 1, blunder_threshold: int = 300) -> str:
    """
    Fetch a player's recent games and find their blunders using Stockfish analysis.
    Returns a summary of each blunder found (move, evaluation drop).
    """
    games = _get_latest_games(username, num_games)
    output = []

    for i, game in enumerate(games, 1):
        pgn = game.get("pgn", "")
        blunders = analyze_game(pgn, player_username=username, blunder_threshold=blunder_threshold)
        output.append(f"Game {i}: {len(blunders)} blunder(s) found")
        for b in blunders:
            output.append(
                f"  Move {b['move_number']} ({b['player']}): {b['move']} "
                f"| Eval: {b['eval_before']} -> {b['eval_after']} (drop: {b['eval_drop']})"
            )

    return "\n".join(output) if output else "No games or blunders found."


@mcp.tool()
def coach_explain(username: str, move: str, move_number: int, eval_before: int,
                   eval_after: int, fen_before: str) -> str:
    """
    Get a plain-English coaching explanation for a specific blunder.
    Provide the move details from find_blunders output.
    """
    blunder = {
        "move_number": move_number,
        "player": username,
        "move": move,
        "eval_before": eval_before,
        "eval_after": eval_after,
        "eval_drop": eval_before - eval_after,
        "fen_before": fen_before
    }
    return explain_blunder(blunder)


@mcp.tool()
def quiz_position(fen_before: str, move_number: int, username: str, original_mistake: str) -> str:
    """
    Generate a quiz question from a real blunder position, asking what the best move is.
    """
    blunder = {
        "move_number": move_number,
        "player": username,
        "move": original_mistake,
        "fen_before": fen_before
    }
    question = generate_quiz_question(blunder)
    best = get_best_move(fen_before)
    return f"{question}\n\n[Hidden answer for reference: {best}]"


if __name__ == "__main__":
    mcp.run()