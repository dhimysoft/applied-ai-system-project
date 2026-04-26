# Model Card: AI Music Recommender System

## 1. Model Overview
This project uses a rule-based recommendation system to suggest songs from a curated catalog.

The recommendation logic uses:
- mood preference
- energy preference
- genre preference

It is not a trained machine learning model. Instead, it applies explicit scoring rules to rank songs by how well they match user inputs.

## 2. Intended Use
Intended use:
- recommend songs for users based on stated preferences
- demonstrate applied AI engineering in a transparent, explainable CLI system
- support classroom and portfolio use cases

Not intended use:
- high-stakes decision-making
- production personalization at large scale

## 3. Limitations
- Small dataset size limits recommendation coverage and variety.
- This is not a trained ML model, so it cannot learn from user behavior automatically.
- Rules may not generalize well to users with uncommon or conflicting preferences.

## 4. Bias and Risks
- Dataset bias risk: if certain genres are overrepresented, recommendations may repeatedly favor those genres.
- Feature-weight risk: energy may be over-weighted relative to genre in some profiles, leading to less intuitive results.
- Simplicity risk: rule-based systems can miss nuanced context that a richer model might capture.

## 5. Evaluation
The system is evaluated through reliability testing with multiple predefined user profiles.

Evaluation approach:
- run predefined preference scenarios
- generate top recommendations for each scenario
- check if recommendations align with target mood or genre
- report match summary results

Match summary:
- counts how many of the top recommendations match expected mood or genre
- reported in an easy-to-read format such as 2/3 or 3/3

This provides a practical quality signal even without a full ML benchmark suite.

## 6. Ethical Considerations
- Transparency: each recommendation includes a Why explanation so users can understand system behavior.
- Honest framing: recommendations are presented as suggestions, not objective truths.
- Misleading output mitigation: reliability checks and clear explanations reduce risk of overclaiming system capability.

Potential misuse examples:
- Treating recommendation output as authoritative emotional assessment.
- Re-using mood input to infer sensitive personal traits outside the recommendation context.
- Over-trusting low-confidence recommendations as equally reliable as high-confidence ones.

Concrete prevention controls:
- Input validation rejects invalid profiles and prevents malformed preference payloads.
- Confidence scoring is exposed in output so users can judge recommendation certainty.
- Low-confidence fallback behavior improves stability under conflicting or weak signals.
- System scope is explicitly constrained to entertainment recommendation, not diagnosis or high-stakes support.

## 7. Future Improvements
- Replace or extend rules with an ML-based ranking model.
- Expand to a larger, more diverse song dataset.
- Add personalization based on interaction history and feedback loops.
- Add fairness and diversity evaluation metrics for stronger governance.

## Reflection
This project reinforced that applied AI quality comes from system design, not only model complexity. Even with a rule-based approach, transparency, reliability checks, and clear communication significantly improve trust and usability.

### AI-Assisted Development Reflection
AI tooling (Copilot/LLM support) was used as a coding collaborator during implementation and review.

One helpful contribution:
- Suggested integrating retrieval-aware recommendations into the main runtime flow and adding stage logs, which improved observability and evaluator traceability.

One incorrect contribution and correction:
- An AI suggestion initially referenced evaluation profile data before the shared constant existed, creating a broken evaluation dependency.
- This was corrected by defining shared evaluation profiles in the main module and validating with pytest plus the evaluation harness.
