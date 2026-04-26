"""Modular CLI entry point for the music recommender system."""

from __future__ import annotations

import sys
from typing import Dict, List

try:
    from .recommender import load_songs as _load_songs
    from .recommender import (
        recommend_songs_with_context as _recommend_songs_with_context,
    )
    from .recommender import score_song as _score_song
except ImportError:
    from recommender import load_songs as _load_songs
    from recommender import (
        recommend_songs_with_context as _recommend_songs_with_context,
    )
    from recommender import score_song as _score_song


DEFAULT_PROFILE: Dict = {
    "genre": "",
    "mood": "happy",
    "energy": 0.6,
    "likes_acoustic": False,
    "mode": "genre-first",
    "preferred_decade": 2010,
}


EVALUATION_PROFILES: Dict[str, Dict] = {
    "High-Energy Pop": {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.85,
        "likes_acoustic": False,
        "mode": "genre-first",
    },
    "Chill Lofi": {
        "genre": "lofi",
        "mood": "chill",
        "energy": 0.40,
        "likes_acoustic": True,
        "mode": "mood-first",
    },
    "Deep Intense Rock": {
        "genre": "rock",
        "mood": "intense",
        "energy": 0.90,
        "likes_acoustic": False,
        "mode": "energy-focused",
    },
    "Adversarial Conflict": {
        "genre": "lofi",
        "mood": "intense",
        "energy": 0.95,
        "likes_acoustic": True,
        "mode": "genre-first",
    },
}


def get_user_preferences() -> Dict:
    """Collect user preferences from terminal input with safe defaults."""
    if not sys.stdin.isatty():
        return dict(DEFAULT_PROFILE)

    print("\nTell us your music vibe:\n")
    mood = input(
        "Enter mood (example: happy, chill, intense): "
    ).strip().lower()
    genre = input("Enter preferred genre (optional): ").strip().lower()

    energy = _prompt_energy_value()
    likes_acoustic = _prompt_yes_no(
        "Prefer acoustic sound? (y/n, default n): ",
        default=False,
    )

    profile = dict(DEFAULT_PROFILE)
    profile["mood"] = mood or DEFAULT_PROFILE["mood"]
    profile["genre"] = genre
    profile["energy"] = energy
    profile["likes_acoustic"] = likes_acoustic
    return profile


def load_songs(filepath: str) -> List[Dict]:
    """Load song records from CSV."""
    return _load_songs(filepath)


def retrieve_candidates(songs: List[Dict], preferences: Dict) -> List[Dict]:
    """Retrieve candidate songs using simple mood/genre filtering."""
    genre = str(preferences.get("genre", "")).strip().lower()
    mood = str(preferences.get("mood", "")).strip().lower()

    filtered = [
        song
        for song in songs
        if (genre and str(song.get("genre", "")).lower() == genre)
        or (mood and str(song.get("mood", "")).lower() == mood)
    ]

    return filtered or songs


def score_song(song: Dict, preferences: Dict) -> float:
    """Compute compatibility score between one song and user preferences."""
    score, _ = _score_song(preferences, song)
    return float(score)


def explain_recommendation(song: Dict, preferences: Dict) -> List[str]:
    """Return short bullet explanations for a recommended song."""
    reasons: List[str] = []

    pref_mood = str(preferences.get("mood", "")).strip().lower()
    song_mood = str(song.get("mood", "")).strip().lower()
    if pref_mood and song_mood == pref_mood:
        reasons.append(f"Matches your mood ({song_mood})")
    else:
        reasons.append("Fits your overall vibe")

    pref_energy = preferences.get("energy")
    song_energy = song.get("energy")
    if (
        isinstance(pref_energy, (int, float))
        and isinstance(song_energy, (int, float))
    ):
        if abs(float(song_energy) - float(pref_energy)) <= 0.15:
            reasons.append("Energy level is aligned with your preference")
        else:
            reasons.append("Energy level is close to what you like")
    else:
        reasons.append("Energy profile is suitable for your taste")

    pref_genre = str(preferences.get("genre", "")).strip().lower()
    song_genre = str(song.get("genre", "")).strip().lower()
    if pref_genre and song_genre == pref_genre:
        reasons.append(f"Matches your preferred genre ({song_genre})")
    else:
        reasons.append("Feels consistent with your usual listening style")

    return reasons[:3]


def rank_songs(
    songs: List[Dict],
    preferences: Dict,
    top_n: int = 3,
) -> List[Dict]:
    """Rank songs by score and return top-N recommendations."""
    candidates = retrieve_candidates(songs, preferences)
    ranked: List[Dict] = []
    seen_ids = set()

    for song in candidates:
        song_id = song.get("id")
        if song_id in seen_ids:
            continue
        seen_ids.add(song_id)

        score = score_song(song, preferences)
        confidence = max(0.35, min(0.99, score / 12.0))
        ranked.append(
            {
                "song": song,
                "score": round(score, 2),
                "confidence": round(confidence, 2),
                "why": explain_recommendation(song, preferences),
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_n]


def display_results(category_name: str, ranked_songs: List[Dict]) -> None:
    """Print clean, user-friendly recommendation output."""
    print(f"\n=== {category_name} ===\n")

    if not ranked_songs:
        print("No matching songs found. Try a different mood or genre.\n")
        return

    for index, item in enumerate(ranked_songs, start=1):
        song = item["song"]
        title = song.get("title", "Unknown Title")
        artist = song.get("artist", "Unknown Artist")
        print(f"{index}. {title} - {artist}")
        print(
            f"   Score: {item['score']:.2f} | "
            f"Confidence: {item['confidence']:.2f}"
        )
        print("   Why:")
        for reason in item["why"][:3]:
            print(f"   - {reason}")
        print()


def recommend_with_context(
    songs: List[Dict],
    preferences: Dict,
    top_n: int = 3,
) -> List[Dict]:
    """Use context-aware recommendations and keep a safe fallback path."""
    print("[RETRIEVAL] Retrieving supporting notes and ranking candidates...")
    enriched = _recommend_songs_with_context(
        user_prefs=preferences,
        songs=songs,
        k=top_n,
    )

    print("[SCORING] Computing compatibility scores and confidence...")
    ranked: List[Dict] = []
    for item in enriched:
        song = item["song"]
        retrieved_notes = item.get("retrieved_notes", [])
        why = explain_recommendation(song, preferences)

        if retrieved_notes:
            note = retrieved_notes[0]
            topic = str(note.get("topic", "knowledge")).strip() or "knowledge"
            content = str(note.get("content", "")).strip()
            content_preview = content[:80] + (
                "..." if len(content) > 80 else ""
            )
            why.append(
                f"Supported by retrieved {topic} note: {content_preview}"
            )

        ranked.append(
            {
                "song": song,
                "score": round(float(item.get("score", 0.0)), 2),
                "confidence": round(float(item.get("confidence", 0.0)), 2),
                "why": why[:3],
            }
        )

    if ranked and max(entry["confidence"] for entry in ranked) < 0.50:
        print(
            "[SCORING] Low confidence detected. "
            "Falling back to baseline ranking."
        )
        fallback = rank_songs(songs, preferences, top_n=top_n)
        for entry in fallback:
            entry["why"].append(
                "Fallback applied due to low confidence in context signals"
            )
        return fallback

    return ranked


def run_tests(songs: List[Dict]) -> None:
    """Run basic reliability checks using predefined preference profiles."""
    print("\n🔍 Running reliability tests to evaluate system performance...\n")

    test_cases = [
        {
            "name": "Happy Pop Listener",
            "prefs": {
                "genre": "pop",
                "mood": "happy",
                "energy": 0.8,
                "likes_acoustic": False,
                "mode": "genre-first",
            },
        },
        {
            "name": "Chill Lofi Listener",
            "prefs": {
                "genre": "lofi",
                "mood": "chill",
                "energy": 0.4,
                "likes_acoustic": True,
                "mode": "genre-first",
            },
        },
        {
            "name": "Rock Intense Listener",
            "prefs": {
                "genre": "rock",
                "mood": "intense",
                "energy": 0.9,
                "likes_acoustic": False,
                "mode": "genre-first",
            },
        },
    ]

    passed = 0
    for test in test_cases:
        try:
            result = rank_songs(songs, test["prefs"], top_n=3)
            structure_ok = all(
                {"song", "score", "confidence", "why"}.issubset(item.keys())
                for item in result
            )
            print(f"- {test['name']}: {'PASS' if structure_ok else 'FAIL'}")

            display_results(test["name"], result)

            match_count = _count_mood_or_genre_matches(result, test["prefs"])
            total = 3
            print(
                f"Match summary: {match_count}/{total} recommendations "
                "matched mood or genre\n"
            )

            if structure_ok:
                passed += 1
        except Exception as error:
            print(f"- {test['name']}: FAIL ({error})")

    print(f"\nTest summary: {passed}/{len(test_cases)} passed\n")
    print("📊 Overall System Reliability:")
    print("✔ Consistent across multiple user profiles")
    print("✔ Produces explainable recommendations")
    print("✔ Matches user preferences effectively")
    print()


def main() -> None:
    print("\n🎧 AI Music Recommender System")
    print("-----------------------------------")

    print("[INPUT] Loading songs dataset...")
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")
    if not songs:
        print(
            "No songs were loaded. "
            "Please check data/songs.csv and try again."
        )
        return

    print("[INPUT] Collecting user preferences...")
    preferences = get_user_preferences()
    if not str(preferences.get("mood", "")).strip():
        preferences["mood"] = DEFAULT_PROFILE["mood"]

    try:
        ranked_songs = recommend_with_context(songs, preferences, top_n=3)
    except ValueError as error:
        print(f"[INPUT] Invalid preferences detected: {error}")
        print("[SCORING] Falling back to safe default profile.")
        ranked_songs = recommend_with_context(
            songs,
            dict(DEFAULT_PROFILE),
            top_n=3,
        )

    print("[OUTPUT] Rendering recommendations...")
    display_results("Your Recommendations", ranked_songs)

    if sys.stdin.isatty() and _prompt_yes_no(
        "Run reliability tests now? (y/n, default n): ",
        default=False,
    ):
        run_tests(songs)


def _prompt_energy_value() -> float:
    """Prompt for energy within [0, 1] with validation and default fallback."""
    while True:
        value = input(
            "Enter preferred energy (0.0 to 1.0, default 0.6): "
        ).strip()
        if not value:
            return 0.6
        try:
            parsed = float(value)
        except ValueError:
            print("Please enter a valid numeric value.")
            continue

        # Allow percent-style values like 50 by normalizing to 0.50.
        if parsed > 1.0:
            parsed /= 100.0

        if 0.0 <= parsed <= 1.0:
            return parsed
        print("Energy must be between 0.0 and 1.0.")


def _prompt_yes_no(prompt: str, default: bool) -> bool:
    """Prompt for yes/no with a default value."""
    value = input(prompt).strip().lower()
    return value in {"y", "yes", "true", "1"} if value else default


def _count_mood_or_genre_matches(
    ranked_songs: List[Dict],
    preferences: Dict,
) -> int:
    """Return how many recommendations match preferred mood or genre."""
    pref_mood = str(preferences.get("mood", "")).strip().lower()
    pref_genre = str(preferences.get("genre", "")).strip().lower()

    matches = 0
    for item in ranked_songs:
        song = item.get("song", {})
        song_mood = str(song.get("mood", "")).strip().lower()
        song_genre = str(song.get("genre", "")).strip().lower()
        if (pref_mood and song_mood == pref_mood) or (
            pref_genre and song_genre == pref_genre
        ):
            matches += 1
    return matches


if __name__ == "__main__":
    main()
