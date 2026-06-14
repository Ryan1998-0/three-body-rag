from datetime import datetime
from pathlib import Path
import json
import re
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_demo.query import answer_question


QUESTIONS = [
    {
        "id": "UQ01",
        "question": "葉文潔為何對人類文明感到失望？她的人生經歷如何影響後續的決定？",
        "criteria": [
            {"label": "父親葉哲泰在文革批判中死亡或遭暴力迫害", "aliases": ["父親", "葉哲泰", "文革", "文化大革命", "批判", "紅衛兵", "死亡", "打死"]},
            {"label": "白沐霖或政治審查/背叛加深她對人性的失望", "aliases": ["白沐霖", "背叛", "審查", "監獄", "程麗華"]},
            {"label": "《寂靜的春天》或環境破壞使她思考人類之惡", "aliases": ["寂靜的春天", "環境", "破壞", "人類之惡", "理性"]},
            {"label": "她把個人創傷擴大為對整體人類文明的失望", "aliases": ["人類文明", "失望", "絕望", "人性", "文明"]},
            {"label": "這些經歷促使她後來選擇向三體文明發訊/回覆", "aliases": ["回覆", "發送", "訊號", "三體", "外星文明", "到這裏來吧"]},
        ],
    },
    {
        "id": "UQ02",
        "question": "紅岸基地的主要任務是什麼？葉文潔在基地中發現了什麼重要現象？",
        "criteria": [
            {"label": "紅岸表面或官方任務與監聽/發射電波/探索外星文明有關", "aliases": ["紅岸", "監聽", "發射", "電波", "外星", "宇宙", "搜尋"]},
            {"label": "基地具有軍事或絕密工程背景", "aliases": ["軍事", "絕密", "工程", "基地", "國防"]},
            {"label": "葉文潔發現太陽可放大/反射/增益無線電訊號", "aliases": ["太陽", "放大", "增益", "反射", "訊號", "電波"]},
            {"label": "此現象使遠距離星際通訊成為可能", "aliases": ["星際", "通訊", "宇宙", "遠距離", "發射"]},
            {"label": "回答區分紅岸任務與葉文潔個人發現", "aliases": ["主要任務", "發現", "葉文潔", "紅岸"]},
        ],
    },
    {
        "id": "UQ03",
        "question": "葉文潔第一次收到來自三體文明的訊息時，訊息內容為何？發送者為何警告她不要回覆？",
        "criteria": [
            {"label": "訊息核心是不要回答/不要回覆", "aliases": ["不要回答", "不要回覆", "不要發回"]},
            {"label": "若回覆，地球位置或發射源會被定位", "aliases": ["定位", "位置", "發射源", "座標"]},
            {"label": "若被定位，地球/行星系會遭入侵或被佔領", "aliases": ["入侵", "佔領", "毀滅", "侵略"]},
            {"label": "發送者是三體文明中的和平主義者或警告者", "aliases": ["和平主義者", "三體", "警告", "監聽員", "善意"]},
            {"label": "警告原因是保護地球避免被三體文明發現", "aliases": ["保護", "地球", "避免", "發現", "三體文明"]},
        ],
    },
    {
        "id": "UQ04",
        "question": "葉文潔最終為何選擇回覆三體文明？她希望藉由三體人達成什麼目的？",
        "criteria": [
            {"label": "她對人類文明/人性徹底失望", "aliases": ["失望", "絕望", "人類", "人性", "文明"]},
            {"label": "她無視不要回答的警告仍回覆", "aliases": ["不要回答", "警告", "回覆", "仍然"]},
            {"label": "她邀請三體文明來到地球", "aliases": ["到這裏來吧", "三體", "來到", "地球"]},
            {"label": "她希望借外部力量改造、干預或拯救人類", "aliases": ["改造", "干預", "拯救", "外部力量", "幫助"]},
            {"label": "回答有連結她的個人經歷與這個選擇", "aliases": ["經歷", "父親", "背叛", "文革", "選擇"]},
        ],
    },
    {
        "id": "UQ05",
        "question": "「科學邊界」是一個什麼樣的組織？其成員對當代科學抱持何種看法？",
        "criteria": [
            {"label": "科學邊界是由精英科學家/學者組成的組織", "aliases": ["科學邊界", "科學家", "學者", "精英"]},
            {"label": "組織關注科學前沿、基礎物理或科學極限", "aliases": ["前沿", "基礎物理", "物理", "極限", "邊界"]},
            {"label": "成員認為現代科學/物理遇到危機", "aliases": ["危機", "物理學", "不存在", "崩潰", "問題"]},
            {"label": "與科學家自殺或思想動搖背景相關", "aliases": ["自殺", "楊冬", "科學家", "動搖"]},
            {"label": "沒有把科學邊界誤說成普通科普社團或單純遊戲組織", "aliases": ["科學邊界", "組織", "物理"]},
        ],
    },
    {
        "id": "UQ06",
        "question": "汪淼在調查科學家自殺事件的過程中，為何會看到神秘的倒數計時？這個現象的目的是什麼？",
        "criteria": [
            {"label": "汪淼看到倒數與他調查科學家自殺/奈米材料研究有關", "aliases": ["汪淼", "倒數", "自殺", "奈米", "調查"]},
            {"label": "倒數出現在照片、視網膜、眼前或觀測中", "aliases": ["照片", "視網膜", "眼前", "倒計時", "倒數"]},
            {"label": "現象由三體方/智子/ETO 施加或操控", "aliases": ["智子", "三體", "ETO", "地球三體組織", "操控"]},
            {"label": "目的是恐嚇或施壓汪淼", "aliases": ["恐嚇", "威脅", "施壓", "嚇阻"]},
            {"label": "目的是迫使他停止奈米材料/相關科學研究", "aliases": ["停止", "奈米", "研究", "飛刃", "實驗"]},
        ],
    },
    {
        "id": "UQ07",
        "question": "三體遊戲中的世界為何經常遭遇毀滅？這反映了三體星系的什麼特徵？",
        "criteria": [
            {"label": "三體遊戲世界有三顆太陽或三恒星", "aliases": ["三顆太陽", "三個太陽", "三恒星", "三顆恆星"]},
            {"label": "恒紀元與亂紀元交替或難以預測", "aliases": ["恆紀元", "恒紀元", "亂紀元", "交替", "不可預測"]},
            {"label": "極寒、酷熱、脫水或太陽災變導致文明毀滅", "aliases": ["嚴寒", "酷熱", "脫水", "毀滅", "災難"]},
            {"label": "反映三體問題/三體星系運動混沌不穩定", "aliases": ["三體問題", "混沌", "不穩定", "無規律"]},
            {"label": "遊戲是在模擬三體文明真實生存環境", "aliases": ["遊戲", "模擬", "真實", "三體文明", "生存"]},
        ],
    },
    {
        "id": "UQ08",
        "question": "三體文明面臨的最大生存危機是什麼？他們為何計畫前往地球？",
        "criteria": [
            {"label": "最大危機是三顆太陽造成星球環境不穩定", "aliases": ["三顆太陽", "三個太陽", "不穩定", "亂紀元", "災難"]},
            {"label": "母星文明反覆毀滅或難以長期生存", "aliases": ["毀滅", "生存", "文明", "滅亡", "危機"]},
            {"label": "地球是穩定或適合生存的目標", "aliases": ["地球", "穩定", "適合", "生存", "家園"]},
            {"label": "葉文潔/地球回覆暴露了地球位置", "aliases": ["葉文潔", "回覆", "位置", "暴露", "定位"]},
            {"label": "因此三體文明計畫遠征/殖民/入侵地球", "aliases": ["艦隊", "前往", "殖民", "入侵", "佔領"]},
        ],
    },
    {
        "id": "UQ09",
        "question": "智子（Sophon）是什麼？三體文明如何利用智子干擾地球的科學發展？",
        "criteria": [
            {"label": "智子是由質子改造/展開製成的微觀智能裝置", "aliases": ["質子", "智子", "微觀", "展開", "改造"]},
            {"label": "智子具有超級計算機、智能或通訊功能", "aliases": ["超級計算機", "智能", "通訊", "監視", "即時"]},
            {"label": "三體文明把智子送到地球", "aliases": ["地球", "三體", "送", "到達", "智子"]},
            {"label": "智子干擾粒子加速器或高能物理實驗結果", "aliases": ["加速器", "高能", "實驗", "撞擊", "干擾"]},
            {"label": "目的是鎖死人類基礎科學/阻止科技進步", "aliases": ["鎖死", "基礎科學", "科技", "發展", "物理"]},
        ],
    },
    {
        "id": "UQ10",
        "question": "在《三體》第一部結尾，人類得知三體艦隊即將抵達地球後，各方勢力對未來的態度有何不同？",
        "criteria": [
            {"label": "人類政府/軍方或科學界意識到危機並準備對抗", "aliases": ["軍方", "政府", "人類", "對抗", "危機"]},
            {"label": "ETO 或地球三體組織內部有不同派別", "aliases": ["ETO", "地球三體組織", "派", "派別"]},
            {"label": "降臨派希望三體降臨甚至毀滅人類", "aliases": ["降臨派", "毀滅", "人類", "降臨"]},
            {"label": "拯救派/救贖派希望三體文明能改造或拯救人類", "aliases": ["拯救派", "救贖派", "改造", "拯救"]},
            {"label": "倖存派/普通人或不同勢力對未來有恐懼、投降、求生或抵抗等差異態度", "aliases": ["倖存派", "求生", "投降", "恐懼", "抵抗", "未來"]},
        ],
    },
]


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = eval_dir / f"three_agent_user10_raw_answers_{timestamp}.jsonl"
    report_path = eval_dir / f"three_agent_user10_scored_report_{timestamp}.md"

    model = "qwen2.5:7b"
    top_k = 5
    started = time.perf_counter()
    records = []

    with raw_path.open("w", encoding="utf-8") as raw_file:
        for item in QUESTIONS:
            q_started = time.perf_counter()
            record = {
                "id": item["id"],
                "question": item["question"],
                "criteria": [criterion["label"] for criterion in item["criteria"]],
                "answer_output": "",
                "final_answer": "",
                "score": 0,
                "max_score": len(item["criteria"]),
                "matched": [],
                "missed": [],
                "error": None,
                "elapsed_seconds": None,
            }
            try:
                record["answer_output"] = answer_question(item["question"], model=model, top_k=top_k)
                record["final_answer"] = extract_final_answer(record["answer_output"])
                score_record(record, item["criteria"])
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
                record["missed"] = record["criteria"]
            record["elapsed_seconds"] = round(time.perf_counter() - q_started, 3)
            records.append(record)
            raw_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            raw_file.flush()
            print(
                f"{record['id']} score={record['score']}/{record['max_score']} "
                f"elapsed={record['elapsed_seconds']}s error={record['error'] is not None}"
            )

    write_report(report_path, raw_path, records, model, top_k, started)
    print(f"Raw JSONL: {raw_path}")
    print(f"Scored report: {report_path}")
    return 0 if all(record["error"] is None for record in records) else 1


def extract_final_answer(answer_output: str) -> str:
    marker = "Final Answer:"
    if marker in answer_output:
        return answer_output.split(marker, 1)[1].strip()
    return str(answer_output).strip()


def score_record(record, criteria) -> None:
    answer = normalize_text(record["final_answer"])
    matched = []
    missed = []
    for criterion in criteria:
        aliases = [normalize_text(alias) for alias in criterion["aliases"]]
        hit_count = sum(1 for alias in aliases if alias and alias in answer)
        required_hits = 1
        if len(aliases) >= 4:
            required_hits = 2
        if hit_count >= required_hits:
            matched.append(criterion["label"])
        else:
            missed.append(criterion["label"])

    record["matched"] = matched
    record["missed"] = missed
    record["score"] = len(matched)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()


def write_report(report_path: Path, raw_path: Path, records, model: str, top_k: int, started: float) -> None:
    total_score = sum(record["score"] for record in records)
    max_score = sum(record["max_score"] for record in records)
    percent = round(total_score / max_score * 100, 1) if max_score else 0.0
    completed = sum(1 for record in records if record["error"] is None)
    elapsed = round(time.perf_counter() - started, 1)

    lines = [
        "# Three-Agent RAG User10 Scored Report",
        "",
        f"- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Model: `{model}`",
        f"- Top K: `{top_k}`",
        "- Pipeline: `Keyword Extraction Agent -> Semantic Retrieval -> Question Extraction Agent -> QA Agent`",
        f"- Raw answers: `{raw_path.as_posix()}`",
        "",
        "## Scoring Mechanism",
        "",
        "Each question is scored on a 5-point rubric.",
        "",
        "- Every question has 5 expected criteria.",
        "- Each matched criterion is worth 1 point.",
        "- Matching is rule-based: a criterion is counted when the Final Answer contains enough aliases for that criterion.",
        "- This keeps the score reproducible across runs, but borderline semantic equivalents should still be manually reviewed.",
        "- Total score is reported as points out of 50 and as a percentage.",
        "",
        "## Run Result",
        "",
        f"- Completed: `{completed}/{len(records)}`",
        f"- Runtime errors: `{len(records) - completed}`",
        f"- Total elapsed: about `{elapsed}s`",
        f"- Total score: `{total_score} / {max_score} = {percent} / 100`",
        "",
        "## Score Table",
        "",
        "| ID | Score | Missed Criteria |",
        "| --- | ---: | --- |",
    ]

    for record in records:
        missed = "; ".join(record["missed"]) if record["missed"] else "None"
        lines.append(f"| {record['id']} | {record['score']}/{record['max_score']} | {missed} |")

    for record in records:
        lines.extend(
            [
                "",
                f"## {record['id']}",
                "",
                f"Question: {record['question']}",
                "",
                f"Elapsed: `{record['elapsed_seconds']}s`",
                "",
                f"Score: `{record['score']} / {record['max_score']}`",
                "",
                "Matched criteria:",
            ]
        )
        if record["matched"]:
            lines.extend(f"- {item}" for item in record["matched"])
        else:
            lines.append("- None")
        lines.append("")
        lines.append("Missed criteria:")
        if record["missed"]:
            lines.extend(f"- {item}" for item in record["missed"])
        else:
            lines.append("- None")
        lines.append("")
        if record["error"]:
            lines.append(f"Error: `{record['error']}`")
        else:
            lines.extend(
                [
                    "Final Answer:",
                    "",
                    "```text",
                    record["final_answer"],
                    "```",
                    "",
                    "Full RAG Output:",
                    "",
                    "```text",
                    record["answer_output"],
                    "```",
                ]
            )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
