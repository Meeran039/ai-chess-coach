"""
Resolves the Stockfish binary path across environments.

Priority order:
1. STOCKFISH_PATH from .env (your local Windows path)
2. /usr/games/stockfish (where apt installs it on Render/Debian)
3. /usr/bin/stockfish (alternate common Linux install location)
4. Fall back to just "stockfish" and let the OS find it on PATH

Import get_stockfish_path() wherever STOCKFISH_PATH was previously read
directly from the environment.
"""

import os
import shutil


def get_stockfish_path() -> str:
    env_path = os.getenv("STOCKFISH_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    for candidate in ("/usr/games/stockfish", "/usr/bin/stockfish"):
        if os.path.exists(candidate):
            return candidate

    found_on_path = shutil.which("stockfish")
    if found_on_path:
        return found_on_path

    raise RuntimeError(
        "Could not locate a Stockfish binary. Set STOCKFISH_PATH in your "
        ".env file (local dev) or ensure Stockfish is installed and on "
        "PATH (deployment)."
    )