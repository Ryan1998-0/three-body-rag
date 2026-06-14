# Three Body 15-Question Retest Scored Report 20260613-210339

## Scope

- Task: retest 15 questions with the repaired RAG architecture.
- Selected IDs: `Q01,Q04,Q05,Q07,Q09,Q10,Q11,Q12,Q13,Q14,Q16,Q17,Q18,Q19,Q20`
- Model: `qwen2.5:7b`
- Top K: `5`
- Raw JSONL: `evals/three_body_qwen/three_body_35_raw_answers_20260613-210339.jsonl`
- Raw report: `evals/three_body_qwen/three_body_35_raw_report_20260613-210339.md`
- Test record: `test-records/qwen-rag-three-body-35q-20260613-210339.md`

## Run Result

- Completed: `15 / 15`
- Runtime errors: `0`
- Verifier marked related: `9 / 15`
- Manual score: `37 / 75` = `49.3 / 100`

## Manual Scoring

| ID | Score | Result | Notes |
|---|---:|---|---|
| Q01 | 5/5 | Pass | Correctly connects Ye Wenjie losing faith in humanity to political violence, personal trauma, Silent Spring reflection, betrayal/political pressure, and later Red Coast decision. |
| Q04 | 5/5 | Pass | Correctly explains scientist suicides through collapse of confidence in basic physics, Yang Dong's note, accelerator anomalies, and sophon interference. |
| Q05 | 5/5 | Pass | Correctly places "physics does not exist" in Yang Dong's suicide note / scientific crisis / accelerator anomaly context. |
| Q07 | 2/5 | Partial | Mentions chaotic epochs, unpredictable suns, flying stars, and dehydration, but does not directly answer the exact first-game-entry astronomical phenomenon. |
| Q09 | 0/5 | Fail | Answer drifted to human civilization weaknesses / ETO instead of Trisolaris's root survival problem: unstable three-sun system and unpredictable chaotic eras. |
| Q10 | 0/5 | Fail | Retrieval failed; answer discusses generic Trisolaris facts instead of prediction methods such as divination/calculation, human-formation computer, and historical/scientific figures. |
| Q11 | 5/5 | Pass | Correctly summarizes ETO as supporting/awaiting Trisolaris intervention, with factions such as Adventists, Redemptionists, and Survivors. |
| Q12 | 5/5 | Pass | Correctly identifies Ye Wenjie's decisive Red Coast reply/invitation to the alien civilization. |
| Q13 | 0/5 | Fail | Retrieval contained listener evidence but verifier rejected it; final answer said unable to confirm. Expected: Trisolaran monitoring/listener system received Earth's message. |
| Q14 | 0/5 | Fail | Retrieval did not find the distance evidence. Expected: about four light-years / Alpha Centauri direction. |
| Q16 | 5/5 | Pass | Correctly states the warning: do not reply, or the sender will be located and invaded. |
| Q17 | 0/5 | Fail | Retrieval missed the official-purpose passage for Red Coast Base. |
| Q18 | 0/5 | Fail | Retrieval missed Mike Evans and Ye Wenjie's first-meeting context. |
| Q19 | 5/5 | Pass | Correctly explains that Earth's technology could grow rapidly enough to surpass and threaten Trisolaris by fleet arrival. |
| Q20 | 0/5 | Fail | Retrieval failed; answer drifted to evolutionary algorithm. Expected: historical/scientific figures appearing in the game to work on the three-body problem. |

## Diagnosis

1. The previous repair works well for Ye Wenjie arc, Red Coast reply, ETO, warning, and sophon-threat questions.
2. The weak area is still retrieval coverage for sparse factual questions. The system often fails when the answer is a short fact buried in a distant chapter.
3. Verifier behavior is inconsistent:
   - Q09 was a false positive: verifier accepted unrelated evidence and the deterministic answer policy produced a wrong answer.
   - Q13 was a false negative: retrieval contained listener evidence, but verifier rejected it.
4. The current alias/evidence expansion is still uneven. It covers Ye Wenjie-related arcs better than game-history, astronomy-distance, listener, Red Coast-purpose, and Evans-meeting facts.

## Next Repair Targets

1. Add generic sparse-fact retrieval support:
   - Detect question types like distance, first meeting, official purpose, who/which figures, and how a signal was received.
   - Use entity anchors plus predicate anchors, not only broad semantic query text.
2. Improve evidence diversification:
   - For each major entity, retrieve from multiple non-adjacent chapters instead of only the closest semantic chunk cluster.
   - Promote exact chunks containing rare terms such as `四光年`, `監聽員`, `伊文斯`, `紅岸基地`, `官方目的`, `人列計算機`, `馮·諾伊曼`, `秦始皇`, `哥白尼`, `牛頓`, `愛因斯坦`.
3. Harden verifier:
   - Reject answers when the final answer question focus does not match the original question focus.
   - Avoid Q09-style topic drift from Trisolaris survival problem to human civilization weakness.
   - Avoid Q13-style false rejection when direct answer evidence is already in retrieved lines.
