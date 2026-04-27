"""Root-level launcher for the music recommender project.

This keeps `python recommender.py` working from the repository root while the
implementation remains in `src/`.
"""

from src.main import main


if __name__ == "__main__":
    main()