from typing import List, Dict, Tuple
from dataclasses import dataclass
import csv


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        scored_songs = sorted(
            self.songs,
            key=lambda song: score_song(
                {
                    "favorite_genre": user.favorite_genre,
                    "favorite_mood": user.favorite_mood,
                    "target_energy": user.target_energy,
                    "likes_acoustic": user.likes_acoustic,
                },
                {
                    "genre": song.genre,
                    "mood": song.mood,
                    "energy": song.energy,
                    "acousticness": song.acousticness,
                },
            )[0],
            reverse=True,
        )
        return scored_songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        _, reasons = score_song(
            {
                "favorite_genre": user.favorite_genre,
                "favorite_mood": user.favorite_mood,
                "target_energy": user.target_energy,
                "likes_acoustic": user.likes_acoustic,
            },
            song,
        )
        return _format_explanation(reasons)


def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from CSV into dictionaries with numeric fields parsed."""
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        songs = [
            {
                "id": int(row["id"]),
                "title": row["title"],
                "artist": row["artist"],
                "genre": row["genre"],
                "mood": row["mood"],
                "energy": float(row["energy"]),
                "tempo_bpm": float(row["tempo_bpm"]),
                "valence": float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            }
            for row in reader
        ]
    return songs


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
) -> List[Tuple[Dict, float, str]]:
    """Score all songs, rank them, and return the top k results."""
    ranked: List[Tuple[Dict, float, str]] = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = _format_explanation(reasons)
        ranked.append((song, score, explanation))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:k]


def score_song(user_prefs: Dict, song: Song | Dict) -> Tuple[float, List[str]]:
    """Calculate a score for one song and return the reasons behind it."""
    genre = _song_value(song, "genre")
    mood = _song_value(song, "mood")
    energy = float(_song_value(song, "energy"))
    acousticness = float(_song_value(song, "acousticness"))

    score = 0.0
    reasons: List[str] = []

    favorite_genre = (
        user_prefs.get("genre")
        or user_prefs.get("favorite_genre")
    )
    favorite_mood = user_prefs.get("mood") or user_prefs.get("favorite_mood")
    target_energy = user_prefs.get("energy") or user_prefs.get("target_energy")
    likes_acoustic = user_prefs.get("likes_acoustic")

    if favorite_genre and genre == favorite_genre:
        score += 3.0
        reasons.append(f"genre match (+3.0): {genre}")

    if favorite_mood and mood == favorite_mood:
        score += 2.5
        reasons.append(f"mood match (+2.5): {mood}")

    if target_energy is not None:
        energy_difference = abs(energy - float(target_energy))
        energy_score = max(0.0, 2.0 - (energy_difference * 4.0))
        score += energy_score
        reasons.append(
            "energy similarity "
            f"(+{energy_score:.2f}): "
            f"target {float(target_energy):.2f}, song {energy:.2f}"
        )

    if likes_acoustic is True:
        acoustic_score = acousticness
        score += acoustic_score
        reasons.append(
            "acoustic preference "
            f"(+{acoustic_score:.2f}): acousticness {acousticness:.2f}"
        )
    elif likes_acoustic is False:
        acoustic_score = 1.0 - acousticness
        score += acoustic_score
        reasons.append(
            "less-acoustic preference "
            f"(+{acoustic_score:.2f}): acousticness {acousticness:.2f}"
        )

    return score, reasons


def _format_explanation(reasons: List[str]) -> str:
    """Convert scoring reasons into a user-facing explanation string."""
    return "Recommended because " + "; ".join(reasons) + "."


def _song_value(song: Song | Dict, key: str):
    """Read a field from either a Song dataclass or a song dictionary."""
    return getattr(song, key) if isinstance(song, Song) else song[key]
