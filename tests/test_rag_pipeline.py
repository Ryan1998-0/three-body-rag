import unittest
import inspect
from pathlib import Path
from tempfile import TemporaryDirectory

from rag_demo.chunking import chunk_markdown
from rag_demo.chunking import chunk_avalon_record_text, load_knowledge_base_chunks
from rag_demo.config import RagConfig
from rag_demo import embeddings as embeddings_module
from rag_demo.embeddings import chunk_to_embedding_text, embed_texts, load_embedding_matrix, save_embedding_matrix
from rag_demo.index_store import load_index, save_index
from rag_demo.ollama_client import build_ollama_payload
from rag_demo.model_providers import (
    build_anthropic_payload,
    build_openai_payload,
    parse_model_spec,
)
from rag_demo.prompting import build_answer_prompt, render_retrieved_context
from rag_demo.general_answer import build_general_answer_prompt
from rag_demo.query import _format_output, answer_question
from rag_demo.query_rewriter import build_rewrite_prompt, extract_retrieval_query, sanitize_retrieval_query
from rag_demo.retrieval_verifier import build_verifier_prompt, parse_verifier_output
from rag_demo.retrieval_verifier import assess_retrieval_confidence, verify_retrieval
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

SAMPLE_AVALON_RECORD = """阿瓦隆 5 API AI 對局重排紀錄
格式：每次隊長提名隊伍視為一輪；包含裁判視角的 AI 思考摘要。

=== 第1輪 ===

【API AI 1 / 梅林】

思考：
我是梅林且看見 5 為邪惡，首輪避開 5。

發言：
第一輪我先提 1、2。

動作：
提名隊伍 [1,2]

本輪統計：
投票：2 贊成，3 反對
隊伍結果：未通過

========== 第1輪結束 ==========

=== 第2輪 ===

【API AI 2 / 派西維爾】

思考：
我是好方且自己可控。

發言：
這輪改開 2、4。

動作：
提名隊伍 [2,4]

本輪統計：
投票：5 贊成，0 反對
任務：出現 1 張失敗，邪惡方破壞
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

    def test_chunk_avalon_record_groups_content_by_round(self):
        chunks = chunk_avalon_record_text(SAMPLE_AVALON_RECORD, source="avalon.txt")

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["parent_title"], "阿瓦隆對局紀錄")
        self.assertEqual(chunks[0]["title"], "第1輪")
        self.assertIn("提名隊伍 [1,2]", chunks[0]["content"])
        self.assertEqual(chunks[1]["title"], "第2輪")
        self.assertIn("邪惡方破壞", chunks[1]["content"])

    def test_chunk_avalon_record_can_split_long_round_with_stride_overlap(self):
        long_record = """=== 第1輪 ===
""" + ("第1輪發言內容。" * 80)

        chunks = chunk_avalon_record_text(
            long_record,
            source="avalon.txt",
            chunk_size=120,
            chunk_stride=80,
        )

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0]["title"], "第1輪 / part 1")
        self.assertEqual(chunks[1]["title"], "第1輪 / part 2")
        self.assertIn(chunks[0]["content"][80:120], chunks[1]["content"])

    def test_load_knowledge_base_chunks_reads_avalon_record_text_files(self):
        with TemporaryDirectory() as temp_dir:
            kb_dir = Path(temp_dir)
            record_path = kb_dir / "avalon-record-formatted.txt"
            record_path.write_text(SAMPLE_AVALON_RECORD, encoding="utf-8")

            chunks = load_knowledge_base_chunks(kb_dir)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["title"], "第1輪")
        self.assertIn("avalon-record-formatted.txt", str(chunks[0]["source"]))

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

    def test_answer_question_default_top_k_is_three(self):
        signature = inspect.signature(answer_question)

        self.assertEqual(signature.parameters["top_k"].default, 3)

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
                "answer_generation": 2.3,
                "total": 5.21,
            },
        )

        self.assertIn("節點耗時：", output)
        self.assertIn("load_index: 0.01s", output)
        self.assertIn("query_rewrite: 1.20s", output)
        self.assertIn("answer_generation: 2.30s", output)
        self.assertIn("total: 5.21s", output)

    def test_rag_config_reads_tunable_environment_values(self):
        env = {
            "RAG_TOP_K": "4",
            "RAG_CHUNK_SIZE": "1800",
            "RAG_CHUNK_STRIDE": "600",
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

        self.assertIn("驗證輸入問題和 retrieval chunks 的關聯性", prompt)
        self.assertIn("is_related", prompt)
        self.assertIn("無正確來源資料", prompt)
        self.assertIn("公司有規定最低學歷嗎", prompt)

    def test_verifier_prompt_truncates_long_chunk_content(self):
        prompt = build_verifier_prompt(
            "第1輪發生什麼事？",
            [
                {
                    "source": "avalon.txt",
                    "parent_title": "阿瓦隆對局紀錄",
                    "title": "第1輪 / part 1",
                    "content": "A" * 1000,
                }
            ],
            context_chars=120,
        )

        self.assertIn("A" * 120, prompt)
        self.assertNotIn("A" * 300, prompt)
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
        self.assertIn("阿瓦隆對局問題", html)
        self.assertIn("誰是梅林", html)
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
