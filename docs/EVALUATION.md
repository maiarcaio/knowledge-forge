# Evaluation protocol

Do not call an answer “grounded” just because it contains a link. Build a small benchmark before adding more connectors.

## Corpus

Use three sources that can be shown publicly: one long founder interview, one technical tutorial, and several short public social examples. Keep personal sources local. The synthetic fixture in `tests/fixtures/` exists only for automated tests.

## Ten question checklist

1. What exact price was stated, and when?
2. How did the creator obtain the first customers?
3. What onboarding change was made?
4. Which action happened before the pricing decision?
5. What was explicitly stated versus inferred?
6. Which source discusses a named tool?
7. Find an obscure term from the middle of a long source.
8. Compare two sources and name one disagreement.
9. Identify a missing prerequisite rather than inventing it.
10. Export a cited answer and verify each timestamp opens the original source.

## Pass gate

For ten manually checked factual claims, at least nine must link to the exact supporting passage or timestamp. Record misses, caption failures, model choice, processing duration, and estimated model cost in the issue tracker or case-study report.
