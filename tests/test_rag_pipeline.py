import unittest
import inspect
from pathlib import Path
from tempfile import TemporaryDirectory

from rag_demo.chunking import chunk_markdown
from rag_demo.chunking import chunk_narrative_text, chunk_sectioned_record_text, chunk_sectioned_text, load_knowledge_base_chunks
from rag_demo.config import RagConfig, resolve_project_path
from rag_demo.action_result_resolution import answer_action_result
from rag_demo import embeddings as embeddings_module
from rag_demo.embeddings import chunk_to_embedding_text, embed_texts, load_embedding_matrix, save_embedding_matrix
from rag_demo.entity_aliases import expand_query_with_aliases
from rag_demo.evidence_policy import build_evidence_policy, has_answerable_event_evidence, sequence_number, should_include_evidence_line
from rag_demo.entity_resolution import answer_entity_existence, extract_entity_numbers, parse_entity_existence_query
from rag_demo.event_list_retrieval import find_event_list_chunks, find_result_constrained_chunks, merge_event_list_chunks
from rag_demo.evidence_extraction_agent import build_evidence_extraction_prompt, render_evidence_context
from rag_demo.index_store import load_index, save_index
from rag_demo.keyword_extraction import parse_keywords_output
from rag_demo.ollama_client import build_ollama_payload
from rag_demo.model_providers import (
    build_anthropic_payload,
    build_openai_payload,
    parse_model_spec,
)
from rag_demo.prompting import build_answer_prompt, render_retrieved_context
from rag_demo.qa_agent import build_qa_prompt
from rag_demo.question_extraction import parse_question_output
from rag_demo.context_summary import build_context_summary_prompt, build_deterministic_context_summary, extract_deterministic_evidence, summarize_retrieved_context
from rag_demo.general_answer import build_general_answer_prompt
from rag_demo.graph_entities import extract_chunk_entities, extract_query_entities
from rag_demo.graph_retrieval import retrieve_graph_context
from rag_demo.query_classifier import classify_query
from rag_demo.query import _answer_from_deterministic_narrative_evidence, _bm25_dense_retrieval_query, _build_source_insufficient_answer, _build_sparse_dense_original_refined_query_variants, _build_sparse_dense_refined_query_variants, _build_three_agent_query_variants, _combine_original_and_rewritten_query, _diversify_retrieval_results, _expand_parent_chunks, _explicit_metadata_filters, _format_output, _format_three_agent_output, _hybrid_rerank_results, _rrf_merge_ranked_results, _rrf_parent_context_results, _select_retrieval_query, answer_question
from rag_demo.query_rewriter import build_rewrite_prompt, extract_retrieval_query, sanitize_retrieval_query
from rag_demo.retrieval_planner import build_retrieval_plan, extract_focus_terms
from rag_demo.retrieval_verifier import build_verifier_prompt, extract_evidence_candidates, parse_verifier_output
from rag_demo.retrieval_verifier import assess_deterministic_narrative_evidence, assess_query_evidence_overlap, assess_retrieval_confidence, verify_retrieval
from rag_demo.retrieval import embedding_search, hybrid_search, keyword_search
from rag_demo.web_app import is_home_path, render_home


SAMPLE_MARKDOWN = """# 員工手冊

## 1. 出勤與請假制度

### 1.1 上下班時間

公司標準上班時間為每日凌晨 4:00，下班時間為每日晚上 20:00。

### 1.2 事假

員工每一曆年可申請事假最多 90 天。事假期間公司給付原薪資的三分之一。

### 1.3 病假

員工每一曆年可申請病假最多 300 天。病假期間公司給付原薪資的三分之二。

## 2. 福利制度

### 2.1 三節獎金

公司於春節、端午節與中秋節發放三節獎金。每次三節獎金固定為新台幣 200 元。

### 2.2 交通補助

員工每月享有交通補助，上限為新台幣 8,000 元，採實支實付方式辦理。

### 2.3 生日福利

生日福利日當天，公司發放生日紅包禮金新台幣 200,000 元。

## 3. 離職流程

### 3.1 福利結算

離職員工之薪資、未休特休、交通補助與其他應結算項目，依公司制度及實際紀錄辦理。
"""

SAMPLE_SECTIONED_EVENT_RECORD = """Incident response replay log
格式：每個處理步驟都是一個 section；包含觀察、發言、動作與結果。

=== Step 1 ===

【Agent 1 / Incident Lead】

觀察：
付款服務錯誤率升高。

說明：
先切換到備援付款路由。

動作：
切換付款路由 [primary -> backup]

本步驟統計：
審核：2 同意，3 不同意
處理結果：未通過

========== Step 1 closed ==========

=== Step 2 ===

【Agent 2 / Operator】

觀察：
備援路由已準備完成。

說明：
重新送出切換申請。

動作：
啟用備援付款路由

本步驟統計：
審核：5 同意，0 不同意
處理結果：成功
錯誤明細：付款逾時已解除
"""


class RagPipelineTest(unittest.TestCase):
    def test_chunk_markdown_groups_content_by_section_heading(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")

        self.assertEqual(len(chunks), 7)
        self.assertEqual(chunks[0]["title"], "1.1 上下班時間")
        self.assertEqual(chunks[0]["parent_title"], "1. 出勤與請假制度")
        self.assertEqual(chunks[0]["source"], "sample.md")
        self.assertIn("凌晨 4:00", chunks[0]["content"])
        self.assertEqual(chunks[5]["title"], "2.3 生日福利")
        self.assertEqual(chunks[5]["parent_title"], "2. 福利制度")

    def test_chunk_sectioned_record_groups_content_by_section(self):
        chunks = chunk_sectioned_record_text(
            SAMPLE_SECTIONED_EVENT_RECORD,
            source="incident.txt",
            parent_title="Incident Response Record",
        )

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["parent_title"], "Incident Response Record")
        self.assertEqual(chunks[0]["title"], "Step 1")
        self.assertIn("切換付款路由 [primary -> backup]", chunks[0]["content"])
        self.assertEqual(chunks[1]["title"], "Step 2")
        self.assertIn("付款逾時已解除", chunks[1]["content"])

    def test_chunk_sectioned_text_splits_generic_delimited_sections(self):
        text = """Generic process notes

=== Phase 1 ===
Status: failed
Owner: Team A

=== Phase 2 ===
Status: completed
Owner: Team B
"""

        chunks = chunk_sectioned_text(text, source="process.txt", parent_title="Process Notes")

        self.assertEqual([chunk["title"] for chunk in chunks], ["Phase 1", "Phase 2"])
        self.assertEqual(chunks[0]["parent_title"], "Process Notes")
        self.assertIn("Status: failed", chunks[0]["content"])

    def test_resolve_project_path_reads_environment_override(self):
        env = {"RAG_KB_DIR": "/tmp/custom-kb"}

        self.assertEqual(resolve_project_path("RAG_KB_DIR", "data/raw", env=env), Path("/tmp/custom-kb"))

    def test_chunk_sectioned_record_can_split_long_section_with_stride_overlap(self):
        long_record = """=== Step 1 ===
""" + ("Step 1 observation content. " * 80)

        chunks = chunk_sectioned_record_text(
            long_record,
            source="incident.txt",
            parent_title="Incident Response Record",
            chunk_size=120,
            chunk_stride=80,
        )

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0]["title"], "Step 1 / part 1")
        self.assertEqual(chunks[1]["title"], "Step 1 / part 2")
        self.assertIn(chunks[0]["content"][80:120], chunks[1]["content"])

    def test_load_knowledge_base_chunks_reads_sectioned_text_files(self):
        with TemporaryDirectory() as temp_dir:
            kb_dir = Path(temp_dir)
            record_path = kb_dir / "incident-record-formatted.txt"
            record_path.write_text(SAMPLE_SECTIONED_EVENT_RECORD, encoding="utf-8")

            chunks = load_knowledge_base_chunks(kb_dir)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["title"], "Step 1")
        self.assertIn("incident-record-formatted.txt", str(chunks[0]["source"]))

    def test_chunk_narrative_text_keeps_front_matter_and_section_titles(self):
        text = """三體X  Isaiah

楔子

另一個星系，另一個時間。

幽靈創造了高山、丘陵、峽谷和平原。

上部

【銀河紀元409年 我們的星星】

雲天明想起程心，也看見另一個女子。
"""

        chunks = chunk_narrative_text(text, source="novel.txt", chunk_size=80, chunk_stride=60)
        titles = [chunk["title"] for chunk in chunks]

        self.assertEqual(chunks[0]["title"], "文件開頭 / metadata")
        self.assertIn("三體X  Isaiah", chunks[0]["content"])
        self.assertTrue(any(title.startswith("楔子") for title in titles))
        self.assertTrue(any("銀河紀元409年" in title for title in titles))

    def test_chunk_narrative_text_detects_numbered_chapter_headings(self):
        text = """1. 開端

第一章的正文。

7.遠星遊戲

主角第一次進入遠星遊戲，看到一個混亂世界。
"""

        chunks = chunk_narrative_text(text, source="novel.txt", chunk_size=120, chunk_stride=80)
        titles = [chunk["title"] for chunk in chunks]

        self.assertTrue(any(title.startswith("1. 開端") for title in titles))
        self.assertTrue(any(title.startswith("7.遠星遊戲") for title in titles))
        self.assertTrue(any("混亂世界" in chunk["content"] for chunk in chunks))

    def test_load_knowledge_base_chunks_uses_narrative_chunks_for_plain_novel_text(self):
        with TemporaryDirectory() as temp_dir:
            kb_dir = Path(temp_dir)
            novel_path = kb_dir / "novel.txt"
            novel_path.write_text(
                "三體X  Isaiah\n\n楔子\n\n另一個星系。\n\n上部\n\n【銀河紀元409年 我們的星星】\n\n雲天明坐在湖邊。",
                encoding="utf-8",
            )

            chunks = load_knowledge_base_chunks(kb_dir)

        self.assertEqual(chunks[0]["title"], "文件開頭 / metadata")
        self.assertTrue(any(chunk["parent_title"] == "Narrative Text" for chunk in chunks))
        self.assertTrue(any("楔子" in chunk["title"] for chunk in chunks))

    def test_expand_query_with_aliases_uses_trigger_rules(self):
        expanded = expand_query_with_aliases(
            "汪淼從事的是哪一項前沿技術研究？",
            alias_records=[
                {
                    "canonical": "納米材料",
                    "aliases": ["奈米材料"],
                    "related_terms": ["納米構件", "高能加速器"],
                    "triggers": [{"all": ["汪淼", "研究"]}],
                }
            ],
        )

        self.assertIn("納米材料", expanded)
        self.assertIn("奈米材料", expanded)
        self.assertIn("納米構件", expanded)

    def test_expand_query_with_aliases_supports_event_bridge_terms(self):
        expanded = expand_query_with_aliases(
            "為什麼小說中有多位頂尖科學家接連自殺？",
            alias_records=[
                {
                    "canonical": "科學家自殺事件",
                    "aliases": ["科學家自殺", "頂尖科學家自殺"],
                    "related_terms": ["楊冬", "物理學從來就沒有存在過", "三台新的高能加速器", "智子"],
                    "triggers": [{"all": ["科學家", "自殺"]}],
                }
            ],
        )

        self.assertIn("科學家自殺事件", expanded)
        self.assertIn("物理學從來就沒有存在過", expanded)
        self.assertIn("智子", expanded)

    def test_deterministic_evidence_uses_alias_expanded_query_terms(self):
        chunks = [
            {
                "source": "three-body-1.txt",
                "parent_title": "Narrative Text",
                "title": "4.三十八年後。 / part 7",
                "content": (
                    "大史又令汪淼像吃了蒼蠅一樣難受。"
                    "但他還是克制著回答了這個問題：我與科學邊界的接觸是從認識申玉菲開始的，"
                    "她是一名日籍華裔物理學家，我們是在今年年初的一次技術研討會上認識的。"
                ),
            }
        ]

        evidence = extract_deterministic_evidence(
            chunks,
            question="汪淼 科學邊界 申玉菲 技術研討會 通過她",
        )

        self.assertIn("申玉菲", evidence)
        self.assertIn("技術研討會", evidence)

    def test_deterministic_evidence_uses_event_bridge_terms(self):
        chunks = [
            {
                "source": "three-body-1.txt",
                "parent_title": "Narrative Text",
                "title": "10. 大史 / part 2",
                "content": (
                    "楊冬的遺書寫著：一切的一切都導向這樣一個結果："
                    "物理學從來就沒有存在過，將來也不會存在。"
                    "常偉思說，這些具體信息與世界上三台新的高能加速器建成後取得的實驗結果有關。"
                ),
            }
        ]

        evidence = extract_deterministic_evidence(
            chunks,
            question="科學家自殺事件 楊冬 遺書 物理學從來就沒有存在過 三台新的高能加速器",
        )

        self.assertIn("楊冬", evidence)
        self.assertIn("物理學從來就沒有存在過", evidence)
        self.assertIn("高能加速器", evidence)

    def test_deterministic_answer_handles_red_coast_period_questions(self):
        evidence = "\n".join(
            [
                "- [來源 1 / 3.紅岸之一 / part 2] 1969年的這一事件是以後人類歷史的一個轉折點。",
                "- [來源 2 / 3.紅岸之一 / part 4] 你以後就是基地的工作人員了，這意味着你再也不能離開這裡了。",
                "- [來源 2 / 3.紅岸之一 / part 5] 紅岸工程第147次發射實驗是在寒冷的星空下進行的。",
            ]
        )

        answer = _answer_from_deterministic_narrative_evidence("葉文潔是在什麼時期被調往紅岸基地工作的？", evidence)

        self.assertIn("文化大革命期間", answer)
        self.assertIn("1969", answer)
        self.assertIn("紅岸基地", answer)

    def test_deterministic_answer_handles_character_arc_questions(self):
        evidence = "\n".join(
            [
                "- [來源 1 / 2.寂靜的春天] 人類惡的一面已經在她年輕的心靈上刻下不可愈合的巨創。",
                "- [來源 1 / 2.寂靜的春天] 這本書使她對人類之惡第一次進行了理性的思考。",
                "- [來源 2 / 3.紅岸之一] 白沐霖的背叛使葉文潔陷入監室。",
                "- [來源 3 / 23.紅岸之六] 正在飛向太陽的信息是：到這裏來吧，我將幫助你們獲得這個世界。",
            ]
        )

        answer = _answer_from_deterministic_narrative_evidence("葉文潔的人生經歷如何影響她後來的選擇？", evidence)

        self.assertIn("多段創傷與失望累積", answer)
        self.assertIn("理性思考", answer)
        self.assertIn("再次發送訊號", answer)

    def test_deterministic_answer_handles_open_stance_questions_before_warning_fact_template(self):
        evidence = "\n".join(
            [
                "- [來源 1 / 23.紅岸之六] 警告你們：不要回答！不要回答！！不要回答！！！",
                "- [來源 1 / 23.紅岸之六] 如果回答，發射源將被定位，你們的行星系將遭到入侵，你們的世界將被佔領！",
                "- [來源 2 / 23.紅岸之六] 正在飛向太陽的信息是：到這裏來吧，我將幫助你們獲得這個世界。",
            ]
        )

        answer = _answer_from_deterministic_narrative_evidence("如果你是葉文潔，在收到外星文明的警告後，你會向宇宙再次發送訊號嗎？為什麼？", evidence)

        self.assertIn("我不會", answer)
        self.assertIn("開放式立場判斷", answer)
        self.assertIn("不可逆", answer)

    def test_deterministic_answer_handles_civilization_weakness_questions(self):
        evidence = "\n".join(
            [
                "- [來源 1 / 1.瘋狂年代] 葉哲泰在文化大革命批判中遭紅衛兵毆打。",
                "- [來源 2 / 2.寂靜的春天] 這本書使她對人類之惡第一次進行了理性的思考。",
                "- [來源 3 / 24.叛亂] 降臨派的最終目標就是請主毀滅全人類。",
            ]
        )

        answer = _answer_from_deterministic_narrative_evidence("小說中哪些事件最能體現人類文明的弱點？", evidence)

        self.assertIn("文革批判", answer)
        self.assertIn("人類之惡", answer)
        self.assertIn("ETO", answer)

    def test_verifier_accepts_alias_expanded_query_evidence_overlap(self):
        decision = assess_query_evidence_overlap(
            "汪淼 科學邊界 申玉菲 技術研討會 通過她",
            "- [來源 1 / 4.三十八年後。 / part 7] 我與科學邊界的接觸是從認識申玉菲開始的，我們是在今年年初的一次技術研討會上認識的。",
        )

        self.assertIsNotNone(decision)
        self.assertTrue(decision["is_related"])
        self.assertIn("query and alias terms", decision["reason"])

    def test_verifier_uses_focus_terms_for_unspaced_chinese_questions(self):
        decision = assess_query_evidence_overlap(
            "魏成研究三體問題時展現了什麼特殊能力或思考方式？",
            "- [來源 1 / 16.三體問題] 魏成用進化演算法研究三體運動，把不同運動矢量看成類似生物的東西，透過優勝劣汰進行預測。",
        )

        self.assertIsNotNone(decision)
        self.assertTrue(decision["is_related"])
        self.assertIn("魏成", decision["evidence_spans"][0])

    def test_keyword_search_ranks_matching_policy_chunks(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")

        results = keyword_search("生日當天有多少紅包禮金", chunks, top_k=2)

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "2.3 生日福利")
        self.assertGreater(results[0]["score"], 0)
        self.assertIn("200,000", results[0]["content"])

    def test_keyword_search_uses_rewritten_section_terms_for_sick_leave_chunk(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")

        results = keyword_search("出勤與請假制度 病假 醫療證明", chunks, top_k=2)

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "1.3 病假")
        self.assertIn("病假最多 300 天", results[0]["content"])

    def test_keyword_search_uses_rewritten_section_terms_for_body_discomfort(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")

        results = keyword_search("病假 身體狀況 醫療證明", chunks, top_k=2)

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "1.3 病假")

    def test_keyword_search_boosts_parent_section_when_query_matches_parent_title(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")

        results = keyword_search("福利制度", chunks, top_k=3)

        self.assertTrue(all(result["parent_title"] == "2. 福利制度" for result in results))

    def test_keyword_search_uses_rewritten_section_terms_for_related_subsidies(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")

        results = keyword_search("福利制度 三節獎金 交通補助 生日福利", chunks, top_k=3)
        titles = [result["title"] for result in results]

        self.assertIn("2.1 三節獎金", titles)
        self.assertIn("2.2 交通補助", titles)
        self.assertIn("2.3 生日福利", titles)

    def test_keyword_search_ranks_actual_failure_above_zero_failure(self):
        chunks = [
            {
                "id": "success-round",
                "source": "avalon.txt",
                "parent_title": "阿瓦隆對局紀錄",
                "title": "第8輪",
                "content": "本輪統計：任務：成功，正義方得分。任務牌：3 張，失敗牌 0 張。",
            },
            {
                "id": "failed-round",
                "source": "avalon.txt",
                "parent_title": "阿瓦隆對局紀錄",
                "title": "第2輪",
                "content": "本輪統計：任務：失敗，邪惡方得分。任務牌：2 張，失敗牌 1 張。",
            },
        ]

        results = keyword_search("哪幾輪任務出現失敗？", chunks, top_k=2)

        self.assertEqual(results[0]["title"], "第2輪")

    def test_keyword_search_uses_generic_outcome_polarity(self):
        chunks = [
            {
                "id": "resolved-ticket",
                "source": "ops.md",
                "parent_title": "客服紀錄",
                "title": "案件 A",
                "content": "處理狀態：成功。錯誤次數 0 次。",
            },
            {
                "id": "failed-ticket",
                "source": "ops.md",
                "parent_title": "客服紀錄",
                "title": "案件 B",
                "content": "處理狀態：失敗。錯誤原因：付款逾時。",
            },
        ]

        results = keyword_search("哪些案件處理失敗？錯誤原因是什麼？", chunks, top_k=2)

        self.assertEqual(results[0]["title"], "案件 B")

    def test_keyword_search_boosts_document_opening_metadata(self):
        chunks = [
            {
                "id": "middle",
                "source": "novel.txt",
                "chunk_index": 9,
                "parent_title": "Narrative Text",
                "title": "中段 / part 1",
                "content": "作品和作者這些詞在中段被討論，但沒有真正 metadata。",
            },
            {
                "id": "front",
                "source": "novel.txt",
                "chunk_index": 0,
                "parent_title": "Narrative Text",
                "title": "文件開頭 / metadata",
                "content": "三體X  Isaiah\n楔子",
            },
        ]

        results = keyword_search("這份知識庫開頭提到的作品標題與作者署名是什麼？", chunks, top_k=2)

        self.assertEqual(results[0]["id"], "front")

    def test_keyword_search_boosts_prologue_section_for_prologue_questions(self):
        chunks = [
            {
                "id": "later",
                "source": "novel.txt",
                "chunk_index": 20,
                "parent_title": "Narrative Text",
                "title": "上部 / part 1",
                "content": "宇宙、星系與背景在後段也有出現。",
            },
            {
                "id": "prologue",
                "source": "novel.txt",
                "chunk_index": 1,
                "parent_title": "Narrative Text",
                "title": "楔子 / part 1",
                "content": "另一個星系，另一個時間。",
            },
        ]

        results = keyword_search("開頭的楔子描述的是什麼樣的宇宙背景？", chunks, top_k=2)

        self.assertEqual(results[0]["id"], "prologue")

    def test_keyword_search_expands_distance_questions_for_narrative_time_spans(self):
        chunks = [
            {
                "id": "wrong",
                "source": "novel.txt",
                "chunk_index": 10,
                "parent_title": "Narrative Text",
                "title": "末日 宇宙的盡頭",
                "content": "雲天明詢問宇宙的狀態，但沒有距離資訊。",
            },
            {
                "id": "distance",
                "source": "novel.txt",
                "chunk_index": 2,
                "parent_title": "Narrative Text",
                "title": "銀河紀元409年 我們的星星 / part 1",
                "content": "雲天明想起程心，這是另一個時代，另一個世界，是近七個世紀之後，近三百光年外的另一顆星星。",
            },
        ]

        results = keyword_search("雲天明距離原本時代與地球環境大約有多遠？", chunks, top_k=2)

        self.assertEqual(results[0]["id"], "distance")

    def test_keyword_search_boosts_first_scene_environment_hazard_evidence(self):
        chunks = [
            {
                "id": "later",
                "source": "novel.txt",
                "chunk_index": 20,
                "parent_title": "Narrative Text",
                "title": "後段場景",
                "content": "主角後來再次登入遠星遊戲，看到文明準備離開母星。",
            },
            {
                "id": "first-entry",
                "source": "novel.txt",
                "chunk_index": 7,
                "parent_title": "Narrative Text",
                "title": "7.遠星遊戲",
                "content": "主角第一次進入遠星遊戲。這是亂紀元，太陽不一定能升起，嚴寒和酷熱會毀滅一切，人們只能脫水求生。",
            },
        ]

        results = keyword_search("主角第一次進入遠星遊戲時，所處文明正面臨什麼樣的天文災難？", chunks, top_k=2)

        self.assertEqual(results[0]["id"], "first-entry")

    def test_diversify_retrieval_results_adds_alias_anchor_chunks(self):
        chunks = [
            {
                "id": "reflection-1",
                "source": "novel.txt",
                "chunk_index": 1,
                "parent_title": "Narrative Text",
                "title": "寂靜的春天 / part 2",
                "content": "葉文潔在《寂靜的春天》中開始理性思考人類惡的一面。",
            },
            {
                "id": "reflection-2",
                "source": "novel.txt",
                "chunk_index": 2,
                "parent_title": "Narrative Text",
                "title": "寂靜的春天 / part 3",
                "content": "葉文潔對人類文明的失望在這一段逐漸加深。",
            },
            {
                "id": "father",
                "source": "novel.txt",
                "chunk_index": 3,
                "parent_title": "Narrative Text",
                "title": "瘋狂年代 / part 1",
                "content": "葉文潔的父親葉哲泰在批判中遭紅衛兵毆打，這成為她早期創傷。",
            },
            {
                "id": "signal",
                "source": "novel.txt",
                "chunk_index": 4,
                "parent_title": "Narrative Text",
                "title": "紅岸之六 / part 4",
                "content": "葉文潔再次發送訊號：到這裏來吧，我將幫助你們獲得這個世界。",
            },
        ]
        initial_results = [dict(chunks[0], score=1.0), dict(chunks[1], score=0.9)]

        diversified = _diversify_retrieval_results(
            "葉文潔的人生經歷如何影響她後來的選擇？",
            "葉文潔的人生經歷如何影響她後來的選擇？ 葉哲泰 父親 紅衛兵 到這裏來吧 我將幫助你們獲得這個世界",
            chunks,
            initial_results,
            extra_limit=3,
        )
        ids = [chunk["id"] for chunk in diversified]

        self.assertIn("father", ids)
        self.assertIn("signal", ids)

    def test_embedding_search_can_rank_by_semantic_vector(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")
        embeddings = [
            [1.0, 0.0],
            [0.2, 0.2],
            [0.0, 1.0],
            [0.4, 0.1],
        ]

        results = embedding_search(
            "身體不舒服需要休息",
            chunks,
            embeddings,
            embed_query_fn=lambda _: [0.0, 1.0],
            top_k=2,
        )

        self.assertEqual(results[0]["title"], "1.3 病假")
        self.assertGreater(results[0]["embedding_score"], results[1]["embedding_score"])

    def test_hybrid_search_combines_keyword_and_embedding_scores(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")
        embeddings = [
            [1.0, 0.0],
            [0.2, 0.2],
            [0.0, 1.0],
            [0.4, 0.1],
        ]

        results = hybrid_search(
            "身體不舒服需要休息",
            chunks,
            embeddings=embeddings,
            embed_query_fn=lambda _: [0.0, 1.0],
            top_k=2,
        )

        self.assertEqual(results[0]["title"], "1.3 病假")
        self.assertIn("keyword_score", results[0])
        self.assertIn("embedding_score", results[0])

    def test_hybrid_search_preserves_high_confidence_keyword_anchor(self):
        chunks = [
            {
                "id": "semantic",
                "source": "sample.txt",
                "chunk_index": 1,
                "parent_title": "Narrative Text",
                "title": "語意相近但缺少關鍵證據",
                "content": "研究遇到困難，大家討論科學的未來。",
            },
            {
                "id": "anchor",
                "source": "sample.txt",
                "chunk_index": 2,
                "parent_title": "Narrative Text",
                "title": "關鍵證據",
                "content": "楊冬的遺書寫著：物理學從來就沒有存在過。三台新的高能加速器實驗結果也造成衝擊。",
            },
        ]

        results = hybrid_search(
            "物理學不存在 楊冬 遺書 三台新的高能加速器 實驗結果",
            chunks,
            embeddings=[[1.0, 0.0], [0.0, 1.0]],
            embed_query_fn=lambda _: [1.0, 0.0],
            top_k=1,
        )

        self.assertEqual(results[0]["id"], "anchor")

    def test_hybrid_search_weights_are_adjustable(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")
        embeddings = [[1.0, 0.0] for _ in chunks]

        keyword_heavy = hybrid_search(
            "生日福利",
            chunks,
            embeddings=embeddings,
            embed_query_fn=lambda _: [1.0, 0.0],
            top_k=1,
            keyword_weight=0.9,
            embedding_weight=0.1,
        )

        self.assertEqual(keyword_heavy[0]["title"], "2.3 生日福利")

    def test_prompt_requires_source_grounding_and_uncertainty(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")
        results = keyword_search("事假可以請幾天", chunks, top_k=1)

        prompt = build_answer_prompt("事假可以請幾天", results)

        self.assertIn("只能根據下列來源回答", prompt)
        self.assertIn("使用者問：", prompt)
        self.assertIn("根據以下檢索資料回答", prompt)
        self.assertNotIn("並做總結", prompt)
        self.assertIn("檢索資料", prompt)
        self.assertIn("回答規則", prompt)
        self.assertIn("請使用繁體中文回答", prompt)
        self.assertIn("不要使用簡體字", prompt)
        self.assertIn("無法從來源確認", prompt)
        self.assertIn("不要使用一般常識、模型內部知識或來源外資訊補答案", prompt)
        self.assertIn("knowledge base", prompt)
        self.assertNotIn("員工手冊", prompt)
        self.assertNotIn("制度可能故意不符合常識", prompt)
        self.assertIn("不要把已經有來源支持的內容列入無法確認", prompt)
        self.assertIn("無法確認只限於使用者問題本身", prompt)
        self.assertNotIn("第三點只寫「無」", prompt)
        self.assertNotIn("回答格式：\n1. 答案\n2. 來源依據\n3.", prompt)
        self.assertIn("不能把推測內容當成已確認答案", prompt)
        self.assertIn("不需要固定輸出第 2 點或第 3 點", prompt)
        self.assertIn("不要加入結尾總結句", prompt)
        self.assertIn("逐一檢視每個檢索來源", prompt)
        self.assertIn("來源 1", prompt)
        self.assertIn("事假最多 90 天", prompt)

    def test_render_retrieved_context_includes_parent_title_and_chunk_content(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")
        results = keyword_search("公司有什麼福利嗎", chunks, top_k=1)

        context = render_retrieved_context(results)

        self.assertIn("[來源 1]", context)
        self.assertIn("父層章節：2. 福利制度", context)
        self.assertIn("章節：", context)
        self.assertIn("內容：", context)

    def test_render_retrieved_context_surfaces_key_excerpts_before_full_content(self):
        context = render_retrieved_context(
            [
                {
                    "source": "avalon.txt",
                    "parent_title": "阿瓦隆對局紀錄",
                    "title": "第2輪 / part 3",
                    "content": ("前段發言。" * 80) + "本輪統計：任務：失敗，邪惡方得分。任務牌：2 張，失敗牌 1 張。",
                }
            ]
        )

        self.assertIn("關鍵摘錄：", context)
        self.assertLess(context.index("關鍵摘錄："), context.index("內容："))
        self.assertIn("任務：失敗，邪惡方得分", context)

    def test_context_summary_prompt_includes_question_sources_and_output_rules(self):
        prompt = build_context_summary_prompt(
            "這場對局每位玩家的角色分別是什麼？",
            [
                {
                    "source": "avalon.txt",
                    "parent_title": "阿瓦隆對局紀錄",
                    "title": "第1輪 / part 1",
                    "content": "【API AI 1 / 梅林】\n【API AI 2 / 派西維爾】",
                }
            ],
        )

        self.assertIn("Context Summary Agent", prompt)
        self.assertIn("使用者提問", prompt)
        self.assertIn("來源資料", prompt)
        self.assertIn("直接 evidence", prompt)
        self.assertIn("不可新增來源沒有的資訊", prompt)
        self.assertIn("只保留能直接回答問題的最小資訊", prompt)
        self.assertIn("每個 evidence 最多一行", prompt)
        self.assertIn("不要摘錄思考過程", prompt)
        self.assertIn("只能包含指定的三個區塊", prompt)
        self.assertIn("【API AI 1 / 梅林】", prompt)

    def test_summarize_retrieved_context_uses_model_and_returns_summary(self):
        calls = []

        def fake_ask_model(prompt, **kwargs):
            calls.append((prompt, kwargs))
            return "## 輔助資訊\n無\n\n## 不足或衝突\n無\n\n---\n這段不應該進入 Answer Prompt"

        summary = summarize_retrieved_context(
            "誰是梅林？",
            [{"source": "avalon.txt", "title": "第1輪", "content": "【API AI 1 / 梅林】"}],
            model="fake",
            ask_model_fn=fake_ask_model,
        )

        self.assertIn("## 程式抽取 evidence", summary)
        self.assertIn("【API AI 1 / 梅林】", summary)
        self.assertIn("## Summary Agent 補充整理", summary)
        self.assertIn("最高優先", summary)
        self.assertNotIn("---", summary)
        self.assertEqual(len(calls), 1)
        self.assertIn("誰是梅林？", calls[0][0])
        self.assertIn("程式已先抽出的 deterministic evidence", calls[0][0])
        self.assertEqual(calls[0][1]["model"], "fake")

    def test_build_deterministic_context_summary_does_not_need_summary_agent(self):
        summary = build_deterministic_context_summary(
            [{"source": "avalon.txt", "title": "第1輪", "content": "【API AI 1 / 梅林】"}]
        )

        self.assertIn("## 程式抽取 evidence", summary)
        self.assertIn("最高優先", summary)
        self.assertIn("【API AI 1 / 梅林】", summary)
        self.assertNotIn("Summary Agent 補充整理", summary)

    def test_evidence_policy_detects_generic_temporal_and_event_questions(self):
        policy = build_evidence_policy("第一次付款失敗是哪一天？負責人是誰？")

        self.assertTrue(policy.temporal_order)
        self.assertTrue(policy.event_or_result_question)
        self.assertTrue(policy.asks_participant)
        self.assertTrue(policy.asks_outcome_detail)

    def test_evidence_policy_detects_event_list_questions(self):
        policy = build_evidence_policy("哪些案件處理失敗？各自負責人是誰？")

        self.assertTrue(policy.event_list)
        self.assertTrue(policy.event_or_result_question)

    def test_evidence_policy_detects_result_only_constraint(self):
        policy = build_evidence_policy("如果只看處理結果，4號和5號為什麼會被視為風險對象？")

        self.assertTrue(policy.result_only)

    def test_result_only_policy_filters_labels_and_keeps_result_fields(self):
        policy = build_evidence_policy("如果只看處理結果，4號和5號為什麼會被視為風險對象？")

        self.assertFalse(should_include_evidence_line("【Agent 4 / 申請人】", policy))
        self.assertFalse(should_include_evidence_line("思考：我認為 4 號很可疑", policy))
        self.assertTrue(should_include_evidence_line("處理結果：失敗", policy))
        self.assertTrue(should_include_evidence_line("處理者：Agent 2、Agent 4", policy))
        self.assertTrue(should_include_evidence_line("失敗原因：Agent 4 文件逾期", policy))

    def test_sequence_number_supports_generic_section_labels(self):
        self.assertEqual(sequence_number("第12章 / part 2"), 12)
        self.assertEqual(sequence_number("Phase 3 - rollout"), 3)
        self.assertEqual(sequence_number("Step 4"), 4)

    def test_event_evidence_gate_accepts_generic_result_fields(self):
        evidence = "\n".join(
            [
                "- [來源 1 / 第2天] 狀態：失敗",
                "- [來源 1 / 第2天] 負責人：王小明",
                "- [來源 1 / 第2天] 錯誤原因：付款逾時",
            ]
        )

        self.assertTrue(has_answerable_event_evidence("第一次付款失敗是哪一天？負責人是誰？", evidence))

    def test_evidence_policy_filters_vote_fields_unless_question_asks_vote(self):
        team_policy = build_evidence_policy("第一個失敗案件的負責人是誰？")
        vote_policy = build_evidence_policy("第1次審核誰贊成、誰反對？")

        self.assertFalse(should_include_evidence_line("贊成：王小明、陳小華", team_policy))
        self.assertTrue(should_include_evidence_line("贊成：王小明、陳小華", vote_policy))

    def test_parse_entity_existence_query_reads_numbered_entity_type(self):
        parsed = parse_entity_existence_query("這場對局有6號玩家參與嗎？")

        self.assertEqual(parsed.entity_type, "玩家")
        self.assertEqual(parsed.target_number, 6)
        self.assertEqual(parsed.target_label, "6號玩家")

    def test_parse_entity_existence_query_ignores_sequence_questions(self):
        self.assertIsNone(parse_entity_existence_query("第1輪隊伍為什麼沒有通過？誰支持、誰反對？"))
        self.assertIsNone(parse_entity_existence_query("第5輪的1、3任務結果是什麼？這對後續判斷有什麼影響？"))
        self.assertIsNone(parse_entity_existence_query("第6輪2、4、5隊伍為什麼沒有通過？"))

    def test_extract_entity_numbers_ignores_sequence_numbers_in_source_labels(self):
        evidence = "\n".join(
            [
                "- [來源 1 / 第6輪 / part 2] 【API AI 1 / 梅林】",
                "- [來源 1 / 第6輪 / part 2] 【API AI 2 / 派西維爾】",
                "- [來源 1 / 第6輪 / part 2] 【API AI 5 / 刺客】",
            ]
        )

        self.assertEqual(extract_entity_numbers(evidence, "玩家"), [1, 2, 5])

    def test_answer_entity_existence_returns_negative_from_observed_entities(self):
        evidence = "\n".join(
            [
                "- [來源 1 / 第6輪 / part 2] 【API AI 1 / 梅林】",
                "- [來源 1 / 第6輪 / part 2] 【API AI 2 / 派西維爾】",
                "- [來源 1 / 第6輪 / part 2] 【API AI 3 / 忠臣】",
                "- [來源 1 / 第6輪 / part 2] 【API AI 4 / 莫德雷德】",
                "- [來源 1 / 第6輪 / part 2] 【API AI 5 / 刺客】",
            ]
        )

        answer = answer_entity_existence("這場對局有6號玩家參與嗎？", evidence)

        self.assertIn("無法從來源確認有6號玩家參與", answer)
        self.assertIn("1、2、3、4、5", answer)
        self.assertNotIn("第6輪", answer)

    def test_answer_action_result_does_not_infer_success_from_action_only(self):
        evidence = "\n".join(
            [
                "- [來源 1 / 第8輪] 刺殺：刺殺座位 5",
                "- [來源 1 / 第8輪] 任務：成功，正義方得分",
            ]
        )

        answer = answer_action_result("最後刺客刺殺了誰？資料中能不能確認刺殺是否成功？", evidence)

        self.assertIn("刺殺座位 5", answer)
        self.assertIn("無法從來源確認刺殺是否成功", answer)
        self.assertNotIn("刺殺成功", answer)

    def test_find_event_list_chunks_returns_all_matching_result_events(self):
        chunks = [
            {
                "id": "event-3",
                "source": "ops.md",
                "parent_title": "事件紀錄",
                "title": "第3天",
                "content": "狀態：失敗\n負責人：陳小華\n錯誤原因：資料逾時",
            },
            {
                "id": "event-1",
                "source": "ops.md",
                "parent_title": "事件紀錄",
                "title": "第1天",
                "content": "狀態：成功\n負責人：王小明",
            },
            {
                "id": "event-2",
                "source": "ops.md",
                "parent_title": "事件紀錄",
                "title": "第2天",
                "content": "狀態：失敗\n負責人：林小美\n錯誤原因：付款逾時",
            },
        ]

        results = find_event_list_chunks("哪些事件失敗？各自負責人是誰？", chunks)

        self.assertEqual([chunk["title"] for chunk in results], ["第2天", "第3天"])

    def test_find_event_list_chunks_ignores_zero_failure_detail_rows(self):
        chunks = [
            {
                "id": "success-event",
                "source": "ops.md",
                "parent_title": "事件紀錄",
                "title": "第1天",
                "content": "狀態：成功\n處理明細：失敗項目 0 個",
            },
            {
                "id": "failed-event",
                "source": "ops.md",
                "parent_title": "事件紀錄",
                "title": "第2天",
                "content": "狀態：失敗\n處理明細：付款逾時",
            },
        ]

        results = find_event_list_chunks("哪些事件失敗？", chunks)

        self.assertEqual([chunk["title"] for chunk in results], ["第2天"])

    def test_find_result_constrained_chunks_uses_structured_result_evidence_for_targets(self):
        chunks = [
            {
                "id": "event-1",
                "source": "ops.md",
                "parent_title": "事件紀錄",
                "title": "第1天",
                "content": "角色：審核人\n處理結果：成功\n負責人：Agent 1",
            },
            {
                "id": "event-2",
                "source": "ops.md",
                "parent_title": "事件紀錄",
                "title": "第2天",
                "content": "【Agent 4 / 申請人】\n處理結果：失敗\n負責人：Agent 4\n錯誤原因：文件逾期",
            },
            {
                "id": "event-3",
                "source": "ops.md",
                "parent_title": "事件紀錄",
                "title": "第3天",
                "content": "【Agent 5 / 申請人】\n處理結果：失敗\n負責人：Agent 5\n錯誤原因：金額不符",
            },
        ]

        results = find_result_constrained_chunks("如果只看處理結果，4號和5號為什麼會被視為風險對象？", chunks)

        self.assertEqual([chunk["title"] for chunk in results], ["第2天", "第3天"])

    def test_find_result_constrained_chunks_matches_generic_numbered_labels(self):
        chunks = [
            {
                "id": "case-1",
                "source": "ops.md",
                "parent_title": "事件紀錄",
                "title": "Step 1",
                "content": "Result: failed\nOwner: Agent 4\nFailure detail: timeout",
            },
            {
                "id": "case-2",
                "source": "ops.md",
                "parent_title": "事件紀錄",
                "title": "Step 2",
                "content": "Result: failed\nOwner: Service 5\nFailure detail: rejected",
            },
            {
                "id": "case-3",
                "source": "ops.md",
                "parent_title": "事件紀錄",
                "title": "Step 3",
                "content": "Result: completed\nOwner: Agent 6",
            },
        ]

        results = find_result_constrained_chunks("only use result evidence: why are 4 and 5 risky?", chunks)

        self.assertEqual([chunk["title"] for chunk in results], ["Step 1", "Step 2"])

    def test_merge_event_list_chunks_places_structured_matches_first(self):
        vector_results = [
            {"id": "event-8", "title": "第8天", "source": "ops.md", "content": "狀態：成功"},
            {"id": "event-2", "title": "第2天", "source": "ops.md", "content": "狀態：失敗"},
        ]
        event_results = [
            {"id": "event-2", "title": "第2天", "source": "ops.md", "content": "狀態：失敗"},
            {"id": "event-3", "title": "第3天", "source": "ops.md", "content": "狀態：失敗"},
        ]

        merged = merge_event_list_chunks(event_results, vector_results)

        self.assertEqual([chunk["id"] for chunk in merged], ["event-2", "event-3", "event-8"])

    def test_build_deterministic_context_summary_orders_first_event_by_chronology(self):
        summary = build_deterministic_context_summary(
            [
                {
                    "source": "avalon.txt",
                    "title": "第3輪 / part 3",
                    "content": "任務：失敗，邪惡方得分\n出任務者：API AI 1、API AI 3、API AI 5\n失敗牌：API AI 5",
                },
                {
                    "source": "avalon.txt",
                    "title": "第2輪 / part 3",
                    "content": "任務：失敗，邪惡方得分\n出任務者：API AI 2、API AI 4\n失敗牌：API AI 4",
                },
            ],
            question="第一個任務失敗是第幾輪？隊伍是誰？誰出了失敗牌？",
        )

        self.assertLess(summary.index("第2輪 / part 3"), summary.index("第3輪 / part 3"))
        self.assertLess(summary.index("出任務者：API AI 2、API AI 4"), summary.index("出任務者：API AI 1、API AI 3、API AI 5"))
        self.assertIn("[來源 2 / 第2輪 / part 3] 任務：失敗", summary)

    def test_extract_deterministic_evidence_prioritizes_task_fields_for_task_questions(self):
        evidence = extract_deterministic_evidence(
            [
                {
                    "source": "avalon.txt",
                    "title": "第2輪 / part 3",
                    "content": "【API AI 4 / 莫德雷德】\n任務：失敗，邪惡方得分\n失敗牌：API AI 4",
                }
            ],
            question="第一個任務失敗是第幾輪？誰出了失敗牌？",
        )

        self.assertLess(evidence.index("任務：失敗"), evidence.index("【API AI 4 / 莫德雷德】"))

    def test_extract_deterministic_evidence_deduplicates_structured_labels(self):
        evidence = extract_deterministic_evidence(
            [
                {
                    "source": "avalon.txt",
                    "title": "第1輪",
                    "content": "【API AI 1 / 梅林】\n【API AI 2 / 派西維爾】",
                },
                {
                    "source": "avalon.txt",
                    "title": "第2輪",
                    "content": "【API AI 1 / 梅林】\n狀態：已核准",
                },
            ]
        )

        self.assertEqual(evidence.count("【API AI 1 / 梅林】"), 1)
        self.assertIn("【API AI 2 / 派西維爾】", evidence)
        self.assertIn("狀態：已核准", evidence)

    def test_extract_deterministic_evidence_prioritizes_slash_labels(self):
        evidence = extract_deterministic_evidence(
            [
                {
                    "source": "avalon.txt",
                    "title": "第1輪",
                    "content": "任務：成功\n【邪惡方私下頻道】\n【API AI 4 / 莫德雷德】",
                }
            ]
        )

        self.assertLess(evidence.index("【API AI 4 / 莫德雷德】"), evidence.index("任務：成功"))

    def test_extract_deterministic_evidence_ignores_narrative_colon_lines(self):
        evidence = extract_deterministic_evidence(
            [
                {
                    "source": "avalon.txt",
                    "title": "第7輪",
                    "content": "我補一句：這段只是發言內容，不是結構化欄位。\n【API AI 4 / 莫德雷德】",
                }
            ]
        )

        self.assertIn("【API AI 4 / 莫德雷德】", evidence)
        self.assertNotIn("我補一句", evidence)

    def test_answer_prompt_uses_summary_without_full_sources_when_summary_exists(self):
        prompt = build_answer_prompt(
            "這場對局每位玩家的角色分別是什麼？",
            [{"source": "avalon.txt", "title": "第1輪", "content": "【API AI 1 / 梅林】"}],
            context_summary="直接 evidence：API AI 1 / 梅林",
        )

        self.assertIn("## 彙整資料", prompt)
        self.assertIn("直接 evidence：API AI 1 / 梅林", prompt)
        self.assertNotIn("## 檢索資料", prompt)
        self.assertNotIn("內容：", prompt)
        self.assertIn("請根據以下彙整資料回答", prompt)
        self.assertIn("程式抽取 evidence 的優先級高於 Summary Agent 補充整理", prompt)
        self.assertIn("名單、身份、欄位值或對照關係", prompt)
        self.assertIn("最高優先", prompt)

    def test_answer_prompt_distinguishes_action_from_success_result(self):
        prompt = build_answer_prompt(
            "最後刺客刺殺了誰？資料中能不能確認刺殺是否成功？",
            [{"source": "avalon.txt", "title": "第8輪", "content": "刺殺：刺殺座位 5"}],
            context_summary="- [來源 1 / 第8輪] 刺殺：刺殺座位 5",
        )

        self.assertIn("動作發生不等於結果成功", prompt)
        self.assertIn("來源只提到動作", prompt)

    def test_answer_question_default_top_k_is_five(self):
        signature = inspect.signature(answer_question)

        self.assertEqual(signature.parameters["top_k"].default, 5)

    def test_three_agent_query_variants_include_question_and_keywords(self):
        variants = _build_three_agent_query_variants(
            "她為什麼回覆？",
            "葉文潔為什麼回覆三體文明？",
            ["葉文潔", "三體文明", "紅岸基地"],
        )

        names = [variant["name"] for variant in variants]
        queries = "\n".join(variant["query"] for variant in variants)
        self.assertEqual(names, ["original", "question_agent", "keywords", "keyword_only"])
        self.assertIn("她為什麼回覆？", queries)
        self.assertIn("葉文潔為什麼回覆三體文明？", queries)
        self.assertIn("葉文潔 三體文明 紅岸基地", queries)
        self.assertEqual(variants[3]["query"], "葉文潔 三體文明 紅岸基地")
        self.assertNotIn("她為什麼回覆？", variants[3]["query"])
        self.assertNotIn("葉文潔為什麼回覆三體文明？", variants[3]["query"])

    def test_sparse_dense_refined_query_variants_use_refined_question_and_keywords(self):
        variants = _build_sparse_dense_refined_query_variants(
            "她是誰？",
            "申玉菲在地球三體組織中較接近哪個派別？",
            ["申玉菲", "地球三體組織", "派別"],
        )

        self.assertEqual(
            [variant["name"] for variant in variants],
            ["sparse_refined", "sparse_keywords", "dense_refined", "dense_keywords"],
        )
        self.assertTrue(all("她是誰？" not in variant["query"] for variant in variants))
        self.assertEqual(variants[0]["query"], "申玉菲在地球三體組織中較接近哪個派別？")
        self.assertEqual(variants[1]["query"], "申玉菲 地球三體組織 派別")
        self.assertEqual(variants[2]["retrieval"], "dense")

    def test_sparse_dense_original_refined_query_variants_include_both_keyword_sets(self):
        variants = _build_sparse_dense_original_refined_query_variants(
            original_question="她後來去那個地方？",
            refined_question="葉文潔後來被調到哪個軍事基地？",
            original_keywords=["她", "紅岸基地"],
            refined_keywords=["葉文潔", "軍事基地"],
        )

        self.assertEqual(
            [variant["name"] for variant in variants],
            [
                "sparse_refined",
                "sparse_original_keywords",
                "sparse_refined_keywords",
                "sparse_all_keywords",
                "dense_refined",
                "dense_all_keywords",
            ],
        )
        self.assertIn("紅岸基地", variants[1]["query"])
        self.assertIn("葉文潔", variants[2]["query"])
        self.assertEqual(variants[3]["query"], "她 紅岸基地 葉文潔 軍事基地")
        self.assertEqual(variants[-1]["retrieval"], "dense")

    def test_hybrid_rerank_uses_multiple_query_variants_before_top_k(self):
        chunks = [
            {
                "id": "c1",
                "source": "three-body.txt",
                "parent_title": "Narrative Text",
                "title": "紅岸 / part 1",
                "content": "葉文潔在紅岸基地工作。",
            },
            {
                "id": "c2",
                "source": "three-body.txt",
                "parent_title": "Narrative Text",
                "title": "三體 / part 1",
                "content": "三體文明收到地球訊號。",
            },
            {
                "id": "c3",
                "source": "three-body.txt",
                "parent_title": "Narrative Text",
                "title": "無關 / part 1",
                "content": "普通背景敘述。",
            },
        ]
        variants = _build_three_agent_query_variants(
            "葉文潔為什麼回覆？",
            "葉文潔為什麼回覆三體文明？",
            ["葉文潔", "三體文明"],
        )

        results = _hybrid_rerank_results(
            query_variants=variants,
            question="葉文潔為什麼回覆？",
            refined_question="葉文潔為什麼回覆三體文明？",
            keywords=["葉文潔", "三體文明"],
            chunks=chunks,
            embeddings=None,
            top_k=2,
            candidate_k=3,
        )

        self.assertEqual(len(results), 2)
        self.assertTrue(all(result["retrieval_method"] == "hybrid_rerank" for result in results))
        self.assertTrue(any("kw:question_agent" in result["rerank_trace"] for result in results))

    def test_rrf_merge_combines_bm25_and_dense_rankings(self):
        bm25_results = [
            {"id": "lexical", "source": "three-body.txt", "title": "紅岸", "content": "紅岸基地"},
            {"id": "shared", "source": "three-body.txt", "title": "葉文潔", "content": "葉文潔"},
        ]
        dense_results = [
            {"id": "semantic", "source": "three-body.txt", "title": "軍事基地", "content": "基地工作"},
            {"id": "shared", "source": "three-body.txt", "title": "葉文潔", "content": "葉文潔"},
        ]

        results = _rrf_merge_ranked_results([("bm25", bm25_results), ("dense", dense_results)], top_k=3)

        self.assertEqual([result["id"] for result in results], ["shared", "lexical", "semantic"])
        self.assertIn("bm25:2", results[0]["rerank_trace"])
        self.assertIn("dense:2", results[0]["rerank_trace"])

    def test_parent_chunk_expansion_adds_adjacent_same_section_chunks(self):
        chunks = [
            {"id": "c1", "source": "three-body.txt", "chunk_index": 1, "parent_title": "Narrative Text", "title": "紅岸 / part 1", "content": "前文"},
            {"id": "c2", "source": "three-body.txt", "chunk_index": 2, "parent_title": "Narrative Text", "title": "紅岸 / part 2", "content": "命中內容"},
            {"id": "c3", "source": "three-body.txt", "chunk_index": 3, "parent_title": "Narrative Text", "title": "紅岸 / part 3", "content": "後文"},
            {"id": "c4", "source": "three-body.txt", "chunk_index": 4, "parent_title": "Narrative Text", "title": "三體 / part 1", "content": "別章"},
        ]

        expanded = _expand_parent_chunks([chunks[1]], chunks, max_contexts=3)

        self.assertEqual([chunk["id"] for chunk in expanded], ["c2", "c1", "c3"])

    def test_rrf_parent_context_results_limits_final_context_after_expansion(self):
        chunks = [
            {"id": "c1", "source": "three-body.txt", "chunk_index": 1, "parent_title": "Narrative Text", "title": "紅岸 / part 1", "content": "葉文潔"},
            {"id": "c2", "source": "three-body.txt", "chunk_index": 2, "parent_title": "Narrative Text", "title": "紅岸 / part 2", "content": "紅岸基地"},
            {"id": "c3", "source": "three-body.txt", "chunk_index": 3, "parent_title": "Narrative Text", "title": "紅岸 / part 3", "content": "軍事基地"},
            {"id": "c4", "source": "three-body.txt", "chunk_index": 4, "parent_title": "Narrative Text", "title": "紅岸 / part 4", "content": "工作"},
            {"id": "c5", "source": "three-body.txt", "chunk_index": 5, "parent_title": "Narrative Text", "title": "紅岸 / part 5", "content": "訊號"},
            {"id": "c6", "source": "three-body.txt", "chunk_index": 6, "parent_title": "Narrative Text", "title": "紅岸 / part 6", "content": "太陽"},
        ]

        results = _rrf_parent_context_results(
            question="葉文潔被調到哪個軍事基地？",
            rewritten_query="葉文潔 紅岸基地 軍事基地",
            chunks=chunks,
            embeddings=None,
            top_k=3,
            candidate_k=6,
            final_context_k=5,
        )

        self.assertLessEqual(len(results), 5)
        self.assertGreaterEqual(len(results), 3)
        self.assertTrue(any(result["id"] == "c2" for result in results))
        self.assertTrue(all("rrf_parent_context" in result["retrieval_method"] for result in results))

    def test_rrf_parent_context_keeps_original_question_terms_when_rewrite_drops_them(self):
        chunks = [
            {"id": "noise", "source": "three-body.txt", "chunk_index": 1, "parent_title": "Narrative Text", "title": "葉文潔 / part 1", "content": "葉文潔 葉文潔 葉文潔與三體遊戲。"},
            {"id": "book", "source": "three-body.txt", "chunk_index": 2, "parent_title": "Narrative Text", "title": "寂靜的春天 / part 1", "content": "寂靜的春天讓她開始思考人類之惡。"},
        ]

        results = _rrf_parent_context_results(
            question="讓葉文潔開始理性思考人類之惡的是哪一本書？",
            rewritten_query="葉文潔",
            chunks=chunks,
            embeddings=None,
            top_k=2,
            candidate_k=2,
            final_context_k=5,
        )

        self.assertEqual(results[0]["id"], "book")

    def test_rrf_parent_context_ignores_low_information_rewrite_terms(self):
        chunks = [
            {"id": "noise", "source": "three-body.txt", "chunk_index": 1, "parent_title": "Narrative Text", "title": "三體問題 / part 1", "content": "汪淼 三體 三體 三體 研究。"},
            {"id": "countdown", "source": "three-body.txt", "chunk_index": 2, "parent_title": "Narrative Text", "title": "射手和農場主 / part 1", "content": "汪淼眼前的倒計時停止了，他停止納米材料研究。"},
        ]

        results = _rrf_parent_context_results(
            question="汪淼被倒數計時威脅時，被要求停止的是哪一類研究？",
            rewritten_query="汪淼 三體",
            chunks=chunks,
            embeddings=None,
            top_k=2,
            candidate_k=2,
            final_context_k=5,
        )

        self.assertEqual(results[0]["id"], "countdown")

    def test_rrf_parent_context_uses_original_question_for_bm25_retrieval(self):
        chunks = [
            {"id": "rewrite-noise", "source": "three-body.txt", "chunk_index": 1, "parent_title": "Narrative Text", "title": "三體 / part 1", "content": "三體 三體 三體 三體 三體。"},
            {"id": "original-hit", "source": "three-body.txt", "chunk_index": 2, "parent_title": "Narrative Text", "title": "紅岸 / part 1", "content": "葉文潔後來被調到紅岸基地工作。"},
        ]

        results = _rrf_parent_context_results(
            question="葉文潔後來被調到哪一個軍事基地工作？",
            rewritten_query="三體 遊戲 文明",
            chunks=chunks,
            embeddings=None,
            top_k=2,
            candidate_k=2,
            final_context_k=5,
        )

        self.assertEqual(results[0]["id"], "original-hit")

    def test_explicit_metadata_filters_extract_sequence_from_question(self):
        chunks = [
            {"id": "round5", "source": "avalon.txt", "chunk_index": 5, "parent_title": "Game", "title": "第5輪 / part 1", "content": "任務結果"},
            {"id": "round8", "source": "avalon.txt", "chunk_index": 8, "parent_title": "Game", "title": "第8輪 / part 1", "content": "任務結果"},
        ]

        filters = _explicit_metadata_filters("第5輪的1、3任務結果是什麼？", chunks)

        self.assertEqual(filters["sequence"], {"第5輪"})

    def test_rrf_parent_context_applies_sequence_metadata_filter_before_retrieval(self):
        chunks = [
            {"id": "round5", "source": "avalon.txt", "chunk_index": 5, "parent_title": "Game", "title": "第5輪 / part 1", "content": "第5輪 1、3 任務成功。"},
            {"id": "round8", "source": "avalon.txt", "chunk_index": 8, "parent_title": "Game", "title": "第8輪 / part 1", "content": "第8輪 1、3 任務結果 任務結果 任務結果。"},
        ]

        results = _rrf_parent_context_results(
            question="第5輪的1、3任務結果是什麼？",
            rewritten_query="第5輪 1 3 任務結果",
            chunks=chunks,
            embeddings=None,
            top_k=2,
            candidate_k=2,
            final_context_k=5,
        )

        self.assertEqual([result["id"] for result in results], ["round5"])

    def test_rrf_parent_context_prefers_structured_result_chunks_for_result_only_questions(self):
        chunks = [
            {
                "id": "noise",
                "source": "avalon.txt",
                "chunk_index": 1,
                "parent_title": "Game",
                "title": "第1輪 / part 1",
                "content": "4號和5號反覆發言，討論很多但沒有任務結果。",
            },
            {
                "id": "round2-result",
                "source": "avalon.txt",
                "chunk_index": 2,
                "parent_title": "Game",
                "title": "第2輪 / part 3",
                "content": "任務：失敗，邪惡方得分\n出任務者：API AI 2、API AI 4\n失敗牌：API AI 4",
            },
            {
                "id": "round3-result",
                "source": "avalon.txt",
                "chunk_index": 3,
                "parent_title": "Game",
                "title": "第3輪 / part 3",
                "content": "任務：失敗，邪惡方得分\n出任務者：API AI 1、API AI 3、API AI 5\n失敗牌：API AI 5",
            },
        ]

        results = _rrf_parent_context_results(
            question="如果只看任務結果，4號和5號為什麼會被視為邪惡方？",
            rewritten_query="只看任務結果 4號 5號",
            chunks=chunks,
            embeddings=None,
            top_k=2,
            candidate_k=3,
            final_context_k=5,
        )

        self.assertEqual([result["id"] for result in results[:2]], ["round2-result", "round3-result"])

    def test_bm25_dense_retrieval_query_is_original_question(self):
        query = _bm25_dense_retrieval_query(
            question="葉文潔後來被調到哪一個軍事基地工作？",
            rewritten_query="三體 遊戲 文明",
        )

        self.assertEqual(query, "葉文潔後來被調到哪一個軍事基地工作？")

    def test_query_entity_extraction_uses_alias_records(self):
        entities = extract_query_entities(
            "申玉菲在 ETO 中屬於哪一派？",
            alias_records=[
                {"canonical": "申玉菲", "type": "person", "aliases": []},
                {"canonical": "地球三體組織", "type": "organization", "aliases": ["ETO"]},
            ],
        )

        self.assertEqual(
            [(entity["name"], entity["type"]) for entity in entities],
            [("申玉菲", "person"), ("地球三體組織", "organization")],
        )

    def test_chunk_entity_extraction_reads_chunk_text_and_metadata(self):
        entities = extract_chunk_entities(
            {
                "title": "地球三體運動",
                "parent_title": "Narrative Text",
                "content": "申玉菲屬於拯救派，這是地球三體組織中的派別。",
            },
            alias_records=[
                {"canonical": "申玉菲", "type": "person", "aliases": []},
                {"canonical": "拯救派", "type": "organization", "aliases": []},
            ],
        )

        self.assertEqual([entity["name"] for entity in entities], ["申玉菲", "拯救派"])

    def test_query_classifier_routes_content_relation_and_hybrid_queries(self):
        self.assertEqual(classify_query("黑暗森林理論是什麼？")["type"], "content")
        self.assertEqual(classify_query("哪些人屬於 ETO？")["type"], "relation")
        self.assertEqual(classify_query("葉文潔為什麼建立 ETO？")["type"], "hybrid")

    def test_graph_retrieval_returns_supporting_chunks_for_relation_query(self):
        chunks = [
            {
                "id": "support",
                "source": "three-body.txt",
                "chunk_index": 1,
                "parent_title": "Narrative Text",
                "title": "地球三體組織 / part 1",
                "content": "申玉菲在內心深處是一名堅定的拯救派。",
            },
            {
                "id": "noise",
                "source": "three-body.txt",
                "chunk_index": 2,
                "parent_title": "Narrative Text",
                "title": "三體遊戲 / part 1",
                "content": "申玉菲玩三體遊戲。",
            },
        ]
        graph = {
            "entities": [
                {"id": "person:shen-yufei", "name": "申玉菲", "type": "Person", "aliases": []},
                {"id": "org:adventists", "name": "拯救派", "type": "Organization", "aliases": []},
            ],
            "relations": [
                {
                    "source": "person:shen-yufei",
                    "target": "org:adventists",
                    "type": "MEMBER_OF",
                    "supporting_chunk_ids": ["support"],
                    "confidence": 1.0,
                }
            ],
        }

        results = retrieve_graph_context("申玉菲屬於哪一派？", chunks, graph=graph)

        self.assertEqual([result["id"] for result in results], ["support"])
        self.assertEqual(results[0]["retrieval_method"], "graph")
        self.assertIn("MEMBER_OF", results[0]["graph_trace"])

    def test_rrf_parent_context_merges_graph_context_for_relation_query(self):
        chunks = [
            {
                "id": "support",
                "source": "three-body.txt",
                "chunk_index": 1,
                "parent_title": "Narrative Text",
                "title": "地球三體組織 / part 1",
                "content": "申玉菲在內心深處是一名堅定的拯救派。",
            },
            {
                "id": "noise",
                "source": "three-body.txt",
                "chunk_index": 2,
                "parent_title": "Narrative Text",
                "title": "三體遊戲 / part 1",
                "content": "申玉菲 三體遊戲 三體遊戲 三體遊戲。",
            },
        ]
        graph = {
            "entities": [
                {"id": "person:shen-yufei", "name": "申玉菲", "type": "Person", "aliases": []},
                {"id": "org:salvationists", "name": "拯救派", "type": "Organization", "aliases": []},
            ],
            "relations": [
                {
                    "source": "person:shen-yufei",
                    "target": "org:salvationists",
                    "type": "MEMBER_OF",
                    "supporting_chunk_ids": ["support"],
                    "confidence": 1.0,
                }
            ],
        }

        results = _rrf_parent_context_results(
            question="申玉菲在地球三體組織中屬於哪一派？",
            rewritten_query="申玉菲 三體遊戲",
            chunks=chunks,
            embeddings=None,
            top_k=2,
            candidate_k=2,
            final_context_k=5,
            graph=graph,
        )

        self.assertEqual(results[0]["id"], "support")
        self.assertIn("graph", results[0]["retrieval_method"])

    def test_hybrid_rerank_prioritizes_subject_and_choice_cooccurrence(self):
        chunks = [
            {
                "id": "definition",
                "source": "three-body.txt",
                "parent_title": "Narrative Text",
                "title": "地球三體組織派別",
                "content": (
                    "地球三體組織分為降臨派和拯救派。"
                    "降臨派與拯救派一直對立。"
                    "降臨派主張毀滅人類，拯救派崇拜三體文明。"
                ),
            },
            {
                "id": "direct",
                "source": "three-body.txt",
                "parent_title": "Narrative Text",
                "title": "人物歸屬",
                "content": "申玉菲曾位居組織核心，但她在內心深處是一名堅定的拯救派。",
            },
            {
                "id": "noise",
                "source": "three-body.txt",
                "parent_title": "Narrative Text",
                "title": "無關背景",
                "content": "申玉菲在房間裏玩三體遊戲。",
            },
        ]
        question = "申玉菲在地球三體組織中，較接近降臨派還是拯救派？"
        keywords = ["申玉菲", "地球三體組織", "降臨派", "拯救派"]
        variants = _build_three_agent_query_variants(question, question, keywords)

        results = _hybrid_rerank_results(
            query_variants=variants,
            question=question,
            refined_question=question,
            keywords=keywords,
            chunks=chunks,
            embeddings=None,
            top_k=3,
            candidate_k=3,
        )

        self.assertEqual(results[0]["id"], "direct")

    def test_parse_keywords_output_reads_json_keywords(self):
        keywords = parse_keywords_output('{"keywords": ["葉文潔", "紅岸基地", "三體文明"]}')

        self.assertEqual(keywords, ["葉文潔", "紅岸基地", "三體文明"])

    def test_parse_question_output_reads_refined_question(self):
        refined_question = parse_question_output(
            '{"refined_question": "葉文潔為什麼回覆三體文明？", "intent": "cause"}'
        )

        self.assertEqual(refined_question, "葉文潔為什麼回覆三體文明？")

    def test_qa_prompt_combines_agent_outputs_and_retrieved_chunks(self):
        prompt = build_qa_prompt(
            original_question="她為什麼這樣做？",
            refined_question="葉文潔為什麼回覆三體文明？",
            keywords=["葉文潔", "紅岸基地", "三體文明"],
            chunks=[
                {
                    "source": "three-body.txt",
                    "parent_title": "Narrative Text",
                    "title": "紅岸",
                    "content": "葉文潔收到警告後仍回覆訊號。",
                }
            ],
            extracted_evidence="- [來源 1] 葉文潔收到警告後仍回覆訊號。",
        )

        self.assertIn("Question Extraction Agent Output", prompt)
        self.assertIn("葉文潔為什麼回覆三體文明？", prompt)
        self.assertIn("Evidence Extraction Agent Output", prompt)
        self.assertIn("葉文潔收到警告後仍回覆訊號", prompt)
        self.assertNotIn("Keyword Extraction Agent Output", prompt)
        self.assertNotIn("葉文潔, 紅岸基地, 三體文明", prompt)
        self.assertNotIn("Original Question", prompt)
        self.assertIn("Retrieved Chunks", prompt)

    def test_evidence_extraction_prompt_requests_sourced_facts(self):
        prompt = build_evidence_extraction_prompt(
            original_question="她為什麼這樣做？",
            refined_question="葉文潔為什麼回覆三體文明？",
            keywords=["葉文潔", "三體文明"],
            chunks=[
                {
                    "source": "three-body.txt",
                    "parent_title": "Narrative Text",
                    "title": "紅岸 / part 1",
                    "content": "葉文潔收到警告後仍回覆訊號。",
                }
            ],
        )

        self.assertIn("Question Extraction Agent Output", prompt)
        self.assertIn("Keyword Extraction Agent Output", prompt)
        self.assertIn("Retrieved Chunks", prompt)
        self.assertIn("每條 evidence 必須保留來源編號", prompt)
        self.assertIn("[來源 1]", prompt)

    def test_evidence_context_prioritizes_answer_cue_terms(self):
        context = render_evidence_context(
            chunks=[
                {
                    "source": "three-body.txt",
                    "parent_title": "Narrative Text",
                    "title": "32.監聽員 / part 9",
                    "content": (
                        "元首對發出警告信息的監聽員沒有什麼憤恨。"
                        "毫無疑問你是有罪的，你是三體世界所有輪迴的文明中最大的罪犯。"
                        "但三體法律實在出現一個例外——你自由了。"
                        "我要讓你活到她失去一切希望的那一天。"
                    ),
                }
            ],
            question="三體元首如何處置發出警告的 1379 號監聽員？",
            keywords=["三體", "元首", "處置", "警告", "1379號", "監聽員"],
            max_chars_per_chunk=500,
            max_snippets_per_chunk=3,
        )

        self.assertIn("有罪", context)
        self.assertIn("自由", context)
        self.assertIn("失去一切希望", context)

    def test_three_agent_output_includes_hybrid_query_variants(self):
        output = _format_three_agent_output(
            question="葉文潔為什麼回覆？",
            query_variants=[
                {"name": "original", "query": "葉文潔為什麼回覆？"},
                {"name": "question_agent", "query": "葉文潔為什麼回覆三體文明？"},
                {"name": "keywords", "query": "葉文潔 三體文明"},
            ],
            keywords=["葉文潔", "三體文明"],
            refined_question="葉文潔為什麼回覆三體文明？",
            results=[
                {
                    "source": "three-body.txt",
                    "title": "紅岸 / part 1",
                    "score": 1.2,
                    "keyword_score": 10,
                    "embedding_score": 0.7,
                    "rerank_trace": "kw:question_agent:1",
                }
            ],
            extracted_evidence="- [來源 1] 葉文潔收到警告後仍回覆訊號。",
            answer="她希望三體文明介入人類世界。",
            timing={"retrieval": 0.12, "evidence_extraction_agent": 0.45, "qa_agent": 1.23},
        )

        self.assertIn("Hybrid Retrieval Query Variants", output)
        self.assertIn("- question_agent: 葉文潔為什麼回覆三體文明？", output)
        self.assertIn("Evidence Extraction Agent", output)
        self.assertIn("葉文潔收到警告後仍回覆訊號", output)
        self.assertIn("trace=kw:question_agent:1", output)
        self.assertIn("evidence_extraction_agent: 0.45s", output)
        self.assertIn("qa_agent: 1.23s", output)

    def test_format_output_includes_node_timing_trace(self):
        output = _format_output(
            "誰是梅林？",
            "梅林 邪惡方",
            [
                {
                    "source": "avalon.txt",
                    "title": "第1輪",
                    "score": 0.8,
                    "keyword_score": 2.0,
                    "embedding_score": 0.6,
                }
            ],
            "1號是梅林。",
            timing={
                "load_index": 0.01,
                "query_rewrite": 1.2,
                "retrieval": 0.2,
                "verifier": 1.5,
                "context_summary": 1.8,
                "answer_generation": 2.3,
                "total": 5.21,
            },
            context_summary="直接 evidence：1號是梅林。",
        )

        self.assertIn("彙整資料：", output)
        self.assertIn("直接 evidence：1號是梅林。", output)
        self.assertIn("節點耗時：", output)
        self.assertIn("load_index: 0.01s", output)
        self.assertIn("query_rewrite: 1.20s", output)
        self.assertIn("context_summary: 1.80s", output)
        self.assertIn("answer_generation: 2.30s", output)
        self.assertIn("total: 5.21s", output)

    def test_source_insufficient_answer_does_not_use_general_fallback(self):
        answer = _build_source_insufficient_answer(
            {
                "is_related": False,
                "confidence": 0.0,
                "reason": "retrieval chunks did not contain evidence",
            }
        )

        self.assertIn("無法從目前檢索來源確認", answer)
        self.assertIn("retrieval chunks did not contain evidence", answer)
        self.assertNotIn("一般常識", answer)

    def test_query_combines_original_question_with_rewritten_query(self):
        combined = _combine_original_and_rewritten_query(
            "雲天明距離原本時代大約有多遠？",
            "雲天明 時間跨度 2005年 part 1",
        )

        self.assertIn("雲天明距離原本時代大約有多遠？", combined)
        self.assertIn("雲天明 時間跨度 2005年 part 1", combined)

    def test_narrative_knowledge_base_uses_original_question_for_retrieval(self):
        query = _select_retrieval_query(
            "雲天明距離原本時代大約有多遠？",
            "雲天明 時間跨度 2005年 part 1",
            [{"parent_title": "Narrative Text", "title": "銀河紀元409年"}],
        )

        self.assertEqual(query, "雲天明距離原本時代大約有多遠？")

    def test_retrieval_planner_extracts_focus_terms_for_explanation_questions(self):
        terms = extract_focus_terms("丁儀用檯球實驗想向汪淼說明什麼問題？")

        self.assertIn("丁儀", terms)
        self.assertIn("檯球實驗", terms)
        self.assertIn("汪淼", terms)

    def test_retrieval_planner_builds_failure_reason_variants(self):
        plan = build_retrieval_plan("墨子的宇宙模型為什麼最後被證明是錯的？")
        joined_queries = "\n".join(plan.query_variants)

        self.assertIn("failure_reason", plan.intent_labels)
        self.assertIn("墨子", joined_queries)
        self.assertIn("宇宙模型", joined_queries)
        self.assertIn("錯誤", joined_queries)
        self.assertIn("預測", joined_queries)

    def test_retrieval_planner_builds_purpose_and_comparison_variants(self):
        purpose_plan = build_retrieval_plan("古箏行動為什麼要使用汪淼的納米材料飛刃？")
        comparison_plan = build_retrieval_plan("大史對三體危機的判斷和科學家有什麼不同？")

        self.assertIn("purpose", purpose_plan.intent_labels)
        self.assertIn("保存", purpose_plan.evidence_query)
        self.assertIn("保留", purpose_plan.evidence_query)
        self.assertIn("comparison", comparison_plan.intent_labels)
        self.assertIn("判斷", comparison_plan.evidence_query)
        self.assertIn("觀點", comparison_plan.evidence_query)

    def test_rag_config_reads_tunable_environment_values(self):
        env = {
            "RAG_TOP_K": "4",
            "RAG_CHUNK_SIZE": "1800",
            "RAG_CHUNK_STRIDE": "600",
            "RAG_RETRIEVAL_CANDIDATE_K": "30",
            "RAG_KEYWORD_WEIGHT": "0.45",
            "RAG_EMBEDDING_WEIGHT": "0.55",
            "RAG_METADATA_BOOST_MAX": "0.12",
            "RAG_VERIFIER_AUTO_ACCEPT_SCORE": "0.52",
            "RAG_VERIFIER_AUTO_REJECT_SCORE": "0.15",
            "RAG_VERIFIER_MIN_KEYWORD_SCORE": "8",
            "RAG_VERIFIER_MIN_EMBEDDING_SCORE": "0.3",
            "RAG_VERIFIER_CONTEXT_CHARS": "500",
        }

        config = RagConfig.from_env(env)

        self.assertEqual(config.top_k, 4)
        self.assertEqual(config.chunk_size, 1800)
        self.assertEqual(config.chunk_stride, 600)
        self.assertEqual(config.retrieval_candidate_k, 30)
        self.assertAlmostEqual(config.keyword_weight, 0.45)
        self.assertAlmostEqual(config.embedding_weight, 0.55)
        self.assertAlmostEqual(config.metadata_boost_max, 0.12)
        self.assertAlmostEqual(config.verifier_auto_accept_score, 0.52)
        self.assertAlmostEqual(config.verifier_auto_reject_score, 0.15)
        self.assertAlmostEqual(config.verifier_min_keyword_score, 8)
        self.assertAlmostEqual(config.verifier_min_embedding_score, 0.3)
        self.assertEqual(config.verifier_context_chars, 500)

    def test_ollama_payload_includes_system_prompt_when_provided(self):
        payload = build_ollama_payload(
            prompt="使用者問題",
            model="qwen2.5:7b",
            system="你是檢索查詢改寫器。",
        )

        self.assertEqual(payload["system"], "你是檢索查詢改寫器。")
        self.assertEqual(payload["prompt"], "使用者問題")

    def test_parse_model_spec_defaults_to_ollama_for_legacy_model_names(self):
        spec = parse_model_spec("qwen2.5:7b")

        self.assertEqual(spec.provider, "ollama")
        self.assertEqual(spec.model, "qwen2.5:7b")

    def test_parse_model_spec_supports_remote_provider_prefixes(self):
        openai_spec = parse_model_spec("openai:gpt-5.5")
        anthropic_spec = parse_model_spec("anthropic:claude-opus-4-1-20250805")

        self.assertEqual(openai_spec.provider, "openai")
        self.assertEqual(openai_spec.model, "gpt-5.5")
        self.assertEqual(anthropic_spec.provider, "anthropic")
        self.assertEqual(anthropic_spec.model, "claude-opus-4-1-20250805")

    def test_openai_payload_uses_responses_api_message_input(self):
        payload = build_openai_payload(
            prompt="使用者問題",
            model="gpt-5.5",
            system="你是回答模型。",
        )

        self.assertEqual(payload["model"], "gpt-5.5")
        self.assertEqual(payload["input"][0]["role"], "system")
        self.assertEqual(payload["input"][1]["role"], "user")
        self.assertEqual(payload["input"][1]["content"], "使用者問題")

    def test_anthropic_payload_uses_messages_api_shape(self):
        payload = build_anthropic_payload(
            prompt="使用者問題",
            model="claude-opus-4-1-20250805",
            system="你是回答模型。",
        )

        self.assertEqual(payload["model"], "claude-opus-4-1-20250805")
        self.assertEqual(payload["system"], "你是回答模型。")
        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertEqual(payload["messages"][0]["content"], "使用者問題")

    def test_rewrite_prompt_requests_step_by_step_semantic_understanding(self):
        prompt = build_rewrite_prompt(
            "公司有什麼福利嗎",
            section_titles=["4.1 三節獎金", "4.2 交通補助", "4.3 生日福利"],
        )

        self.assertIn("先做一次語意理解", prompt)
        self.assertIn("step by step", prompt)
        self.assertIn("向量檢索用查詢", prompt)
        self.assertIn("公司有什麼福利嗎", prompt)
        self.assertIn("4.1 三節獎金", prompt)
        self.assertIn("不要加入候選章節之外的制度名詞", prompt)
        self.assertIn("如果問題是廣義分類", prompt)

    def test_extract_retrieval_query_reads_tagged_output(self):
        output = """語意理解：使用者想查公司福利項目。
向量檢索用查詢：福利制度 三節獎金 交通補助 生日福利 特休"""

        self.assertEqual(
            extract_retrieval_query(output),
            "福利制度 三節獎金 交通補助 生日福利 特休",
        )

    def test_sanitize_retrieval_query_removes_terms_not_in_question_or_sections(self):
        sanitized = sanitize_retrieval_query(
            original_question="公司有哪些相關的補助？",
            retrieval_query="補助措施 衛生福利 交通補助 生日福利 餘暇補助 特別獎金",
            section_titles=["4.2 交通補助", "4.3 生日福利"],
        )

        self.assertIn("補助", sanitized)
        self.assertIn("交通補助", sanitized)
        self.assertIn("生日福利", sanitized)
        self.assertNotIn("衛生福利", sanitized)
        self.assertNotIn("餘暇補助", sanitized)
        self.assertNotIn("特別獎金", sanitized)

    def test_sanitize_retrieval_query_drops_unrelated_section_terms(self):
        sanitized = sanitize_retrieval_query(
            original_question="公司有規定最低錄取學歷嗎？謊報學歷會怎麼樣",
            retrieval_query="保密義務",
            section_titles=["3. 保密義務", "3.1 保密範圍"],
        )

        self.assertEqual(sanitized, "公司有規定最低錄取學歷嗎？謊報學歷會怎麼樣")

    def test_verifier_prompt_checks_question_chunk_relevance(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")
        results = keyword_search("最低學歷", chunks, top_k=2)

        prompt = build_verifier_prompt("公司有規定最低學歷嗎", results)

        self.assertIn("驗證 retrieval chunks 是否包含足夠 evidence", prompt)
        self.assertIn("is_answerable", prompt)
        self.assertIn("無正確來源資料", prompt)
        self.assertIn("公司有規定最低學歷嗎", prompt)

    def test_verifier_prompt_requires_evidence_aware_schema(self):
        prompt = build_verifier_prompt(
            "這場對局每位玩家的角色分別是什麼？",
            [
                {
                    "source": "avalon.txt",
                    "parent_title": "阿瓦隆對局紀錄",
                    "title": "第1輪 / part 1",
                    "content": "【API AI 1 / 梅林】\n【API AI 2 / 派西維爾】",
                }
            ],
        )

        self.assertIn("先找 evidence", prompt)
        self.assertIn("is_answerable", prompt)
        self.assertIn("evidence_spans", prompt)
        self.assertIn("標題", prompt)
        self.assertIn("列表", prompt)
        self.assertIn("metadata", prompt)
        self.assertIn("角色標籤", prompt)

    def test_verifier_prompt_can_include_deterministic_evidence(self):
        prompt = build_verifier_prompt(
            "第一個任務失敗是第幾輪？",
            [
                {
                    "source": "avalon.txt",
                    "parent_title": "阿瓦隆對局紀錄",
                    "title": "第2輪 / part 3",
                    "content": "本輪統計：\n任務：失敗，邪惡方得分\n出任務者：API AI 2、API AI 4\n失敗牌：API AI 4",
                }
            ],
            evidence_summary="## 程式抽取 evidence\n- [來源 1 / 第2輪 / part 3] 任務：失敗，邪惡方得分",
        )

        self.assertIn("deterministic evidence", prompt)
        self.assertIn("任務：失敗，邪惡方得分", prompt)
        self.assertLess(prompt.index("deterministic evidence："), prompt.rindex("retrieval chunks："))

    def test_verify_retrieval_passes_deterministic_evidence_to_model(self):
        calls = []

        def fake_ask_model(prompt, **kwargs):
            calls.append(prompt)
            return """{
              "is_answerable": true,
              "confidence": 0.9,
              "evidence_spans": ["任務：失敗，邪惡方得分"],
              "missing_info": [],
              "reason": "deterministic evidence directly supports the answer"
            }"""

        verification = verify_retrieval(
            "這段資料是否提到任務流程？",
            [
                {
                    "source": "avalon.txt",
                    "parent_title": "阿瓦隆對局紀錄",
                    "title": "第2輪 / part 3",
                    "content": "任務：失敗，邪惡方得分",
                    "score": 0.5,
                    "keyword_score": 1.0,
                    "embedding_score": 0.2,
                }
            ],
            model="fake",
            ask_model_fn=fake_ask_model,
            config=RagConfig.from_env(),
            evidence_summary="## 程式抽取 evidence\n- 背景：任務審核",
        )

        self.assertEqual(len(calls), 1)
        self.assertIn("背景：任務審核", calls[0])
        self.assertTrue(verification["is_answerable"])

    def test_verify_retrieval_auto_accepts_task_result_deterministic_evidence(self):
        calls = []

        def fake_ask_model(prompt, **kwargs):
            calls.append(prompt)
            return "{}"

        verification = verify_retrieval(
            "第一個任務失敗是第幾輪？隊伍是誰？誰出了失敗牌？",
            [
                {
                    "source": "avalon.txt",
                    "parent_title": "阿瓦隆對局紀錄",
                    "title": "第2輪 / part 3",
                    "content": "任務：失敗，邪惡方得分\n出任務者：API AI 2、API AI 4\n失敗牌：API AI 4",
                    "score": 0.5,
                    "keyword_score": 1.0,
                    "embedding_score": 0.2,
                }
            ],
            model="fake",
            ask_model_fn=fake_ask_model,
            config=RagConfig.from_env(),
            evidence_summary="\n".join(
                [
                    "- [來源 1 / 第2輪 / part 3] 任務：失敗，邪惡方得分",
                    "- [來源 1 / 第2輪 / part 3] 出任務者：API AI 2、API AI 4",
                    "- [來源 1 / 第2輪 / part 3] 失敗牌：API AI 4",
                ]
            ),
        )

        self.assertEqual(calls, [])
        self.assertTrue(verification["is_answerable"])
        self.assertIn("deterministic_evidence", verification["reason"])

    def test_verify_retrieval_accepts_structured_role_labels_as_evidence(self):
        calls = []

        def fake_ask_model(prompt, **kwargs):
            calls.append(prompt)
            return """{
              "is_answerable": true,
              "confidence": 0.9,
              "evidence_spans": ["【API AI 1 / 梅林】", "【API AI 2 / 派西維爾】"],
              "missing_info": [],
              "reason": "角色標籤直接回答問題"
            }"""

        verification = verify_retrieval(
            "這場對局每位玩家的角色分別是什麼？",
            [
                {
                    "source": "avalon.txt",
                    "parent_title": "阿瓦隆對局紀錄",
                    "title": "第1輪 / part 1",
                    "content": "【API AI 1 / 梅林】\n【API AI 2 / 派西維爾】",
                    "score": 0.61,
                    "keyword_score": 6.0,
                    "embedding_score": 0.52,
                }
            ],
            model="fake",
            ask_model_fn=fake_ask_model,
            config=RagConfig.from_env(),
        )

        self.assertEqual(len(calls), 1)
        self.assertTrue(verification["is_related"])
        self.assertTrue(verification["is_answerable"])
        self.assertEqual(verification["evidence_spans"], ["【API AI 1 / 梅林】", "【API AI 2 / 派西維爾】"])
        self.assertEqual(verification["missing_info"], [])

    def test_extract_evidence_candidates_surfaces_structured_labels_and_table_rows(self):
        candidates = extract_evidence_candidates(
            """# 客戶資料

【API AI 1 / 梅林】
- 狀態：已核准
| 姓名 | 角色 |
| 王小明 | 管理員 |
部門：資料科學
一般長句內容不應全部放入候選 evidence，避免 prompt 變得太長。
"""
        )

        self.assertIn("【API AI 1 / 梅林】", candidates)
        self.assertIn("- 狀態：已核准", candidates)
        self.assertIn("| 王小明 | 管理員 |", candidates)
        self.assertIn("部門：資料科學", candidates)
        self.assertNotIn("一般長句內容不應全部放入候選 evidence，避免 prompt 變得太長。", candidates)

    def test_extract_evidence_candidates_keeps_relevant_narrative_sentences(self):
        candidates = extract_evidence_candidates(
            "有那麼一瞬間，雲天明有一種時空錯亂的感覺，他覺得自己仿佛回到了大一時的那次郊遊。"
            "但淡黃色的湖面，藍色的草叢和色彩斑斕的石子無不提醒著他，這是另一個時代，另一個世界，是近七個世紀之後，近三百光年外的另一顆星星。"
        )

        self.assertTrue(any("近七個世紀" in candidate for candidate in candidates))
        self.assertTrue(any("近三百光年" in candidate for candidate in candidates))

    def test_extract_evidence_candidates_clips_long_narrative_sentence_around_answer(self):
        long_prefix = "雲天明坐在岸邊，" + "湖畔景色與回憶交錯。" * 20
        content = (
            f"{long_prefix}但淡黃色的湖面，藍色的草叢和色彩斑斕的石子無不提醒著他，"
            "這是另一個時代，另一個世界，是近七個世紀之後，近三百光年外的另一顆星星。"
        )

        candidates = extract_evidence_candidates(content)

        self.assertTrue(any("近七個世紀" in candidate for candidate in candidates))
        self.assertTrue(any("近三百光年" in candidate for candidate in candidates))
        self.assertTrue(all(len(candidate) <= 226 for candidate in candidates))

    def test_deterministic_evidence_keeps_short_narrative_answer_sentences(self):
        chunks = [
            {
                "source": "three-body-1.txt",
                "parent_title": "Narrative Text",
                "title": "【銀河紀元409年 我們的星星】 / part 1",
                "content": (
                    "但淡黃色的湖面，藍色的草叢和色彩斑斕的石子無不提醒著他，"
                    "這是另一個時代，另一個世界，是近七個世紀之後，近三百光年外的另一顆星星。"
                ),
            }
        ]

        evidence = extract_deterministic_evidence(
            chunks,
            question="文中提到雲天明距離原本時代與地球環境大約有多遠？",
        )

        self.assertIn("近七個世紀", evidence)
        self.assertIn("近三百光年", evidence)

    def test_deterministic_evidence_keeps_generic_environment_hazard_sentences(self):
        chunks = [
            {
                "source": "novel.txt",
                "parent_title": "Narrative Text",
                "title": "7.遠星遊戲",
                "content": (
                    "主角第一次進入遠星遊戲。這是亂紀元，太陽不一定能升起。"
                    "嚴寒和酷熱會毀滅一切，人們只能脫水求生。"
                ),
            }
        ]

        evidence = extract_deterministic_evidence(
            chunks,
            question="主角第一次進入遠星遊戲時，所處文明正面臨什麼樣的天文災難？",
        )

        self.assertIn("亂紀元", evidence)
        self.assertIn("嚴寒", evidence)
        self.assertIn("酷熱", evidence)
        self.assertIn("脫水", evidence)

    def test_deterministic_narrative_evidence_accepts_distance_answer(self):
        decision = assess_deterministic_narrative_evidence(
            "文中提到雲天明距離原本時代與地球環境大約有多遠？",
            (
                "- [來源 1] 但淡黃色的湖面提醒著他，這是另一個時代，另一個世界，"
                "是近七個世紀之後，近三百光年外的另一顆星星。"
            ),
        )

        self.assertIsNotNone(decision)
        self.assertTrue(decision["is_related"])
        self.assertTrue(decision["is_answerable"])
        self.assertIn("narrative distance evidence", decision["reason"])

    def test_deterministic_narrative_evidence_accepts_first_scene_hazard_answer(self):
        decision = assess_deterministic_narrative_evidence(
            "主角第一次進入遠星遊戲時，所處文明正面臨什麼樣的天文災難？",
            "\n".join(
                [
                    "- [來源 1] 主角第一次進入遠星遊戲。",
                    "- [來源 1] 這是亂紀元，太陽不一定能升起。",
                    "- [來源 1] 嚴寒和酷熱會毀滅一切，人們只能脫水求生。",
                ]
            ),
        )

        self.assertIsNotNone(decision)
        self.assertTrue(decision["is_related"])
        self.assertTrue(decision["is_answerable"])
        self.assertIn("environment hazard evidence", decision["reason"])

    def test_answer_from_deterministic_narrative_evidence_returns_distance_answer(self):
        answer = _answer_from_deterministic_narrative_evidence(
            "文中提到雲天明距離原本時代與地球環境大約有多遠？",
            (
                "- [來源 1] 但淡黃色的湖面提醒著他，這是另一個時代，另一個世界，"
                "是近七個世紀之後，近三百光年外的另一顆星星。"
            ),
        )

        self.assertIn("近七個世紀", answer)
        self.assertIn("近三百光年", answer)

    def test_answer_from_deterministic_narrative_evidence_returns_environment_hazard_answer(self):
        answer = _answer_from_deterministic_narrative_evidence(
            "主角第一次進入遠星遊戲時，所處文明正面臨什麼樣的天文災難？",
            "\n".join(
                [
                    "- [來源 1] 主角第一次進入遠星遊戲。",
                    "- [來源 1] 這是亂紀元，太陽不一定能升起。",
                    "- [來源 1] 嚴寒和酷熱會毀滅一切，人們只能脫水求生。",
                ]
            ),
        )

        self.assertIn("亂紀元", answer)
        self.assertIn("太陽運行不可預測", answer)
        self.assertIn("脫水", answer)

    def test_answer_from_deterministic_narrative_evidence_returns_death_cause_answer(self):
        answer = _answer_from_deterministic_narrative_evidence(
            "葉文潔的父親是如何去世的？",
            "\n".join(
                [
                    "- [來源 1] 她掄起皮帶衝上去，她的三個小同志立刻跟上，帶銅扣的寬皮帶如雨點般打在他的頭上和身上。",
                    "- [來源 1] 當那四個女孩兒施暴奪去父親生命時，她曾想衝上台去。",
                    "- [來源 1] 她只是凝視台上父親已沒有生命的軀體。",
                ]
            ),
        )

        self.assertIn("施暴毆打致死", answer)
        self.assertIn("奪去父親生命", answer)

    def test_answer_from_deterministic_narrative_evidence_returns_scientist_suicide_bridge(self):
        answer = _answer_from_deterministic_narrative_evidence(
            "為什麼小說中有多位頂尖科學家接連自殺？",
            "\n".join(
                [
                    "- [來源 1] 一切的一切都導向這樣一個結果：物理學從來就沒有存在過，將來也不會存在。",
                    "- [來源 1] 這些自殺的學者大部分與科學邊界有過聯繫。",
                    "- [來源 2] 智子能夠在所有加速器中製造錯誤的撞擊結果。",
                ]
            ),
        )

        self.assertIn("智子", answer)
        self.assertIn("物理學從來就沒有存在過", answer)
        self.assertIn("科學信念", answer)

    def test_answer_from_deterministic_narrative_evidence_returns_physics_absent_background(self):
        answer = _answer_from_deterministic_narrative_evidence(
            "「物理學不存在了」這句話是在什麼背景下被提出的？",
            "\n".join(
                [
                    "- [來源 1] 楊冬的遺書寫著：一切的一切都導向這樣一個結果：物理學從來就沒有存在過，將來也不會存在。",
                    "- [來源 1] 常偉思說，相關具體信息與世界上三台新的高能加速器建成后取得的實驗結果有關。",
                ]
            ),
        )

        self.assertIn("楊冬遺書", answer)
        self.assertIn("高能加速器", answer)

    def test_answer_from_deterministic_narrative_evidence_returns_eto_purpose(self):
        answer = _answer_from_deterministic_narrative_evidence(
            "地球三體組織（ETO）成立的主要目的為何？",
            "\n".join(
                [
                    "- [來源 1] 這群人類叛徒齊聲喊出：世界屬於三體！",
                    "- [來源 2] 降臨派的最終目標就是請主來執行這個神聖的懲罰：毀滅全人類！",
                    "- [來源 2] 拯救派本質上是一個宗教團體，最終理想就是拯救主。",
                ]
            ),
        )

        self.assertIn("支持三體文明降臨", answer)
        self.assertIn("毀滅全人類", answer)

    def test_verifier_prompt_surfaces_evidence_candidates_before_content(self):
        prompt = build_verifier_prompt(
            "這場對局每位玩家的角色分別是什麼？",
            [
                {
                    "source": "avalon.txt",
                    "parent_title": "阿瓦隆對局紀錄",
                    "title": "第1輪 / part 1",
                    "content": "【API AI 1 / 梅林】\n【API AI 2 / 派西維爾】",
                }
            ],
        )

        self.assertIn("evidence 候選：", prompt)
        self.assertLess(prompt.index("evidence 候選："), prompt.index("內容節錄："))
        self.assertIn("【API AI 1 / 梅林】", prompt)
        self.assertIn("【API AI 2 / 派西維爾】", prompt)

    def test_verifier_prompt_truncates_long_chunk_content(self):
        content = ("開頭資訊" * 20) + ("中段資訊" * 100) + ("結尾任務結果：任務：失敗，邪惡方得分" * 5)
        prompt = build_verifier_prompt(
            "第1輪發生什麼事？",
            [
                {
                    "source": "avalon.txt",
                    "parent_title": "阿瓦隆對局紀錄",
                    "title": "第1輪 / part 1",
                    "content": content,
                }
            ],
            context_chars=120,
        )

        self.assertIn("開頭資訊", prompt)
        self.assertIn("結尾任務結果", prompt)
        self.assertNotIn("中段資訊" * 20, prompt)
        self.assertIn("內容已截斷", prompt)

    def test_assess_retrieval_confidence_auto_accepts_strong_hits(self):
        decision = assess_retrieval_confidence(
            [
                {
                    "score": 0.55,
                    "keyword_score": 19.0,
                    "embedding_score": 0.34,
                }
            ],
            RagConfig.from_env(
                {
                    "RAG_VERIFIER_AUTO_ACCEPT_ENABLED": "true",
                    "RAG_VERIFIER_AUTO_ACCEPT_SCORE": "0.52",
                    "RAG_VERIFIER_MIN_KEYWORD_SCORE": "8",
                    "RAG_VERIFIER_MIN_EMBEDDING_SCORE": "0.35",
                }
            ),
        )

        self.assertTrue(decision["is_related"])
        self.assertIn("auto_accept", decision["reason"])

    def test_assess_retrieval_confidence_does_not_auto_accept_by_default(self):
        decision = assess_retrieval_confidence(
            [
                {
                    "score": 0.70,
                    "keyword_score": 20.0,
                    "embedding_score": 0.45,
                }
            ],
            RagConfig.from_env(),
        )

        self.assertIsNone(decision)

    def test_assess_retrieval_confidence_does_not_accept_weak_keyword_overlap(self):
        decision = assess_retrieval_confidence(
            [
                {
                    "score": 0.54,
                    "keyword_score": 4.0,
                    "embedding_score": 0.34,
                }
            ],
            RagConfig.from_env(
                {
                    "RAG_VERIFIER_AUTO_ACCEPT_SCORE": "0.52",
                    "RAG_VERIFIER_MIN_KEYWORD_SCORE": "8",
                    "RAG_VERIFIER_MIN_EMBEDDING_SCORE": "0.35",
                }
            ),
        )

        self.assertIsNone(decision)

    def test_verify_retrieval_skips_llm_when_confidence_gate_accepts(self):
        calls = []

        def fake_ask_model(*args, **kwargs):
            calls.append(args)
            return '{"is_related": false, "confidence": 0.0, "reason": "should not call"}'

        verification = verify_retrieval(
            "誰是梅林？",
            [{"score": 0.7, "keyword_score": 20.0, "embedding_score": 0.4}],
            model="fake",
            ask_model_fn=fake_ask_model,
            config=RagConfig.from_env(
                {
                    "RAG_VERIFIER_AUTO_ACCEPT_ENABLED": "true",
                    "RAG_VERIFIER_AUTO_ACCEPT_SCORE": "0.52",
                }
            ),
        )

        self.assertEqual(calls, [])
        self.assertTrue(verification["is_related"])

    def test_verify_retrieval_calls_llm_when_auto_accept_is_disabled(self):
        calls = []

        def fake_ask_model(*args, **kwargs):
            calls.append(args)
            return '{"is_related": true, "confidence": 0.8, "reason": "verified by llm"}'

        verification = verify_retrieval(
            "刺客最後殺了誰？",
            [{"score": 0.7, "keyword_score": 20.0, "embedding_score": 0.4}],
            model="fake",
            ask_model_fn=fake_ask_model,
            config=RagConfig.from_env(),
        )

        self.assertEqual(len(calls), 1)
        self.assertTrue(verification["is_related"])
        self.assertEqual(verification["reason"], "verified by llm")


    def test_parse_verifier_output_reads_json_result(self):
        parsed = parse_verifier_output(
            '{"is_related": false, "confidence": 0.2, "reason": "chunks do not mention education"}'
        )

        self.assertFalse(parsed["is_related"])
        self.assertEqual(parsed["reason"], "chunks do not mention education")

    def test_parse_verifier_output_reads_evidence_aware_json_result(self):
        parsed = parse_verifier_output(
            """{
              "is_answerable": true,
              "confidence": 0.85,
              "evidence_spans": ["表格列：A 公司 / 營收 100", "metadata：2026 Q1"],
              "missing_info": [],
              "reason": "表格列與 metadata 足以回答"
            }"""
        )

        self.assertTrue(parsed["is_related"])
        self.assertTrue(parsed["is_answerable"])
        self.assertEqual(parsed["confidence"], 0.85)
        self.assertEqual(parsed["evidence_spans"][0], "表格列：A 公司 / 營收 100")
        self.assertEqual(parsed["missing_info"], [])

    def test_general_answer_prompt_marks_no_source_and_common_knowledge(self):
        prompt = build_general_answer_prompt("公司有規定最低學歷嗎")

        self.assertIn("無法在資料中搜尋到", prompt)
        self.assertIn("改用一般常識回答", prompt)
        self.assertIn("公司有規定最低學歷嗎", prompt)

    def test_index_round_trip_preserves_chunks(self):
        chunks = chunk_markdown(SAMPLE_MARKDOWN, source="sample.md")

        with TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "chunks.json"
            save_index(chunks, index_path)
            loaded = load_index(index_path)

        self.assertEqual(loaded, chunks)

    def test_embedding_matrix_round_trip_preserves_values(self):
        matrix = [[0.1, 0.2], [0.3, 0.4]]

        with TemporaryDirectory() as temp_dir:
            matrix_path = Path(temp_dir) / "embeddings.npy"
            save_embedding_matrix(matrix, matrix_path)
            loaded = load_embedding_matrix(matrix_path)

        self.assertEqual(len(loaded), len(matrix))
        self.assertAlmostEqual(loaded[0][0], matrix[0][0])
        self.assertAlmostEqual(loaded[1][1], matrix[1][1])

    def test_embed_texts_reuses_cached_model_for_same_model_name(self):
        class FakeModel:
            def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
                return [[float(len(text)), 1.0] for text in texts]

        created = []

        def fake_factory(model_name):
            created.append(model_name)
            return FakeModel()

        embeddings_module.clear_embedding_model_cache()
        try:
            first = embed_texts(["abc"], model_name="fake-model", model_factory=fake_factory)
            second = embed_texts(["abcd"], model_name="fake-model", model_factory=fake_factory)
        finally:
            embeddings_module.clear_embedding_model_cache()

        self.assertEqual(created, ["fake-model"])
        self.assertEqual(first[0][0], 3.0)
        self.assertEqual(second[0][0], 4.0)

    def test_chunk_to_embedding_text_includes_title_and_content(self):
        chunk = {
            "parent_title": "1. 出勤與請假制度",
            "title": "1.3 病假",
            "content": "員工每一曆年可申請病假最多 300 天。",
        }

        text = chunk_to_embedding_text(chunk)

        self.assertIn("1.3 病假", text)
        self.assertIn("1. 出勤與請假制度", text)
        self.assertIn("300 天", text)

    def test_render_home_contains_question_form(self):
        html = render_home()

        self.assertIn('method="post" action="/ask" id="ask-form"', html)
        self.assertIn('name="question"', html)
        self.assertIn('name="model"', html)
        self.assertIn("Knowledge base question", html)
        self.assertIn("請根據目前 knowledge base 回答", html)
        self.assertNotIn("阿瓦隆對局問題", html)
        self.assertNotIn("誰是梅林", html)
        self.assertIn('name="top_k"', html)
        self.assertIn("ollama:qwen2.5:7b", html)
        self.assertIn("openai:", html)
        self.assertIn("anthropic:", html)
        self.assertIn("送出問題", html)
        self.assertIn('data-loading-text="處理中"', html)
        self.assertIn("submit-spinner", html)
        self.assertIn('setAttribute("aria-busy", "true")', html)

    def test_ask_path_is_treated_as_home_for_browser_refresh(self):
        self.assertTrue(is_home_path("/"))
        self.assertTrue(is_home_path("/ask"))


if __name__ == "__main__":
    unittest.main()
