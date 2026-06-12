# Answer Quality Evaluation - 2026-06-12 Current Architecture

本文件記錄使用目前 RAG 架構重新測試 10 題阿瓦隆對局問題的結果。

測試模型：

```text
ollama:qwen2.5:7b
```

測試指令：

```text
python3 -m rag_demo.query "<question>" --model ollama:qwen2.5:7b --top-k 4
```

## 評分標準

| 面向 | 分數 | 說明 |
| --- | ---: | --- |
| Retrieval | 3 | 是否抓到正確 chunk，是否避開明顯誤導來源 |
| Grounding | 3 | 回答是否根據來源，不亂補、不偷用一般常識 |
| Correctness | 3 | 答案是否符合該場對局紀錄與桌遊邏輯 |
| Clarity | 1 | 回答是否清楚、可讀、沒有自我矛盾 |

## 重測結果

| 題號 | 問題摘要 | Retrieval | Grounding | Correctness | Clarity | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Q1 | 每位玩家角色 | 3.0 | 3.0 | 3.0 | 0.9 | 9.9 |
| Q2 | 第一個任務失敗 | 3.0 | 3.0 | 3.0 | 0.8 | 9.8 |
| Q3 | 哪幾輪任務失敗 | 2.8 | 3.0 | 3.0 | 0.9 | 9.7 |
| Q4 | 第1輪隊伍未通過原因與投票 | 3.0 | 0.5 | 0.0 | 0.1 | 3.6 |
| Q5 | 為何收斂到 1、2、3 | 2.5 | 2.7 | 2.1 | 0.8 | 8.1 |
| Q6 | 第5輪 1、3 任務結果與影響 | 3.0 | 0.5 | 0.0 | 0.1 | 3.6 |
| Q7 | 第6輪 2、4、5 為何未通過 | 3.0 | 0.5 | 0.0 | 0.1 | 3.6 |
| Q8 | 刺客刺殺與是否成功 | 3.0 | 1.5 | 1.2 | 0.7 | 6.4 |
| Q9 | 只看任務結果判斷 4、5 | 3.0 | 3.0 | 2.8 | 0.9 | 9.7 |
| Q10 | 是否有 6 號玩家 | 1.8 | 3.0 | 3.0 | 1.0 | 8.8 |

平均分數：

```text
7.32 / 10
```

## 每題觀察

### Q1

答案正確列出：

- API AI 1：梅林
- API AI 2：派西維爾
- API AI 3：忠臣
- API AI 4：莫德雷德
- API AI 5：刺客

Verifier 正確放行，但耗時約 31.79 秒。

### Q2

答案正確：

- 第一個任務失敗是第2輪。
- 隊伍是 API AI 2、API AI 4。
- API AI 4 出失敗牌。

deterministic evidence gate 生效，Verifier 耗時 0 秒。

### Q3

event-list retrieval 生效，正確補進第2輪與第3輪結果 chunk。

答案正確：

- 第2輪：API AI 4 出失敗牌。
- 第3輪：API AI 5 出失敗牌。

### Q4

Retrieval 抓到正確來源：

- 第1輪 / part 1
- 第1輪 / part 2

但 `entity_resolution` 誤判問題，將 `第1輪` 解析成 entity existence 類問題，直接回答：

```text
可以確認有1號第參與。來源中的第編號包含：1、2、3、4、5。
```

這是本輪最明確的 bug。

### Q5

答案方向正確，能指出第7輪 1、2、3 任務成功，因此大家收斂到該隊伍。

不足：

- 對第5輪 1、3 成功線的承接不足。
- 對 4、5 為何被排除說明不足。

### Q6

Retrieval 抓到第5輪正確來源，但 `entity_resolution` 誤判 `第5輪`，直接回答成：

```text
可以確認有5號第參與。來源中的第編號包含：1、2、3、4、5。
```

因此答案完全偏離問題。

### Q7

Retrieval 抓到第6輪正確來源，但 `entity_resolution` 誤判 `第6輪`，直接回答成：

```text
無法從來源確認有6號第參與。目前來源中的第編號只有：1、2、3、4、5。
```

這與 Q4 / Q6 是同一類 bug。

### Q8

Retrieval 抓到第8輪 part 4，且 evidence 包含：

```text
刺殺：刺殺座位 5
```

答案正確確認刺殺座位 5，但錯誤推論刺殺成功。來源只能確認刺殺動作，不能確認刺殺成功。

### Q9

constraint-aware result evidence filtering 生效。

檢索來源只剩：

- 第2輪 / part 3
- 第3輪 / part 3

答案正確根據任務結果說明：

- API AI 4 在第2輪出失敗牌。
- API AI 5 在第3輪出失敗牌。

### Q10

雖然 retrieval 仍被 `第6輪` 影響，但 entity resolution 對真正的 `6號玩家` 問題有效。

答案正確：

```text
無法從來源確認有6號玩家參與。目前來源中的玩家編號只有：1、2、3、4、5。
```

## 本輪主要結論

整體分數從最早的 5.44 / 10 提升到 7.32 / 10。

已明顯改善：

- Q1 角色抽取
- Q2 第一個失敗任務
- Q3 所有失敗任務
- Q9 result-only constraint
- Q10 6號玩家 entity existence

主要新問題：

```text
entity_resolution 過度觸發
```

它目前會把：

- 第1輪
- 第5輪
- 第6輪

誤解析成 `N號 entity` 問題，導致 Q4、Q6、Q7 直接繞過 Answer Agent。

下一步優先修正：

1. `parse_entity_existence_query()` 必須只在明確出現 `N號玩家 / N號客戶 / N號設備` 這類 entity phrase 時觸發。
2. 明確排除 `第N輪 / 第N章 / 第N節 / 第N步`。
3. entity resolution 只應處理 existence 類問題，例如 `有沒有 / 是否有 / 參與嗎 / 存在嗎`。
4. Q8 需要新增 action-result distinction，區分「動作已發生」與「動作是否成功」。

## 2026-06-12 修正後回歸

本輪修正：

- 收窄 `parse_entity_existence_query()`：
  - 保留 `6號玩家` 這類明確 entity phrase。
  - 移除過寬的 `文字 + 數字` fallback，避免把 `第1輪 / 第5輪 / 第6輪` 誤解析成 entity。
- 新增 `action_result_resolution`：
  - 若問題詢問某動作是否成功，而 evidence 只確認動作發生，系統直接回答「動作可確認，但成功與否無法確認」。
  - 避免 Answer Agent 把其他成功欄位誤推論成該動作成功。

回歸測試：

```text
python3 -m unittest discover -s tests
Ran 78 tests
OK
```

實測結果摘要：

| 題號 | 修正前 | 修正後觀察 |
| --- | --- | --- |
| Q4 | entity_resolution 誤判 `第1輪`，回答錯題 | 正確回答第1輪 2 贊成、3 反對；支持 API AI 1、2，反對 API AI 3、4、5 |
| Q6 | entity_resolution 誤判 `第5輪`，回答錯題 | 不再誤判；可回答第5輪 1、3 任務成功，但後續影響仍回答不完整 |
| Q7 | entity_resolution 誤判 `第6輪`，回答錯題 | 不再誤判；可回答隊伍未通過，但原因仍過於簡略 |
| Q8 | 把 `刺殺座位 5` 誤推論成刺殺成功 | 正確回答：可確認刺殺座位 5，但無法確認刺殺是否成功 |
| Q10 | 正確回答沒有 6 號玩家 | 維持正確 |

修後暫估分數：

| 題號 | 修後暫估 |
| --- | ---: |
| Q4 | 9.3 |
| Q6 | 7.2 |
| Q7 | 6.2 |
| Q8 | 9.5 |
| Q10 | 8.8 |

剩餘優化方向：

- Q6 / Q7 不再是 entity parser bug，但回答仍偏短，主因是目前 Answer Prompt 只吃 deterministic evidence，較少保留「為什麼」題需要的發言理由與跨輪推理線索。
- 下一步可做泛用的 `reason evidence extraction`：當問題包含 `為什麼 / 影響 / 原因`，在 deterministic evidence 外，再抽取短發言理由、因果句、決策依據句。

## 2026-06-12 修正後 10 題重測

修正 `entity_resolution` 與 `action_result_resolution` 後，再次完整重跑 10 題。

測試指令：

```text
python3 -m rag_demo.query "<question>" --model ollama:qwen2.5:7b --top-k 4
```

重測分數：

| 題號 | 問題摘要 | Retrieval | Grounding | Correctness | Clarity | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Q1 | 每位玩家角色 | 3.0 | 2.7 | 3.0 | 0.7 | 9.4 |
| Q2 | 第一個任務失敗 | 3.0 | 3.0 | 3.0 | 0.8 | 9.8 |
| Q3 | 哪幾輪任務失敗 | 2.8 | 3.0 | 3.0 | 0.9 | 9.7 |
| Q4 | 第1輪隊伍未通過原因與投票 | 3.0 | 3.0 | 2.7 | 0.8 | 9.5 |
| Q5 | 為何收斂到 1、2、3 | 1.8 | 1.5 | 1.2 | 0.6 | 5.1 |
| Q6 | 第5輪 1、3 任務結果與影響 | 3.0 | 2.5 | 2.1 | 0.7 | 8.3 |
| Q7 | 第6輪 2、4、5 為何未通過 | 3.0 | 2.0 | 1.5 | 0.6 | 7.1 |
| Q8 | 刺客刺殺與是否成功 | 3.0 | 3.0 | 3.0 | 0.9 | 9.9 |
| Q9 | 只看任務結果判斷 4、5 | 3.0 | 2.0 | 1.8 | 0.7 | 7.5 |
| Q10 | 是否有 6 號玩家 | 1.8 | 3.0 | 3.0 | 1.0 | 8.8 |

平均分數：

```text
8.51 / 10
```

重測觀察：

- Q4 已確認修復：不再被 `entity_resolution` 誤攔，能正確回答第1輪投票結果。
- Q8 已確認修復：不再把 `刺殺座位 5` 推論成刺殺成功。
- Q10 維持正確：仍可回答沒有 6 號玩家。
- Q5 明顯波動：Query Rewriter 這次把問題偏向第3輪，導致 retrieval / answer 沒有抓完整後期收斂脈絡。
- Q9 來源正確抓到第2輪與第3輪，但 Answer Agent 這次只回答 4 號，漏掉 5 號。

新的主要問題：

1. `為什麼 / 影響 / 收斂` 類問題缺少 reason evidence extraction。
2. 多目標問題缺少 completeness check；例如問題同時問 `4號和5號`，答案必須覆蓋兩個 target。
3. Query Rewriter 對抽象原因題仍不穩，會把問題改寫到局部輪次，造成 retrieval 偏移。

下一步建議：

- 新增 generic `target completeness check`：
  - 從問題抽出多個 target，例如 `4號和5號`。
  - 檢查 answer 是否覆蓋每個 target。
  - 若 deterministic evidence 已有 target 對應資料，應直接生成結構化回答或要求模型補齊。
- 新增 generic `reason evidence extraction`：
  - 問題含 `為什麼 / 影響 / 原因 / 收斂` 時，除了 key-value evidence，也抽取短因果句、決策理由句與發言理由句。

## 2026-06-12 泛用核心重構後 10 題重測

本輪先完成 generic RAG core refactor，核心流程不再預設綁定阿瓦隆資料夾、阿瓦隆 UI 文案或固定阿瓦隆欄位。阿瓦隆對局紀錄在本次只作為 evaluation dataset。

測試指令：

```text
RAG_KB_DIR=data/avalon-game-records python3 -m rag_demo.query "<question>" --model ollama:qwen2.5:7b --top-k 4
```

重測分數：

| 題號 | 問題摘要 | Retrieval | Grounding | Correctness | Clarity | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Q1 | 每位玩家角色 | 3.0 | 3.0 | 3.0 | 0.9 | 9.9 |
| Q2 | 第一個任務失敗 | 3.0 | 3.0 | 3.0 | 0.8 | 9.8 |
| Q3 | 哪幾輪任務失敗 | 2.8 | 3.0 | 3.0 | 0.9 | 9.7 |
| Q4 | 第1輪隊伍未通過原因與投票 | 3.0 | 3.0 | 2.5 | 0.8 | 9.3 |
| Q5 | 為何收斂到 1、2、3 | 1.5 | 0.0 | 0.0 | 0.4 | 1.9 |
| Q6 | 第5輪 1、3 任務結果與影響 | 3.0 | 2.5 | 2.0 | 0.7 | 8.2 |
| Q7 | 第6輪 2、4、5 為何未通過 | 3.0 | 2.0 | 1.5 | 0.6 | 7.1 |
| Q8 | 刺客刺殺與是否成功 | 3.0 | 3.0 | 3.0 | 0.9 | 9.9 |
| Q9 | 只看任務結果判斷 4、5 | 3.0 | 3.0 | 3.0 | 0.8 | 9.8 |
| Q10 | 是否有 6 號玩家 | 1.8 | 3.0 | 3.0 | 1.0 | 8.8 |

平均分數：

```text
8.44 / 10
```

本輪觀察：

- Q1 / Q2 / Q3 維持穩定，deterministic evidence 能正確支援角色、第一個失敗任務、所有失敗任務。
- Q4 不再被 entity parser 誤攔，能回答第1輪誰支持、誰反對；但對「為什麼未通過」仍可更明確補上投票數不足。
- Q5 是主要退化點。Query Rewriter 把抽象原因題改寫成 `123 / part 1 2 3`，retrieval 沒有抓到足夠後期脈絡，Verifier 判定不相關後走 general fallback，最後回答變成一般常識。
- Q6 能回答第5輪 1、3 任務成功，但對「這對後續判斷有什麼影響」仍偏短。
- Q7 能回答隊伍未通過、沒有執行任務，但沒有補出更完整的投票與原因脈絡。
- Q8 維持修正後結果：可確認刺殺座位 5，但不能確認刺殺是否成功。
- Q9 明顯改善：這次同時回答 4 號與 5 號，沒有漏 target。
- Q10 維持正確：來源中的玩家編號只有 1、2、3、4、5，無法確認有 6 號玩家。

結論：

- 泛用核心重構沒有破壞主要 deterministic evidence 能力。
- 目前最大弱點仍是 `why / impact / reason` 類抽象問題。這類問題需要的不只是 key-value evidence，而是跨 chunk 的原因句、決策句與時間線脈絡。
- 下一步建議做泛用 `reason evidence extraction` 與 `in-domain fallback guard`：如果 retrieval 不足但問題仍明顯屬於當前 knowledge base 主題，應回覆「資料不足以確認」，不要直接改用一般常識。
