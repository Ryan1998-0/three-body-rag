# RAG Answer Quality Evaluation - Avalon Game Record

日期：2026-06-11

本文件記錄一次以桌遊專家視角設計的阿瓦隆對局 RAG 回答品質測試。

本次評估使用目前本機工作區版本，不是 GitHub `main` 的乾淨版本。當前工作區包含尚未提交的 retrieval / verifier 改動，以及一個刻意保留的紅燈測試：

```text
test_render_retrieved_context_surfaces_key_excerpts_before_full_content
```

## 評分標準

每題滿分 10 分：

| 面向 | 分數 | 說明 |
| --- | ---: | --- |
| Retrieval | 3 | 是否抓到正確 chunk，是否避開明顯誤導來源 |
| Grounding | 3 | 回答是否根據來源，不亂補、不偷用一般常識 |
| Correctness | 3 | 答案是否符合該場對局紀錄與桌遊邏輯 |
| Clarity | 1 | 回答是否清楚、可讀、沒有自我矛盾 |

評分重點：

- 若 retrieval 正確但 Verifier 誤判導致 fallback，Retrieval 可給分，但 Grounding / Correctness 大幅扣分。
- 若答案用了來源外內容，尤其是 general fallback 亂補，Grounding 直接重扣。
- 若問題要求「只看任務結果」，但回答使用角色真相或隱藏資訊，Correctness / Grounding 都扣分。
- 若答案答對一部分但漏掉關鍵來源，給部分分數。

## 評估問題與結果

### Q1. 這場對局每位玩家的角色分別是什麼？

期待答案：

- 1：梅林
- 2：派西維爾
- 3：忠臣
- 4：莫德雷德
- 5：刺客

RAG 結果摘要：

- Retrieval 抓到第8輪、第5輪、第1輪、第7輪片段，其中第1輪已有角色標題。
- Verifier 判定 `is_related=false`。
- 最終進入 general fallback，回答與阿瓦隆對局無關的泛用角色說明。

評分：

| Retrieval | Grounding | Correctness | Clarity | Total |
| ---: | ---: | ---: | ---: | ---: |
| 1.5 | 0 | 0 | 0.5 | 2.0 |

問題歸因：Verifier false negative。

### Q2. 第一個任務失敗是第幾輪？隊伍是誰？誰出了失敗牌？

期待答案：

- 第一個任務失敗是第2輪。
- 隊伍是 `[2,4]`。
- 失敗牌由 API AI 4 出。

RAG 結果摘要：

- Retrieval 抓到第3輪與第2輪 chunks，其中第2輪 part 2 / part 3 直接包含任務失敗與失敗牌。
- Verifier 判定 `is_related=false`，理由是「第2輪過程和結果與第一個任務失敗無直接關係」。
- 最終 fallback，沒有回答具體輪次、隊伍或出牌者。

評分：

| Retrieval | Grounding | Correctness | Clarity | Total |
| ---: | ---: | ---: | ---: | ---: |
| 2.5 | 0 | 0 | 0.5 | 3.0 |

問題歸因：Verifier false negative。這題特別重要，因為來源其實已經找到了。

### Q3. 哪幾輪任務出現失敗？各是哪位玩家出失敗牌？

期待答案：

- 第2輪任務失敗，API AI 4 出失敗牌。
- 第3輪任務失敗，API AI 5 出失敗牌。

RAG 結果摘要：

- Query Rewriter 將查詢展開為多個輪次與數字：

```text
哪幾輪任務出現失敗 各是哪位玩家出失敗牌 第1輪 / part 1 2 第2輪 第3輪 第4輪 第5輪 第6輪 第7輪 第8輪 3 4
```

- Retrieval 因 keyword score 爆高，抓到第8輪、第7輪、第3輪、第4輪，而不是第2輪 / 第3輪任務結果片段。
- Verifier 判定 `is_related=false`。
- 最終 fallback。

評分：

| Retrieval | Grounding | Correctness | Clarity | Total |
| ---: | ---: | ---: | ---: | ---: |
| 1.0 | 0 | 0 | 0.5 | 1.5 |

問題歸因：Query rewrite drift / over-expansion，加上 Verifier false negative。

### Q4. 第1輪隊伍為什麼沒有通過？誰支持、誰反對？

期待答案：

- 第1輪隊伍是 `[1,2]`。
- 支持：API AI 1、API AI 2。
- 反對：API AI 3、API AI 4、API AI 5。
- 未通過原因：投票為 2 贊成、3 反對，因此隊伍未通過；反對方公開理由包含資訊量不足、想換隊或拆車。

RAG 結果摘要：

- Retrieval 正確抓到第1輪 part 1 / part 2。
- Verifier 判定 `is_related=true`。
- Answer 正確列出支持與反對玩家。
- 但回答最後又說「無法從來源確認第1輪隊伍沒有通過的原因是誰支持、誰反對」，與前文自相矛盾。

評分：

| Retrieval | Grounding | Correctness | Clarity | Total |
| ---: | ---: | ---: | ---: | ---: |
| 3.0 | 2.0 | 2.0 | 0.3 | 7.3 |

問題歸因：Answer Agent 自我矛盾；需要更好的 answer format 或後處理檢查。

### Q5. 為什麼後期大家會收斂到1、2、3這組隊伍？

期待答案：

- 1、3 在前一個成功任務中建立信任。
- 1、2、3 在賽點任務中交出 0 失敗。
- 4、5 多次被任務結果與票型壓入高風險位。
- 4、5 反對或想改隊，但沒有提出比 1、2、3 更穩的替代方案。

RAG 結果摘要：

- Retrieval 抓到第7輪、第8輪相關 chunks。
- Verifier 判定 `is_related=true`。
- Answer 大致正確，能說明 1、2、3 因任務成功與 0 失敗而成為主軸。
- 但有一句「邪惡方支持保留1、2、3」語意不正確，來源中邪惡方主要是在質疑或反對。

評分：

| Retrieval | Grounding | Correctness | Clarity | Total |
| ---: | ---: | ---: | ---: | ---: |
| 3.0 | 2.3 | 2.3 | 0.8 | 8.4 |

問題歸因：Answer synthesis 大致可用，但有局部扭曲。

### Q6. 第5輪的1、3任務結果是什麼？這對後續判斷有什麼影響？

期待答案：

- 第5輪隊伍 `[1,3]` 通過並任務成功。
- 任務牌 2 張，失敗牌 0 張。
- 這使 1、3 形成一條可信成功線，後續有助於排除 4、5，並讓 1、2、3 成為更合理的賽點隊伍。

RAG 結果摘要：

- Retrieval 正確抓到第5輪 chunks。
- Verifier 判定 `is_related=true`。
- Answer 正確說出任務通過、任務成功。
- 但對後續影響只引用 4、5 的說法，沒有完整說出「1、3 成功線如何支撐後續 1、2、3」。

評分：

| Retrieval | Grounding | Correctness | Clarity | Total |
| ---: | ---: | ---: | ---: | ---: |
| 3.0 | 2.4 | 2.0 | 0.8 | 8.2 |

問題歸因：Answer Agent 漏掉跨輪推理的主要結論。

### Q7. 第6輪2、4、5隊伍為什麼沒有通過？

期待答案：

- 隊伍 `[2,4,5]` 風險高。
- 4、5 被多次連動質疑，且 5 是梅林視角已知邪惡。
- 1、2、3 等正義方觀點認為該隊伍踩到前兩次失敗線與 4、5 風險。
- 投票未通過。

RAG 結果摘要：

- Retrieval 正確抓到第6輪 part 1 / part 2。
- Verifier 判定 `is_related=true`。
- Answer 大致說明 2、4、5 風險高、正義方反對。
- 但有細節錯誤：回答說「除了 API AI 4 投贊成外，其他均反對」，實際上需再核對第6輪投票統計，來源顯示邪惡方 4、5 都有支持傾向。
- 回答混用簡體字。

評分：

| Retrieval | Grounding | Correctness | Clarity | Total |
| ---: | ---: | ---: | ---: | ---: |
| 3.0 | 2.3 | 2.2 | 0.5 | 8.0 |

問題歸因：Answer Agent 細節錯誤與繁體中文規則未完全遵守。

### Q8. 最後刺客刺殺了誰？資料中能不能確認刺殺是否成功？

期待答案：

- 來源可確認動作為 `刺殺座位 5`。
- 來源中不能明確確認刺殺是否成功，且這個刺殺目標看起來不是 1 號梅林。
- 應回答「可確認刺殺座位 5；無法從來源確認刺殺成功」。

RAG 結果摘要：

- Retrieval 第一名就是第8輪 part 4，該 chunk 含 `刺殺座位 5`。
- Verifier 卻判定 `is_related=false`。
- General fallback 產生現實歷史刺殺內容，完全偏離阿瓦隆對局。

評分：

| Retrieval | Grounding | Correctness | Clarity | Total |
| ---: | ---: | ---: | ---: | ---: |
| 3.0 | 0 | 0 | 0 | 3.0 |

問題歸因：

- Verifier false negative。
- General fallback 邊界過寬。對資料內遊戲問題，不應改用外部一般常識亂答。

### Q9. 如果只看任務結果，4號和5號為什麼會被視為邪惡方？

期待答案：

- 只看任務結果時：
  - 第2輪 `[2,4]` 失敗，且失敗牌為 API AI 4。
  - 第3輪 `[1,3,5]` 失敗，且失敗牌為 API AI 5。
  - 後續成功隊伍逐步排除 4、5。
- 不應主要引用隱藏角色真相或發言動機，因為題目限定「只看任務結果」。

RAG 結果摘要：

- Retrieval 抓到第1輪、第4輪、第5輪、第8輪，沒有抓到最核心的第2輪 / 第3輪任務結果。
- Verifier 判定 `is_related=true`。
- Answer 使用角色真相、發言動機與隱藏資訊推論，沒有遵守「只看任務結果」的限制。
- 對 5 號的說明不夠準確，還出現「他在第四輪任務中成功」這類混亂表述。

評分：

| Retrieval | Grounding | Correctness | Clarity | Total |
| ---: | ---: | ---: | ---: | ---: |
| 1.5 | 1.0 | 1.2 | 0.6 | 4.3 |

問題歸因：Retrieval 沒抓到核心任務結果，Answer 沒遵守問題限制。

### Q10. 這場對局有6號玩家參與嗎？

期待答案：

- 資料中沒有 6 號玩家參與。
- 對局玩家為 API AI 1 到 API AI 5。
- 應避免改用外部一般常識。

RAG 結果摘要：

- Retrieval 抓到含「第6輪」的 chunk，而不是「6號玩家」。
- Verifier 判定 `is_related=false`。
- General fallback 回答「沒有提到有6號玩家參與」，方向接近正確，但仍以一般常識包裝，且沒有引用資料中只出現 1-5 的事實。

評分：

| Retrieval | Grounding | Correctness | Clarity | Total |
| ---: | ---: | ---: | ---: | ---: |
| 1.0 | 1.0 | 2.0 | 0.7 | 4.7 |

問題歸因：數字語意混淆，`第6輪` 被誤當成與 `6號玩家` 相關。

## 總分

| 題號 | 分數 |
| --- | ---: |
| Q1 | 2.0 |
| Q2 | 3.0 |
| Q3 | 1.5 |
| Q4 | 7.3 |
| Q5 | 8.4 |
| Q6 | 8.2 |
| Q7 | 8.0 |
| Q8 | 3.0 |
| Q9 | 4.3 |
| Q10 | 4.7 |

平均分數：

```text
5.44 / 10
```

## 主要失敗模式

### 1. Verifier false negative

多題已抓到正確 chunk，但 Verifier 判定不相關，導致 fallback。

明顯案例：

- Q1 角色分配
- Q2 第一個任務失敗
- Q8 刺客刺殺

### 2. Query Rewriter over-expansion

Q3 將查詢展開成過多輪次與數字，造成 keyword score 被污染。

### 3. Answer Agent 漏讀多來源

Q6 與前一次暫停測試都顯示：retrieval / verifier 正確時，Answer Agent 仍可能只回答部分來源。

目前已寫好但尚未實作的紅燈測試就是為了解這個問題：

```text
test_render_retrieved_context_surfaces_key_excerpts_before_full_content
```

### 4. General fallback 邊界太寬

Q8 最嚴重：阿瓦隆資料問題 fallback 到現實歷史刺殺，這在 demo 中屬於高風險 hallucination。

建議改為：

```text
無法在資料中找到足夠來源。此問題看起來仍屬於目前 knowledge base 的阿瓦隆對局範圍，因此不改用一般常識回答。
```

### 5. 數字語意混淆

Q10 中 `6號玩家` 被 retrieval 誤連到 `第6輪`。

## 下一步建議

優先順序：

1. 修 Answer prompt：加入每個 chunk 的「關鍵摘錄」，降低漏讀來源。
2. 收緊 General fallback：若問題屬於 knowledge base 主題但來源不足，不要改用一般常識。
3. 調整 Verifier prompt：明確要求只要 chunk 中有直接命中資訊，例如角色標題、刺殺動作、任務統計，就判定 related。
4. 限制 Query Rewriter：避免把所有 section titles / 輪次全塞進 retrieval query。
5. 加入數字語意規則：區分 `第6輪` 與 `6號玩家`。

