# First20 Sparse + Dense Refined-Keywords Semantic Rescore

- Date: 2026-06-15
- Workflow: `sparse_dense_refined_keywords`
- Raw answers: `evals/three_body_qwen/first20_closed_raw_answers_20260615-143440.jsonl`
- Alias report: `evals/three_body_qwen/first20_closed_scored_report_20260615-143440.md`
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
- Previous semantic score: `85 / 100`
- Net change: `0`

## Score Table

| ID | Semantic Score | Alias Score | Judgment |
| --- | ---: | ---: | --- |
| F20Q01 | 4/5 | 5/5 | Mostly correct setting: Cultural Revolution/Red Guard violence at Tsinghua, but the answer frames it as Hundred Days armed struggle rather than clearly as the criticism/struggle meeting. |
| F20Q02 | 5/5 | 5/5 | Correct: Silent Spring. |
| F20Q03 | 5/5 | 5/5 | Correct meaning: it identifies the letter as a serious political accusation tied to a reactionary text. |
| F20Q04 | 3/5 | 1/5 | Partially correct: it identifies the radar-peak military base context but does not name Red Coast Base. |
| F20Q05 | 5/5 | 5/5 | Correct: the celestial body is the Sun. |
| F20Q06 | 5/5 | 1/5 | Correct category: a pacifist from the Trisolaris world. The 1379 monitor identity is more specific than the question wording requires. |
| F20Q07 | 5/5 | 5/5 | Correct: do not answer, or Earth will be located and invaded. |
| F20Q08 | 0/5 | 0/5 | Opposite answer: says Ye Wenjie obeyed the warning, but she did not. |
| F20Q09 | 5/5 | 5/5 | Correct: physics never existed. |
| F20Q10 | 3/5 | 3/5 | Partially correct: identifies the stopped experiment/equipment, but not the broader nanomaterial/Flying Blade research class. |
| F20Q11 | 5/5 | 3/5 | Correct: 2.726K microwave background is semantically the 3K cosmic microwave background. |
| F20Q12 | 5/5 | 5/5 | Correct: Chaotic Era. |
| F20Q13 | 0/5 | 1/5 | Wrong concept: answers Three-Sun Syzygy instead of Stable Era. |
| F20Q14 | 5/5 | 4/5 | Correct: Three Suns in the Sky causes civilization destruction. |
| F20Q15 | 5/5 | 5/5 | Correct: three-body problem. |
| F20Q16 | 5/5 | 1/5 | Correct: Shen Yufei is closer to the Redemptionists; alias score is low because the answer correctly mentions she had once been in the Adventist core. |
| F20Q17 | 5/5 | 5/5 | Correct: Adventists want Trisolaris to destroy or punish humanity. |
| F20Q18 | 5/5 | 0/5 | Correct: nanofilament/Flying Blade cuts Judgment Day; ordinary steel cable is only described as support/fixation. |
| F20Q19 | 5/5 | 5/5 | Correct: proton. |
| F20Q20 | 5/5 | 5/5 | Correct: lock down human fundamental science. |

## Compared With Previous Semantic Rescore

Improved or clarified:

- F20Q05: now directly answers `Sun`.
- F20Q11: answer says `2.726K microwave background`, which is equivalent to the expected 3K microwave background.
- F20Q18: answer correctly distinguishes nanofilament as the cutting material and ordinary cable as support.

Regressed or weaker:

- F20Q04: no longer names `Red Coast Base`, only the radar-peak military base.
- F20Q13: still fails the Stable Era question, now answering Three-Sun Syzygy.
- F20Q08: still answers the opposite of the correct Ye Wenjie follow-up action.

## Remaining True Failures

- F20Q08: needs retrieval/QA handling for "warning vs later action" questions.
- F20Q13: needs better term-definition retrieval for `恆紀元`.
- F20Q10: needs stronger mapping from the stopped experiment to nanomaterial/Flying Blade research.
- F20Q04: needs the Red Coast Base name preserved when the retrieved context uses radar-peak/base descriptions.
