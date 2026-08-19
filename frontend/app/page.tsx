"use client";

import { useState } from "react";
import ChessBoard from "./ChessBoard";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Blunder {
  game_index: number;
  move_number: number;
  player: string;
  move: string;
  eval_before: number;
  eval_after: number;
  eval_drop: number;
  fen_before: string;
}

export default function Home() {
  const [username, setUsername] = useState("");
  const [numGames, setNumGames] = useState(1);
  const [threshold, setThreshold] = useState(300);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [blunders, setBlunders] = useState<Blunder[]>([]);
  const [gamesChecked, setGamesChecked] = useState<number | null>(null);

  const [explanations, setExplanations] = useState<Record<number, string>>({});
  const [quizQuestions, setQuizQuestions] = useState<Record<number, string>>({});
  const [userAnswers, setUserAnswers] = useState<Record<number, string>>({});
  const [feedback, setFeedback] = useState<Record<number, string>>({});
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [showFen, setShowFen] = useState<Record<number, boolean>>({});

  async function handleAnalyze(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim()) {
      setError("Please enter a Chess.com username.");
      return;
    }

    setLoading(true);
    setError("");
    setBlunders([]);
    setExplanations({});
    setQuizQuestions({});
    setFeedback({});

    try {
      const res = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: username.trim(),
          num_games: numGames,
          blunder_threshold: threshold,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to analyze games.");
      }

      const data = await res.json();
      setBlunders(data.blunders);
      setGamesChecked(data.games_checked);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function handleExplain(idx: number, blunder: Blunder) {
    setLoadingAction(`explain-${idx}`);
    try {
      const res = await fetch(`${API_URL}/explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ blunder }),
      });
      const data = await res.json();
      setExplanations((prev) => ({ ...prev, [idx]: data.explanation }));
    } finally {
      setLoadingAction(null);
    }
  }

  async function handleQuiz(idx: number, blunder: Blunder) {
    setLoadingAction(`quiz-${idx}`);
    try {
      const res = await fetch(`${API_URL}/quiz`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ blunder }),
      });
      const data = await res.json();
      setQuizQuestions((prev) => ({ ...prev, [idx]: data.question }));
    } finally {
      setLoadingAction(null);
    }
  }

  async function handleSubmitAnswer(idx: number, blunder: Blunder) {
    const answer = userAnswers[idx];
    if (!answer?.trim()) return;

    setLoadingAction(`grade-${idx}`);
    try {
      const res = await fetch(`${API_URL}/grade`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ blunder, user_answer: answer.trim() }),
      });
      const data = await res.json();
      setFeedback((prev) => ({ ...prev, [idx]: data.feedback }));
    } finally {
      setLoadingAction(null);
    }
  }

  function severityColor(evalDrop: number) {
    if (evalDrop >= 500) return "text-rose-400 bg-rose-500/10 border-rose-500/30";
    if (evalDrop >= 300) return "text-orange-400 bg-orange-500/10 border-orange-500/30";
    return "text-amber-300 bg-amber-500/10 border-amber-500/30";
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-indigo-950 via-slate-900 to-emerald-950 text-neutral-100 px-4 py-10">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-4xl">♟️</span>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-amber-300 via-orange-300 to-rose-300 bg-clip-text text-transparent">
            AI Chess Coach
          </h1>
        </div>
        <p className="text-indigo-200/70 mb-8">
          Pulls your real Chess.com games, finds blunders with Stockfish, explains
          them with an LLM grounded in chess theory (RAG), and quizzes you on them.
        </p>

        <form
          onSubmit={handleAnalyze}
          className="bg-white/5 backdrop-blur border border-white/10 rounded-2xl p-6 mb-8 space-y-4 shadow-xl"
        >
          <div>
            <label className="block text-sm text-indigo-200/70 mb-1">Chess.com username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. ihatechopperew"
              className="w-full bg-slate-800/80 rounded-lg px-3 py-2 outline-none border border-white/10 focus:ring-2 focus:ring-amber-400 focus:border-transparent transition"
            />
          </div>

          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm text-indigo-200/70 mb-1">Games to check</label>
              <input
                type="number"
                min={1}
                max={5}
                value={numGames}
                onChange={(e) => setNumGames(Number(e.target.value))}
                className="w-full bg-slate-800/80 rounded-lg px-3 py-2 outline-none border border-white/10 focus:ring-2 focus:ring-amber-400 focus:border-transparent transition"
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm text-indigo-200/70 mb-1">
                Sensitivity ({threshold} cp)
              </label>
              <input
                type="range"
                min={100}
                max={500}
                step={50}
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                className="w-full mt-3 accent-amber-400"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-amber-500 to-rose-500 hover:from-amber-400 hover:to-rose-400 disabled:opacity-50 rounded-lg py-2.5 font-semibold transition shadow-lg shadow-amber-900/30"
          >
            {loading ? "Analyzing..." : "Analyze my games"}
          </button>

          {error && <p className="text-rose-400 text-sm">{error}</p>}
        </form>

        {gamesChecked !== null && blunders.length === 0 && !loading && (
          <p className="text-emerald-400 mb-6">
            No blunders found in the last {gamesChecked} game(s). Nice play!
          </p>
        )}

        {blunders.length > 0 && (
          <div className="space-y-5">
            <h2 className="text-xl font-semibold text-indigo-100">
              Found {blunders.length} blunder(s) across {gamesChecked} game(s)
            </h2>

            {blunders.map((b, idx) => (
              <div
                key={idx}
                className="bg-white/5 backdrop-blur border border-white/10 rounded-2xl p-5 shadow-xl"
              >
                <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
                  <p className="font-medium text-indigo-100">
                    Game {b.game_index}, Move {b.move_number}:{" "}
                    <span className="text-amber-300">{b.move}</span>
                  </p>
                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded-full border ${severityColor(
                      b.eval_drop
                    )}`}
                  >
                    {b.eval_drop} cp swing
                  </span>
                </div>

                <div className="flex flex-col sm:flex-row gap-4 mb-4">
                  <ChessBoard fen={b.fen_before} />

                  <div className="flex-1">
                    <button
                      onClick={() => setShowFen((prev) => ({ ...prev, [idx]: !prev[idx] }))}
                      className="text-xs text-indigo-300 hover:text-indigo-100 underline underline-offset-2 mb-2"
                    >
                      {showFen[idx] ? "Hide raw FEN" : "Show raw FEN"}
                    </button>
                    {showFen[idx] && (
                      <code className="block text-xs bg-slate-800/80 rounded p-2 overflow-x-auto border border-white/10">
                        {b.fen_before}
                      </code>
                    )}
                  </div>
                </div>

                <div className="flex gap-3 mb-3">
                  <button
                    onClick={() => handleExplain(idx, b)}
                    disabled={loadingAction === `explain-${idx}`}
                    className="bg-indigo-600/80 hover:bg-indigo-500 disabled:opacity-50 rounded-lg px-4 py-1.5 text-sm font-medium transition"
                  >
                    {loadingAction === `explain-${idx}` ? "Thinking..." : "Get explanation"}
                  </button>
                  <button
                    onClick={() => handleQuiz(idx, b)}
                    disabled={loadingAction === `quiz-${idx}`}
                    className="bg-emerald-700/80 hover:bg-emerald-600 disabled:opacity-50 rounded-lg px-4 py-1.5 text-sm font-medium transition"
                  >
                    {loadingAction === `quiz-${idx}` ? "Generating..." : "Quiz me"}
                  </button>
                </div>

                {explanations[idx] && (
                  <p className="text-sm bg-indigo-500/10 border border-indigo-500/20 rounded-lg p-3 mb-3 leading-relaxed">
                    <span className="font-semibold text-indigo-300">Coach: </span>
                    {explanations[idx]}
                  </p>
                )}

                {quizQuestions[idx] && (
                  <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 space-y-2">
                    <p className="text-sm leading-relaxed">{quizQuestions[idx]}</p>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="Your move (e.g. Nf3)"
                        value={userAnswers[idx] || ""}
                        onChange={(e) =>
                          setUserAnswers((prev) => ({ ...prev, [idx]: e.target.value }))
                        }
                        className="flex-1 bg-slate-800/80 rounded-lg px-3 py-1.5 text-sm outline-none border border-white/10 focus:ring-2 focus:ring-emerald-400"
                      />
                      <button
                        onClick={() => handleSubmitAnswer(idx, b)}
                        disabled={loadingAction === `grade-${idx}`}
                        className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg px-4 py-1.5 text-sm font-medium transition"
                      >
                        Submit
                      </button>
                    </div>
                    {feedback[idx] && (
                      <p className="text-sm text-emerald-300 pt-1 leading-relaxed">
                        {feedback[idx]}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
