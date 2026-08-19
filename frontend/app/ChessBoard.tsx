"use client";

interface ChessBoardProps {
  fen: string;
}

const PIECE_SYMBOLS: Record<string, string> = {
  K: "♔", Q: "♕", R: "♖", B: "♗", N: "♘", P: "♙",
  k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟",
};

function parseFEN(fen: string): (string | null)[][] {
  const boardPart = fen.split(" ")[0];
  const rows = boardPart.split("/");
  return rows.map((row) => {
    const squares: (string | null)[] = [];
    for (const char of row) {
      if (/\d/.test(char)) {
        for (let i = 0; i < Number(char); i++) squares.push(null);
      } else {
        squares.push(char);
      }
    }
    return squares;
  });
}

export default function ChessBoard({ fen }: ChessBoardProps) {
  const board = parseFEN(fen);

  return (
    <div className="inline-block rounded-lg overflow-hidden border border-white/10 shadow-lg">
      {board.map((row, rowIdx) => (
        <div key={rowIdx} className="flex">
          {row.map((piece, colIdx) => {
            const isDark = (rowIdx + colIdx) % 2 === 1;
            const isWhitePiece = piece && piece === piece.toUpperCase();
            return (
              <div
                key={colIdx}
                className={`w-9 h-9 flex items-center justify-center text-2xl select-none ${
                  isDark ? "bg-emerald-800" : "bg-emerald-100"
                }`}
              >
                {piece && (
                  <span
                    className={
                      isWhitePiece
                        ? "text-white drop-shadow-[0_1px_1px_rgba(0,0,0,0.9)]"
                        : "text-neutral-900"
                    }
                  >
                    {PIECE_SYMBOLS[piece]}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
