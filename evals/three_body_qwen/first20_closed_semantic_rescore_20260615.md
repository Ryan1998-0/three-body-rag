# First20 Closed Semantic Rescore

- Date: 2026-06-15
- Scope: first volume only
- Base raw answers: `evals/three_body_qwen/first20_closed_raw_answers_20260615-104328.jsonl`
- F20Q16 replacement raw answer after retrieval fix: `evals/three_body_qwen/first20_closed_raw_answers_20260615-114154.jsonl`
- Scoring mode: semantic lenient manual review

## Scoring Standard

- 5: The answer means the same thing as the standard answer. Synonyms, abbreviations, and alternate wording count as correct.
- 4: Core answer is correct, but one important qualifier is misleading or weak.
- 3: Partially correct; points to the right area but does not clearly answer the target.
- 2: Only a small related fragment is correct.
- 1: Mostly wrong, with one relevant clue.
- 0: Opposite answer, wrong concept, or no usable answer.

Expression quality, shortness, or missing decorative detail is not penalized. The score focuses on whether the meaning is correct.

## Result

- Total score: `85 / 100`
- Compared with deterministic alias report: `76 / 100`
- Difference: `+9`

## Score Table

| ID | Semantic Score | Deterministic Score | Judgment |
| --- | ---: | ---: | --- |
| F20Q01 | 5/5 | 4/5 | Occasion is correct: Cultural Revolution criticism/struggle meeting with Red Guards. It says injured rather than explicitly dead, but the asked target is the occasion. |
| F20Q02 | 5/5 | 5/5 | Correct: The book is Silent Spring. |
| F20Q03 | 5/5 | 2/5 | "Class enemy against the people" is a political accusation, so the meaning matches the political-problem nature. |
| F20Q04 | 5/5 | 5/5 | Correct: Red Coast Base. |
| F20Q05 | 2/5 | 5/5 | The answer mentions solar-radiation research but explicitly says the source did not identify the specific celestial body, so it fails to directly answer "the Sun." |
| F20Q06 | 5/5 | 1/5 | The question asks "which type of person"; "a pacifist from the Trisolaris world" is semantically correct even though it does not name 1379 monitor. |
| F20Q07 | 5/5 | 5/5 | Correct: Do not answer, or Earth will be located. |
| F20Q08 | 0/5 | 0/5 | Opposite answer: says Ye Wenjie obeyed the warning, but she did not. |
| F20Q09 | 5/5 | 5/5 | Correct: Physics never existed. |
| F20Q10 | 3/5 | 3/5 | Partially correct: identifies the stopped experiment/equipment, but not the broader nanomaterial/Flying Blade research class. |
| F20Q11 | 5/5 | 5/5 | Correct: 3K cosmic microwave background radiation. |
| F20Q12 | 5/5 | 5/5 | Correct: Chaotic Era. |
| F20Q13 | 0/5 | 1/5 | Wrong concept: answers "sophon era" instead of Stable Era. |
| F20Q14 | 5/5 | 4/5 | Correct: Three suns in the sky destroys civilization, not continuation. |
| F20Q15 | 5/5 | 5/5 | Correct: Three-body problem. |
| F20Q16 | 5/5 | 5/5 | Correct after retrieval fix: Shen Yufei is closer to the Redemptionists. |
| F20Q17 | 5/5 | 5/5 | Correct meaning: Adventists are not trying to save humanity; they accept sacrificing/destroying the human world for Trisolaris. |
| F20Q18 | 5/5 | 5/5 | Correct: nanofilament/Flying Blade, not ordinary steel cable. |
| F20Q19 | 5/5 | 5/5 | Correct: proton. |
| F20Q20 | 5/5 | 5/5 | Correct: lock down human fundamental science. |

## Main Changes From Alias Scoring

- F20Q03 rises from `2/5` to `5/5`: the wording does not say "political problem," but "class enemy against the people" is semantically a political accusation.
- F20Q06 rises from `1/5` to `5/5`: "pacifist" answers the asked category, while `1379 monitor` is a more specific identity.
- F20Q14 rises from `4/5` to `5/5`: the answer clearly chooses destruction; it should not lose points for not explicitly saying "not continuation."
- F20Q01 rises from `4/5` to `5/5`: the occasion is correct, and the question asks the occasion.
- F20Q05 falls from `5/5` to `2/5`: the answer hedges and fails to directly say "the Sun."
- F20Q13 falls from `1/5` to `0/5`: "sophon era" is the wrong concept.

## Remaining True Failures

- F20Q08: QA answers the opposite of the standard answer.
- F20Q13: Retrieval/QA leads to the wrong term.
- F20Q05: answer does not directly name the Sun despite nearby source context.
- F20Q10: answer is only partially mapped to nanomaterial/Flying Blade research.
