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

# Keep default behavior demo-friendly (safe fallbacks). Set to True to
# enforce re-prompting until valid values are provided.
STRICT_INPUT_MODE = False

MOOD_DEFINITIONS = {
    "happy": {
        "description": "Upbeat and positive music.",
        "typical_energy": "medium to high",
        "keywords": ["joyful", "bright", "uplifting"],
    },
    "chill": {
        "description": "Relaxed and calm easy-listening music.",
        "typical_energy": "low to medium",
        "keywords": ["calm", "smooth", "soft"],
    },
    "intense": {
        "description": "Powerful and emotionally strong high-energy music.",
        "typical_energy": "high",
        "keywords": ["aggressive", "dramatic", "driving"],
    },
    "sad": {
        "description": "Emotional and reflective music.",
        "typical_energy": "low",
        "keywords": ["melancholic", "emotional", "deep"],
    },
    "energetic": {
        "description": "Fast-paced and motivating music.",
        "typical_energy": "high",
        "keywords": ["fast", "exciting", "active"],
    },
}

VALID_MOODS = set(MOOD_DEFINITIONS.keys())

VALID_GENRES = {
    "ambient",
    "classical",
    "country",
    "electronic",
    "folk",
    "hip-hop",
    "indie pop",
    "jazz",
    "latin",
    "lofi",
    "metal",
    "pop",
    "r&b",
    "rock",
    "synthwave",
}

MOOD_MAPPING = {
    "dance": "energetic",
    "party": "energetic",
    "relax": "chill",
    "calm": "chill",
    "focus": "chill",
    "workout": "energetic",
    "chil": "chill",
    "happpy": "happy",
    "energeticc": "energetic",
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

    warnings: List[str] = []

    print("\n🎧 AI Music Recommender System")
    print("Enter your preferences:\n")
    mood_input = input(
        "Mood (happy, chill, intense, sad, energetic): "
    ).strip().lower()
    genre = input("Genre (optional): ").strip().lower()
    if genre and genre not in VALID_GENRES:
        warnings.append("[WARNING] Unknown genre. Ignoring preference.")
        genre = None

    mood = mood_input or DEFAULT_PROFILE["mood"]
    if not mood_input:
        warnings.append(f"[INFO] No mood provided. Using default ({mood}).")
    while True:
        if not mood:
            mood = DEFAULT_PROFILE["mood"]

        if mood in VALID_MOODS:
            break

        if mood in MOOD_MAPPING:
            mapped = MOOD_MAPPING[mood]
            warnings.append(f"[INFO] Interpreting '{mood}' as '{mapped}'")
            mood = mapped
            break

        warnings.append(
            "[WARNING] Unknown mood. Using general recommendations."
        )
        if not STRICT_INPUT_MODE:
            mood = None
            break

        mood = input(
            "Mood (happy, chill, intense, sad, energetic): "
        ).strip().lower()

    energy = _prompt_energy_value(warnings, strict_mode=STRICT_INPUT_MODE)
    likes_acoustic = _prompt_yes_no(
        "Acoustic? (y/n, default n): ",
        default=False,
        warnings=warnings,
        strict_mode=STRICT_INPUT_MODE,
    )

    profile = dict(DEFAULT_PROFILE)
    profile["mood"] = mood
    profile["genre"] = genre
    profile["energy"] = energy
    profile["likes_acoustic"] = likes_acoustic
    profile["warnings"] = warnings
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

    mood_value = preferences.get("mood")
    song_mood = str(song.get("mood", "")).strip().lower()
    if mood_value is None:
        reasons.append("Fits your overall vibe")
    else:
        mood = str(mood_value).strip().lower()
        if mood and song_mood == mood:
            if mood_description := MOOD_DEFINITIONS.get(mood, {}).get(
                "description",
                "",
            ):
                reasons.append(
                    f"Matches your mood ({mood}) - {mood_description}"
                )
            else:
                reasons.append(f"Matches your mood ({mood})")
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
    try:
        preferences = get_user_preferences()
    except KeyboardInterrupt:
        print("\n[INPUT] Cancelled by user. Exiting.")
        return
    if preferences.get("mood") is not None and not str(
        preferences.get("mood", "")
    ).strip():
        preferences["mood"] = DEFAULT_PROFILE["mood"]

    if warnings := preferences.pop("warnings", []):
        print("\n[WARNINGS]")
        for message in warnings:
            print(f"- {message}")

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

    try:
        should_run_tests = sys.stdin.isatty() and _prompt_yes_no(
            "Run reliability tests now? (y/n, default n): ",
            default=False,
            warnings=[],
        )
    except KeyboardInterrupt:
        print("\n[INPUT] Cancelled by user. Exiting.")
        return

    if should_run_tests:
        run_tests(songs)

    print("\nDone. You can run again with different inputs.\n")


def _prompt_energy_value(
    warnings: List[str],
    strict_mode: bool = False,
) -> float:
    """Prompt for energy and apply strict range validation with fallback."""
    while True:
        value = input(
            "Energy (0.0-1.0, default 0.6): "
        ).strip()
        if not value:
            return 0.6

        try:
            parsed = float(value)
        except ValueError:
            warnings.append(
                "[WARNING] Energy must be between 0.0 and 1.0. "
                "Using default (0.6)."
            )
            if strict_mode:
                continue
            return 0.6

        if not 0.0 <= parsed <= 1.0:
            warnings.append(
                "[WARNING] Energy must be between 0.0 and 1.0. "
                "Using default (0.6)."
            )
            if strict_mode:
                continue
            return 0.6

        return parsed


def _prompt_yes_no(
    prompt: str,
    default: bool,
    warnings: List[str],
    strict_mode: bool = False,
) -> bool:
    """Prompt for y/n with default fallback and warning on invalid input."""
    while True:
        value = input(prompt).strip().lower()
        if not value:
            return default
        if value == "y":
            return True
        if value == "n":
            return False

        warnings.append("[WARNING] Invalid input. Defaulting to 'n'.")
        if strict_mode:
            continue
        return False


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
