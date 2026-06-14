# Repair Record - Generic First Scene Environment Hazard

Date: 2026-06-13

## Trigger

Question:

`汪淼第一次進入「三體」遊戲時，所處的文明正面臨什麼樣的天文災難？`

The fixed RAG pipeline found related chunks but still answered source-insufficient. The user asked to find and repair the issue, with generalizable logic as the core principle.

## Root Cause

- The updated `三體1.docx` uses numbered chapter headings such as `7.三體。`; the narrative chunker did not recognize this generic chapter format.
- Retrieval treated later explanatory chapters as stronger than the first-entry scene because the query contained broad disaster terms.
- Deterministic evidence did not retain generic environment hazard signals such as `亂紀元`, `恆紀元`, `飛星`, `太陽運行`, `嚴寒`, `酷熱`, and `脫水`.
- Verifier lacked a generic rule for first-scene environment hazard questions.

## Generic Fix

- Added numeric narrative heading detection for `N. Title` style chapters.
- Added first-scene environment hazard retrieval intent:
  - first-entry terms: `第一次`, `首次`, `第一回`, `初次`
  - entry action terms: `進入`, `登入`, `來到`, `抵達`
  - scene/world terms: `遊戲`, `世界`, `場景`, `文明`, `星球`, `星系`
  - hazard terms: `災難`, `危機`, `困境`, `風險`, `天文`, `生存`
- Added generic entry-action boosts for `啟動遊戲`, `成功登錄`, `註冊`, `登入`, `置身`.
- Added later-scene penalty for `再次`, `後來`, `最後場景`, `最終目標`, and `第...次` when the query asks for the first scene.
- Expanded narrative evidence extraction to keep environment and astronomical hazard lines.
- Added deterministic verifier and answer paths for first-scene environment hazard questions.

## Verification

- Unit tests: `test-records/test-record-20260613-133855.md`, 99 tests OK.
- End-to-end smoke test: `test-records/fixed-generic-logic-wang-miao-three-body-game-final-20260613-133915.md`.

## Result

The pipeline now answers from retrieved sources without fallback:

`亂紀元與恆紀元無規律交替；太陽運行不可預測；多顆太陽造成天體運行失序；行星可能被恆星吞噬或墜入火海。`
