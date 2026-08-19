"""
FastAPI backend for the AI Chess Coach.

Wraps the existing pipeline (blunder_finder, coach, quiz) into REST
endpoints for a Next.js frontend to call.

Run locally with:
    uvicorn api:app --reload --port 8000

Deploy to Render (or similar) as a standard Python web service.
"""

import os
import sys
import requests
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), "analysis"))
sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))

from blunder_finder import analyze_game
from coach import explain_blunder
from quiz import generate_quiz_question, get_best_move, grade_quiz_answer

app = FastAPI(title="AI Chess Coach API")

# Allow the Next.js frontend (localhost during dev, your Vercel domain in prod)
# to call this API. Update allow_origins with your real Vercel URL once deployed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ai-chess-coach-meeran.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {"User-Agent": "ai-chess-coach-app (contact: your_email@example.com)"}


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    username: str
    num_games: int = 1
    blunder_threshold: int = 300


class Blunder(BaseModel):
    game_index: int
    move_number: int
    player: str
    move: str
    eval_before: int
    eval_after: int
    eval_drop: int
    fen_before: str


class AnalyzeResponse(BaseModel):
    blunders: list[Blunder]
    games_checked: int


class ExplainRequest(BaseModel):
    blunder: Blunder


class QuizRequest(BaseModel):
    blunder: Blunder


class GradeRequest(BaseModel):
    blunder: Blunder
    user_answer: str


# ---------------------------------------------------------------------------
# Chess.com data fetching
# ---------------------------------------------------------------------------

def get_archives(username: str):
    url = f"https://api.chess.com/pub/player/{username}/games/archives"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()["archives"]


def get_latest_games(username: str, num_games: int = 3):
    archives = get_archives(username)
    if not archives:
        return []
    latest_archive_url = archives[-1]
    response = requests.get(latest_archive_url, headers=HEADERS)
    response.raise_for_status()
    games = response.json()["games"]
    return games[-num_games:]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def health_check():
    return {"status": "ok", "service": "ai-chess-coach-api"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    """Fetch recent games and run Stockfish blunder detection."""
    try:
        games = get_latest_games(req.username.strip(), num_games=req.num_games)
    except requests.HTTPError:
        raise HTTPException(
            status_code=404,
            detail=f"Couldn't find Chess.com games for '{req.username}'.",
        )

    if not games:
        return AnalyzeResponse(blunders=[], games_checked=0)

    all_blunders = []
    for i, game in enumerate(games):
        pgn = game.get("pgn", "")
        found = analyze_game(
            pgn, player_username=req.username.strip(), blunder_threshold=req.blunder_threshold
        )
        for b in found:
            b["game_index"] = i + 1
        all_blunders.extend(found)

    return AnalyzeResponse(blunders=all_blunders, games_checked=len(games))


@app.post("/explain")
def explain(req: ExplainRequest):
    """Get a coaching explanation for a specific blunder."""
    blunder_dict = req.blunder.model_dump()
    explanation = explain_blunder(blunder_dict)
    return {"explanation": explanation}


@app.post("/quiz")
def quiz(req: QuizRequest):
    """Generate a quiz question from a blunder position."""
    blunder_dict = req.blunder.model_dump()
    question = generate_quiz_question(blunder_dict)
    return {"question": question}


@app.post("/grade")
def grade(req: GradeRequest):
    """Grade a user's quiz answer against Stockfish's best move."""
    blunder_dict = req.blunder.model_dump()
    best_move = get_best_move(blunder_dict["fen_before"])
    feedback = grade_quiz_answer(blunder_dict, req.user_answer, best_move)
    return {"feedback": feedback, "best_move": best_move}