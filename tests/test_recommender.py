from src.recommender import (
    Song,
    UserProfile,
    Recommender,
    validate_user_profile,
    recommend_songs_with_context,
)


def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_validate_user_profile_rejects_invalid_energy():
    is_valid, issues = validate_user_profile(
        {
            "genre": "pop",
            "mood": "happy",
            "energy": 1.5,
            "likes_acoustic": False,
            "mode": "genre-first",
        }
    )
    assert is_valid is False
    assert any("energy" in issue for issue in issues)


def test_recommend_songs_with_context_returns_confidence_and_evidence():
    songs = [
        {
            "id": 1,
            "title": "Test Pop Track",
            "artist": "Test Artist",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            "tempo_bpm": 120,
            "valence": 0.9,
            "danceability": 0.8,
            "acousticness": 0.2,
            "popularity": 85,
            "release_decade": 2010,
            "mood_tag": "uplifting",
            "instrumentalness": 0.1,
            "liveness": 0.3,
            "speechiness": 0.12,
        }
    ]
    user_prefs = {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.8,
        "likes_acoustic": False,
        "mode": "genre-first",
    }

    recommendations = recommend_songs_with_context(
        user_prefs=user_prefs,
        songs=songs,
        k=1,
        notes_path="data/knowledge_notes.csv",
        log_path="logs/test_recommendation_events.jsonl",
    )

    assert len(recommendations) == 1
    assert 0.0 <= recommendations[0]["confidence"] <= 1.0
    assert "retrieved_notes" in recommendations[0]
