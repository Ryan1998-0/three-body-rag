# Three Body New 10-Question Retest Scored Report 20260614-004818

## Scope

- Task: create a fresh set of 10 questions and retest the current repaired RAG pipeline.
- Question file: `evals/three_body_qwen/questions_new10_20260614.json`
- Model: `qwen2.5:7b`
- Top K: `5`
- Raw JSONL: `evals/three_body_qwen/three_body_35_raw_answers_20260614-004818.jsonl`
- Raw report: `evals/three_body_qwen/three_body_35_raw_report_20260614-004818.md`
- Test record: `test-records/qwen-rag-three-body-35q-20260614-004818.md`
- Unit test record: `test-records/test-record-20260614-004757.md`

## Run Result

- Completed: `10 / 10`
- Runtime errors: `0`
- Manual score: `29 / 50` = `58 / 100`

## New Questions

| ID | Question |
|---|---|
| NQ01 | 丁儀用檯球實驗想向汪淼說明什麼問題？ |
| NQ02 | 魏成研究三體問題時展現了什麼特殊能力或思考方式？ |
| NQ03 | 墨子的宇宙模型為什麼最後被證明是錯的？ |
| NQ04 | 《三體》遊戲中的三日連珠造成了什麼災難？ |
| NQ05 | 古箏行動為什麼要使用汪淼的納米材料飛刃？ |
| NQ06 | 審判日號上保存的關鍵資料是什麼，為什麼各方都想保住它？ |
| NQ07 | 智子除了干擾加速器之外，還能用哪些方式製造神跡？ |
| NQ08 | 1379號監聽員為什麼要警告地球不要回答三體世界？ |
| NQ09 | 葉文潔為什麼一開始認為紅岸發出的電波很難被外星文明聽見？ |
| NQ10 | 大史對三體危機的判斷和科學家有什麼不同？ |

## Manual Scoring

| ID | Score | Result | Notes |
|---|---:|---|---|
| NQ01 | 0/5 | Fail | Retrieval did not find the billiards passage. Expected: Ding Yi used the billiards thought experiment to illustrate that physics depends on stable, uniform laws; if outcomes varied randomly, physics would collapse. |
| NQ02 | 5/5 | Pass | Correctly explains Wei Cheng's evolutionary-algorithm style thinking and need for massive computation. |
| NQ03 | 0/5 | Fail | Retrieval found Mozi's model but not the failure reason. Expected: the model assumed the sun's motion could be simulated mechanically, but real Trisolaris motion remained unpredictable. |
| NQ04 | 5/5 | Pass | Correctly explains that the triple-sun alignment destroys civilization by pulling surface matter/atmosphere upward and ending the civilization. |
| NQ05 | 2/5 | Partial | Found Flying Blade material evidence but answered the fixing/pad detail, not the main reason: nanofilament could silently slice Judgment Day and kill onboard enemies quickly while preserving information. |
| NQ06 | 5/5 | Pass | Correctly identifies Trisolaran information on Judgment Day and why deleting it must be prevented. |
| NQ07 | 5/5 | Pass | Correctly lists film exposure, retina/vision effects, cosmic microwave background flicker, and dimensional unfolding. |
| NQ08 | 5/5 | Pass | Correctly explains that answering would locate Earth and lead to invasion/occupation. |
| NQ09 | 2/5 | Partial | Retrieved a technical reason related to solar shielding, but missed the broader source-supported point that Red Coast's direct signal was far too weak and noisy to be easily heard. |
| NQ10 | 0/5 | Fail | Retrieval drifted badly and confused Da Shi with a scientist; expected contrast: Da Shi relies on police/social intuition, practical pattern recognition, and operational thinking rather than purely theoretical scientific reasoning. |

## Diagnosis

1. The previous sparse-fact repair improved questions around known anchors, but new narrative questions still fail when the wording does not match existing alias anchors.
2. The weak spots are now:
   - analogy/explanation questions, such as Ding Yi's billiards experiment;
   - failure-cause questions, such as Mozi's model;
   - action-purpose questions, such as why Flying Blade was used in Operation Guzheng;
   - character-viewpoint questions, such as Da Shi versus scientists.
3. Current retrieval still favors nearby named entities over rhetorical intent. For NQ10 it confused `大史` with unrelated technical/scientific contexts.
4. This fresh test did not reach the previous 60-point target; it scored `58 / 100`.

## Next Repair Direction

1. Add generic retrieval anchors for analogy and demonstration questions:
   - detect `用...實驗想說明什麼`;
   - retrieve nearby explanation lines after the experiment.
2. Add action-purpose routing:
   - detect `為什麼要使用 X`;
   - prioritize passages describing goal/constraint before implementation details.
3. Add failure-cause routing:
   - detect `為什麼最後錯/失敗`;
   - retrieve chunks after the model/method introduction where contradiction/result appears.
4. Add character-viewpoint routing:
   - detect `某人和科學家有什麼不同`;
   - retrieve character dialogue and summary lines, not only entity mentions.
