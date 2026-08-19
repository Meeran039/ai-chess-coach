# AI Chess Coach

An AI-powered coaching app that pulls your real Chess.com games, finds your blunders using the Stockfish engine, explains them in plain English using a RAG-grounded LLM, and quizzes you on your own mistakes to help you actually learn from them.

Built as a hands-on project to explore four core AI engineering concepts: RAG, MCP, multi-agent systems, and evals, all wired into one working application instead of four separate toy demos.

## What it does

1. You enter your Chess.com username
2. The app fetches your recent games from Chess.com's public API
3. Every move is analyzed with the Stockfish chess engine to find blunders (moves that significantly worsened your position)
4. For any blunder, an LLM coach explains what went wrong, using a knowledge base of chess opening theory and tactical patterns for grounding (RAG), so the explanation is based on real chess concepts instead of the model guessing
5. You can quiz yourself on that exact position, type your answer, and get graded against Stockfish's actual best move

## Why this project

Most AI portfolio projects either use synthetic examples or stop at "chat with a PDF." This one is built around a domain (chess) with objective ground truth, so the AI's output can actually be checked for correctness, not just fluency. That objectivity is also what makes the eval suite meaningful, since Stockfish gives a deterministic, verifiable answer for what the LLM should be explaining.

## Architecture

```
Frontend (Next.js, deployed on Vercel)
        |
        v  HTTP requests
Backend (FastAPI, deployed on Render)
        |
        +--> Chess.com public API        (fetch real games)
        +--> Stockfish (python-chess)     (find blunders, get best moves)
        +--> ChromaDB                     (RAG: chess theory retrieval)
        +--> Groq (LLM inference)         (coaching explanations, quiz generation)
        +--> MCP server (FastMCP)         (exposes tools to any MCP-compatible client)
```

## The four core concepts, applied

**RAG (Retrieval-Augmented Generation)**
The coaching explanations are grounded in a small knowledge base of opening theory and tactical patterns (`backend/rag/opening_theory.md`), embedded and stored in ChromaDB. When a blunder is found, the relevant theory is retrieved and passed into the LLM's prompt, so explanations reference real chess concepts (forks, pins, king safety, tempo) instead of the model inventing plausible-sounding but ungrounded reasoning.

**MCP (Model Context Protocol)**
The backend exposes its core functionality (fetch games, find blunders, get a coaching explanation, generate a quiz) as MCP tools via FastMCP. This means any MCP-compatible client, including Claude Desktop, can connect to the server and use these tools directly, not just this app's own frontend.

**Multi-agent design**
Three distinct roles handle different jobs instead of one prompt doing everything:
- A deterministic analysis layer (Stockfish plus python-chess) finds blunders and calculates evaluations
- A coaching agent (Groq LLM plus RAG) explains why a move was a mistake
- A quiz agent (Groq LLM) turns a real blunder into a quiz question and grades the user's answer against Stockfish's ground truth

**Evals**
`backend/evals/test_explanation_accuracy.py` contains two kinds of tests:
- Deterministic tests that verify blunder detection logic, eval math, and quiz integrity (for example, checking the quiz never accidentally leaks the correct answer in the question text)
- LLM-as-judge tests that use a separate model call to verify the coach's explanation actually references the move that was played and correctly treats a large evaluation drop as a mistake, not a good move

This eval suite already caught two real bugs during development: a malformed PGN test fixture that silently parsed zero moves, and a Groq API edge case where an empty response was not being retried.

## Tech stack

- **Backend**: Python, FastAPI, Uvicorn
- **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS
- **Chess engine**: Stockfish, accessed via python-chess
- **LLM inference**: Groq API (free tier)
- **Vector database**: ChromaDB (local, persistent)
- **MCP**: FastMCP
- **Testing**: pytest
- **Data source**: Chess.com public API

## Project structure

```
ai-chess-coach/
    backend/
        agents/
            coach.py          RAG-grounded coaching explanations
            quiz.py            Quiz generation and grading
        analysis/
            blunder_finder.py  Stockfish-based blunder detection
        rag/
            ingest.py          Chunks and embeds opening theory into ChromaDB
            retriever.py       Retrieves relevant theory chunks for a query
            opening_theory.md  The knowledge base itself
        mcp_server/
            lichess_server.py  MCP server exposing coaching tools (Chess.com API)
        evals/
            test_explanation_accuracy.py
        api.py                 FastAPI app, REST endpoints for the frontend
        requirements.txt
    frontend/
        app/
            page.tsx           Main UI
            ChessBoard.tsx     Renders a FEN position as a visual board with move highlighting
        package.json
```

## Running it locally

### Backend

```
cd backend
python -m venv venv
venv\Scripts\activate          (Windows)
pip install -r requirements.txt
```

Create a `.env` file in `backend/` with:
```
GROQ_API_KEY=your_groq_key_here
STOCKFISH_PATH=C:\path\to\stockfish.exe
```

Build the RAG database once:
```
python rag\ingest.py
```

Run the API:
```
uvicorn api:app --reload --port 8000
```

### Frontend

```
cd frontend
npm install
```

Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run it:
```
npm run dev
```

Visit `http://localhost:3000`.

### Running the evals

```
cd backend
python -m pytest evals\test_explanation_accuracy.py -v
```

## Notable design decisions

**Centipawn threshold as a tunable slider.** Rather than hardcoding what counts as a blunder, the sensitivity is adjustable (100 to 500 centipawns), since what counts as a meaningful mistake differs by skill level.

**Stockfish as ground truth, LLM as explainer.** The LLM is never asked to judge whether a move was good or bad. That determination comes entirely from Stockfish's evaluation. The LLM's only job is explaining a fact that has already been established deterministically, which avoids relying on the model's own, unreliable chess calculation ability.

**Visual board instead of raw FEN.** FEN strings are accurate but unreadable to anyone who is not already fluent in the notation. The frontend parses FEN into an actual rendered board and highlights the specific square(s) involved in the blunder, so the position is understandable at a glance.

## Possible extensions

- CI/CD pipeline that runs the eval suite on every push and blocks merges on regressions
- Support for Lichess in addition to Chess.com
- Persisting analysis history per user across sessions
- Expanding the RAG knowledge base with endgame theory and more opening lines

## Credits

Built using free tiers throughout: Groq for LLM inference, Chess.com's public API for game data, and Stockfish, which is free and open source.