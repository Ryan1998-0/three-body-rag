import unittest

from evals.three_body_qwen.run_first20_closed_eval import extract_final_answer, score_answer


class First20ClosedEvalTest(unittest.TestCase):
    def test_extract_final_answer_returns_final_answer_section(self):
        output = """問題：測試

Final Answer:
葉文潔在紅岸基地向太陽發射訊號。
"""

        self.assertEqual(extract_final_answer(output), "葉文潔在紅岸基地向太陽發射訊號。")

    def test_score_answer_counts_required_aliases_and_forbidden_penalty(self):
        item = {
            "criteria": [
                {"label": "紅岸基地", "weight": 2, "aliases": ["紅岸基地", "紅岸"]},
                {"label": "太陽放大訊號", "weight": 3, "aliases": ["太陽", "放大", "訊號"]},
            ],
            "forbidden": [
                {"label": "錯誤角色", "penalty": 2, "aliases": ["汪淼發射"]},
            ],
        }

        result = score_answer("葉文潔在紅岸基地利用太陽放大訊號。", item)

        self.assertEqual(result["score"], 5)
        self.assertEqual(result["max_score"], 5)
        self.assertEqual(result["matched"], ["紅岸基地 (+2)", "太陽放大訊號 (+3)"])
        self.assertEqual(result["missed"], [])
        self.assertEqual(result["penalties"], [])

        penalized = score_answer("汪淼發射訊號。", item)

        self.assertEqual(penalized["score"], 1)
        self.assertEqual(penalized["penalties"], ["錯誤角色 (-2)"])

    def test_score_answer_does_not_penalize_negated_forbidden_alias(self):
        item = {
            "criteria": [
                {"label": "納米絲", "weight": 3, "aliases": ["納米絲"]},
                {"label": "切割", "weight": 2, "aliases": ["切割"]},
            ],
            "forbidden": [
                {"label": "錯說普通鋼纜", "penalty": 4, "aliases": ["普通鋼纜"]},
            ],
        }

        result = score_answer("古箏行動使用納米絲切割審判日號，而不是普通鋼纜。", item)

        self.assertEqual(result["score"], 5)
        self.assertEqual(result["penalties"], [])


if __name__ == "__main__":
    unittest.main()
