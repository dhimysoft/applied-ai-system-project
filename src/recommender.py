from typing import List, Dict, Tuple
from dataclasses import dataclass
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


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
    popularity: int = 50
    release_decade: int = 2010
    mood_tag: str = "balanced"
    instrumentalness: float = 0.5
    liveness: float = 0.3
    speechiness: float = 0.1


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
                song,
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


def validate_user_profile(user_prefs: Dict) -> Tuple[bool, List[str]]:
    """Guardrail checks for user preference payloads before recommendation."""
    issues: List[str] = []

    target_energy = user_prefs.get("energy") or user_prefs.get("target_energy")
    if target_energy is None:
        issues.append("missing energy/target_energy")
    else:
        try:
            energy_value = float(target_energy)
            if not 0.0 <= energy_value <= 1.0:
                issues.append("energy must be between 0.0 and 1.0")
        except (TypeError, ValueError):
            issues.append("energy must be numeric")

    likes_acoustic = user_prefs.get("likes_acoustic")
    if likes_acoustic is not None and not isinstance(likes_acoustic, bool):
        issues.append("likes_acoustic must be true/false")

    mode = str(user_prefs.get("mode", "genre-first")).lower()
    if mode not in {"genre-first", "mood-first", "energy-focused"}:
        issues.append(
            "mode must be one of genre-first, mood-first, energy-focused"
        )

    return not issues, issues


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
                "popularity": int(row.get("popularity", 50)),
                "release_decade": int(row.get("release_decade", 2010)),
                "mood_tag": row.get("mood_tag", "balanced"),
                "instrumentalness": float(row.get("instrumentalness", 0.5)),
                "liveness": float(row.get("liveness", 0.3)),
                "speechiness": float(row.get("speechiness", 0.1)),
            }
            for row in reader
        ]
    return songs


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
) -> List[Tuple[Dict, float, str]]:
    """Score all songs, apply diversity penalty, and return top k."""
    candidates: List[Dict] = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        candidates.append({"song": song, "score": score, "reasons": reasons})

    ranked: List[Tuple[Dict, float, str]] = []
    selected_artists: Dict[str, int] = {}
    selected_genres: Dict[str, int] = {}
    artist_penalty = float(user_prefs.get("artist_diversity_penalty", 1.1))
    genre_penalty = float(user_prefs.get("genre_diversity_penalty", 0.35))

    while candidates and len(ranked) < k:
        best_index = -1
        best_adjusted_score = float("-inf")
        best_penalty_note = ""

        for index, item in enumerate(candidates):
            song = item["song"]
            base_score = float(item["score"])
            artist_seen = selected_artists.get(song["artist"], 0)
            genre_seen = selected_genres.get(song["genre"], 0)
            penalty = (
                artist_seen * artist_penalty
            ) + (
                genre_seen * genre_penalty
            )
            adjusted_score = base_score - penalty

            if adjusted_score > best_adjusted_score:
                best_adjusted_score = adjusted_score
                best_index = index
                if penalty > 0:
                    best_penalty_note = (
                        "diversity penalty "
                        f"(-{penalty:.2f}) for repeated artist/genre"
                    )
                else:
                    best_penalty_note = ""

        chosen = candidates.pop(best_index)
        chosen_song = chosen["song"]
        chosen_reasons = list(chosen["reasons"])
        if best_penalty_note:
            chosen_reasons.append(best_penalty_note)

        ranked.append(
            (
                chosen_song,
                best_adjusted_score,
                _format_explanation(chosen_reasons),
            )
        )
        selected_artists[chosen_song["artist"]] = (
            selected_artists.get(chosen_song["artist"], 0) + 1
        )
        selected_genres[chosen_song["genre"]] = (
            selected_genres.get(chosen_song["genre"], 0) + 1
        )

    return ranked


def recommend_songs_with_context(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    notes_path: str = "data/knowledge_notes.csv",
    log_path: str = "logs/recommendation_events.jsonl",
) -> List[Dict]:
    """Rank songs, retrieve context, estimate confidence, and log events."""
    is_valid, issues = validate_user_profile(user_prefs)
    if not is_valid:
        raise ValueError("Invalid user profile: " + "; ".join(issues))

    ranked = recommend_songs(user_prefs, songs, k=k)
    notes = _load_knowledge_notes(notes_path)
    selected_mode = str(user_prefs.get("mode", "genre-first")).lower()
    max_weight = sum(_mode_weights(selected_mode).values())

    enriched_results: List[Dict] = []
    for song, score, explanation in ranked:
        retrieved_notes = retrieve_supporting_notes(
            song,
            user_prefs,
            notes,
            top_n=2,
        )
        confidence = _confidence_from_score(
            score=score,
            max_score=max_weight,
            retrieval_hits=len(retrieved_notes),
        )
        enriched_results.append(
            {
                "song": song,
                "score": score,
                "confidence": confidence,
                "explanation": explanation,
                "retrieved_notes": retrieved_notes,
            }
        )

    _log_recommendation_event(
        profile=user_prefs,
        issues=issues,
        results=enriched_results,
        log_path=log_path,
    )
    return enriched_results


def score_song(user_prefs: Dict, song: Song | Dict) -> Tuple[float, List[str]]:
    """Calculate a score for one song and return the reasons behind it."""
    mode = str(user_prefs.get("mode", "genre-first")).lower()
    weights = _mode_weights(mode)

    genre = _song_value(song, "genre")
    mood = _song_value(song, "mood")
    energy = float(_song_value(song, "energy"))
    acousticness = float(_song_value(song, "acousticness"))
    popularity = int(_song_value(song, "popularity", 50))
    release_decade = int(_song_value(song, "release_decade", 2010))
    mood_tag = str(_song_value(song, "mood_tag", "balanced"))
    instrumentalness = float(_song_value(song, "instrumentalness", 0.5))
    liveness = float(_song_value(song, "liveness", 0.3))
    speechiness = float(_song_value(song, "speechiness", 0.1))

    score = 0.0
    reasons: List[str] = [f"scoring mode: {mode}"]

    favorite_genre = (
        user_prefs.get("genre")
        or user_prefs.get("favorite_genre")
    )
    favorite_mood = user_prefs.get("mood") or user_prefs.get("favorite_mood")
    target_energy = user_prefs.get("energy") or user_prefs.get("target_energy")
    likes_acoustic = user_prefs.get("likes_acoustic")
    target_popularity = float(user_prefs.get("target_popularity", 65))
    preferred_decade = int(user_prefs.get("preferred_decade", release_decade))
    preferred_tags = {
        str(tag).strip().lower()
        for tag in user_prefs.get("preferred_mood_tags", [])
    }
    target_instrumentalness = float(
        user_prefs.get("target_instrumentalness", 0.5)
    )
    target_liveness = float(user_prefs.get("target_liveness", 0.3))
    target_speechiness = float(user_prefs.get("target_speechiness", 0.1))

    if favorite_genre and genre == favorite_genre:
        score += weights["genre"]
        reasons.append(f"genre match (+{weights['genre']:.2f}): {genre}")

    if favorite_mood and mood == favorite_mood:
        score += weights["mood"]
        reasons.append(f"mood match (+{weights['mood']:.2f}): {mood}")

    if target_energy is not None:
        energy_difference = abs(energy - float(target_energy))
        energy_score = max(
            0.0,
            weights["energy"] - (energy_difference * (weights["energy"] * 2)),
        )
        score += energy_score
        reasons.append(
            "energy similarity "
            f"(+{energy_score:.2f}): "
            f"target {float(target_energy):.2f}, song {energy:.2f}"
        )

    if likes_acoustic is True:
        acoustic_score = acousticness * weights["acoustic"]
        score += acoustic_score
        reasons.append(
            "acoustic preference "
            f"(+{acoustic_score:.2f}): acousticness {acousticness:.2f}"
        )
    elif likes_acoustic is False:
        acoustic_score = (1.0 - acousticness) * weights["acoustic"]
        score += acoustic_score
        reasons.append(
            "less-acoustic preference "
            f"(+{acoustic_score:.2f}): acousticness {acousticness:.2f}"
        )

    popularity_gap = abs(popularity - target_popularity) / 100.0
    popularity_score = max(
        0.0,
        weights["popularity"] - (popularity_gap * weights["popularity"] * 2),
    )
    score += popularity_score
    reasons.append(
        "popularity similarity "
        f"(+{popularity_score:.2f}): "
        f"target {target_popularity:.0f}, song {popularity}"
    )

    decade_gap = min(abs(release_decade - preferred_decade), 30)
    decade_score = max(
        0.0,
        weights["decade"] - (decade_gap / 10.0) * 0.45,
    )
    score += decade_score
    reasons.append(
        "era similarity "
        f"(+{decade_score:.2f}): "
        f"target {preferred_decade}s, song {release_decade}s"
    )

    if preferred_tags and mood_tag.lower() in preferred_tags:
        score += weights["mood_tag"]
        reasons.append(
            f"mood tag match (+{weights['mood_tag']:.2f}): {mood_tag}"
        )

    instr_gap = abs(instrumentalness - target_instrumentalness)
    instr_score = max(
        0.0,
        weights["instrumentalness"]
        - instr_gap * weights["instrumentalness"] * 2,
    )
    score += instr_score
    reasons.append(
        "instrumentalness similarity "
        f"(+{instr_score:.2f}): "
        f"target {target_instrumentalness:.2f}, song {instrumentalness:.2f}"
    )

    live_gap = abs(liveness - target_liveness)
    live_score = max(
        0.0,
        weights["liveness"] - live_gap * weights["liveness"] * 2,
    )
    score += live_score
    reasons.append(
        "liveness similarity "
        f"(+{live_score:.2f}): "
        f"target {target_liveness:.2f}, song {liveness:.2f}"
    )

    speech_gap = abs(speechiness - target_speechiness)
    speech_score = max(
        0.0,
        weights["speechiness"] - speech_gap * weights["speechiness"] * 2,
    )
    score += speech_score
    reasons.append(
        "speechiness similarity "
        f"(+{speech_score:.2f}): "
        f"target {target_speechiness:.2f}, song {speechiness:.2f}"
    )

    return score, reasons


def _format_explanation(reasons: List[str]) -> str:
    """Convert scoring reasons into a user-facing explanation string."""
    return "Recommended because " + "; ".join(reasons) + "."


def _song_value(song: Song | Dict, key: str, default=None):
    """Read a field from either a Song dataclass or a song dictionary."""
    if isinstance(song, Song):
        return getattr(song, key, default)
    return song.get(key, default)


def _mode_weights(mode: str) -> Dict[str, float]:
    """Return a weight set for the selected scoring strategy."""
    strategies = {
        "genre-first": {
            "genre": 3.2,
            "mood": 2.2,
            "energy": 1.8,
            "acoustic": 1.0,
            "popularity": 0.9,
            "decade": 0.6,
            "mood_tag": 1.2,
            "instrumentalness": 0.6,
            "liveness": 0.4,
            "speechiness": 0.4,
        },
        "mood-first": {
            "genre": 2.0,
            "mood": 3.3,
            "energy": 1.6,
            "acoustic": 1.1,
            "popularity": 0.8,
            "decade": 0.5,
            "mood_tag": 1.5,
            "instrumentalness": 0.6,
            "liveness": 0.5,
            "speechiness": 0.4,
        },
        "energy-focused": {
            "genre": 1.6,
            "mood": 1.8,
            "energy": 3.6,
            "acoustic": 0.9,
            "popularity": 0.7,
            "decade": 0.4,
            "mood_tag": 1.0,
            "instrumentalness": 0.5,
            "liveness": 0.5,
            "speechiness": 0.5,
        },
    }
    return strategies.get(mode, strategies["genre-first"])


def _load_knowledge_notes(notes_path: str) -> List[Dict]:
    """Load retrieval notes used to support recommendation explanations."""
    path = Path(notes_path)
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        notes: List[Dict] = [
            {
                "note_id": row.get("note_id", "unknown"),
                "topic": row.get("topic", "general"),
                "tags": [
                    tag.strip().lower()
                    for tag in row.get("tags", "").split("|")
                    if tag.strip()
                ],
                "content": row.get("content", ""),
            }
            for row in reader
        ]
    return notes


def retrieve_supporting_notes(
    song: Dict,
    user_prefs: Dict,
    notes: List[Dict],
    top_n: int = 2,
) -> List[Dict]:
    """Simple retrieval step that selects relevant notes by tag overlap."""
    if not notes:
        return []

    query_tokens = {
        str(song.get("genre", "")).lower(),
        str(song.get("mood", "")).lower(),
        str(song.get("mood_tag", "")).lower(),
        str(
            user_prefs.get("genre")
            or user_prefs.get("favorite_genre")
            or ""
        ).lower(),
        str(
            user_prefs.get("mood")
            or user_prefs.get("favorite_mood")
            or ""
        ).lower(),
    }
    query_tokens = {token for token in query_tokens if token}

    scored_notes: List[Tuple[float, Dict]] = []
    for note in notes:
        if overlap := query_tokens.intersection(set(note.get("tags", []))):
            score = float(len(overlap))
            scored_notes.append((score, note))

    scored_notes.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "note_id": note["note_id"],
            "topic": note["topic"],
            "content": note["content"],
        }
        for _, note in scored_notes[:top_n]
    ]


def _confidence_from_score(
    score: float,
    max_score: float,
    retrieval_hits: int,
) -> float:
    """Estimate confidence from score strength and evidence coverage."""
    normalized_score = (
        0.0
        if max_score <= 0
        else max(0.0, min(1.0, score / max_score))
    )
    retrieval_bonus = min(0.2, 0.1 * retrieval_hits)
    confidence = max(0.0, min(1.0, normalized_score * 0.8 + retrieval_bonus))
    return round(confidence, 3)


def _log_recommendation_event(
    profile: Dict,
    issues: List[str],
    results: List[Dict],
    log_path: str,
) -> None:
    """Write one JSONL event for later reliability analysis."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "profile": profile,
        "validation_issues": issues,
        "results": [
            {
                "song_id": result["song"].get("id"),
                "title": result["song"].get("title"),
                "artist": result["song"].get("artist"),
                "score": round(float(result["score"]), 3),
                "confidence": result["confidence"],
                "evidence_note_ids": [
                    note["note_id"]
                    for note in result["retrieved_notes"]
                ],
            }
            for result in results
        ],
    }

    with path.open("a", encoding="utf-8") as output_file:
        output_file.write(json.dumps(payload) + "\n")
