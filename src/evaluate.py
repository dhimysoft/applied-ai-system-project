"""Evaluation harness for reliability testing."""

from __future__ import annotations

try:
    from .main import EVALUATION_PROFILES
    from .recommender import load_songs, recommend_songs_with_context
except ImportError:
    from main import EVALUATION_PROFILES
    from recommender import load_songs, recommend_songs_with_context


def run_evaluation() -> dict:
    songs = load_songs("data/songs.csv")

    checks = [
        {
            "profile": "High-Energy Pop",
            "assertion": (
                lambda results: results[0]["song"]["genre"]
                in {"pop", "indie pop"}
            ),
            "description": "top song should be pop-adjacent",
        },
        {
            "profile": "Chill Lofi",
            "assertion": lambda results: results[0]["song"]["genre"] == "lofi",
            "description": "top song should be lofi",
        },
        {
            "profile": "Deep Intense Rock",
            "assertion": (
                lambda results: results[0]["song"]["genre"]
                in {"rock", "metal"}
            ),
            "description": "top song should be rock/metal",
        },
        {
            "profile": "Adversarial Conflict",
            "assertion": lambda results: len(results) == 5,
            "description": (
                "system should still return top-5 under conflicting "
                "preferences"
            ),
        },
    ]

    passed = 0
    total = len(checks)
    confidence_values: list[float] = []

    print("\nReliability Evaluation\n")
    for index, check in enumerate(checks, start=1):
        profile_name = check["profile"]
        prefs = EVALUATION_PROFILES[profile_name]
        results = recommend_songs_with_context(prefs, songs, k=5)
        confidence_values.extend(result["confidence"] for result in results)

        outcome = bool(check["assertion"](results))
        if outcome:
            passed += 1

        print(
            f"{index}. {profile_name}: {'PASS' if outcome else 'FAIL'} "
            f"({check['description']})"
        )
        print(
            f"   Top pick: {results[0]['song']['title']} | "
            f"score={results[0]['score']:.2f} | "
            f"conf={results[0]['confidence']:.2f}"
        )

    avg_conf = (
        sum(confidence_values) / len(confidence_values)
        if confidence_values
        else 0.0
    )
    print("\nSummary")
    print(f"- Passed: {passed}/{total}")
    print(f"- Average confidence: {avg_conf:.3f}")

    return {
        "passed": passed,
        "total": total,
        "average_confidence": round(avg_conf, 3),
    }


if __name__ == "__main__":
    run_evaluation()
