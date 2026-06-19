from datetime import datetime
from pathlib import Path
import json
import os
import re
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("RAG_PROFILE", "three_body_trilogy")

from rag_demo.embeddings import load_embedding_matrix
from rag_demo.index_store import load_index
from rag_demo.knowledge_base import active_knowledge_base
from rag_demo.query import _rrf_parent_context_results
from rag_demo.vector_store import QdrantVectorStore


COLLECTION_NAME = "three_body_trilogy_mixed200_eval"


FACTS = [
    {
        "id": "MIX-TB1-01",
        "book": "三體1：瘋狂年代",
        "standard_answer": "汪淼被要求停止納米材料研究。",
        "criteria": [
            {"label": "汪淼", "weight": 1, "aliases": ["汪淼"]},
            {"label": "停止研究", "weight": 2, "aliases": ["停止", "停下", "停掉"]},
            {"label": "納米材料", "weight": 2, "aliases": ["纳米材料", "納米材料", "奈米材料", "飞刃", "飛刃"]},
        ],
        "questions": [
            "汪淼被倒計時威脅時，被要求停止哪一類研究？",
            "如果有人說主角眼前出現幽靈倒計時，對方其實要他停下什麼工作？",
            "汪淼 倒計時 停止 研究",
            "三體第一部裡，倒數計時和申玉菲對汪淼提出的要求，與哪項材料技術有關？",
        ],
    },
    {
        "id": "MIX-TB1-02",
        "book": "三體1：瘋狂年代",
        "standard_answer": "宇宙閃爍發生在 3K 宇宙微波背景輻射上。",
        "criteria": [
            {"label": "宇宙閃爍", "weight": 2, "aliases": ["宇宙闪烁", "宇宙閃爍"]},
            {"label": "3K", "weight": 1, "aliases": ["3K", "三K"]},
            {"label": "微波背景輻射", "weight": 2, "aliases": ["微波背景辐射", "微波背景輻射", "背景辐射", "背景輻射"]},
        ],
        "questions": [
            "小說中「宇宙閃爍」是在哪種背景輻射上被觀測到的？",
            "汪淼去天文館看到整個宇宙像燈一樣閃動，那個觀測目標是什麼？",
            "宇宙閃爍 3K 背景輻射",
            "三體第一部裡，讓汪淼崩潰的全天空閃爍現象，和哪個宇宙學觀測量有關？",
        ],
    },
    {
        "id": "MIX-TB1-03",
        "book": "三體1：瘋狂年代",
        "standard_answer": "《寂靜的春天》讓葉文潔開始理性思考人類之惡。",
        "criteria": [
            {"label": "寂靜的春天", "weight": 2, "aliases": ["寂静的春天", "寂靜的春天"]},
            {"label": "葉文潔", "weight": 1, "aliases": ["叶文洁", "葉文潔"]},
            {"label": "人類之惡", "weight": 2, "aliases": ["人类之恶", "人類之惡", "人类的恶", "人類的惡"]},
        ],
        "questions": [
            "哪一本書使葉文潔開始理性思考人類之惡？",
            "葉文潔在大興安嶺時讀到一本環保著作，這本書如何影響她看待人類？",
            "葉文潔 寂靜的春天 人類之惡",
            "在三體第一部中，白沐霖借給葉文潔的那本書，對她後來的文明觀造成了什麼影響？",
        ],
    },
    {
        "id": "MIX-TB1-04",
        "book": "三體1：瘋狂年代",
        "standard_answer": "三體監聽員警告地球不要回答三體文明的訊息。",
        "criteria": [
            {"label": "監聽員", "weight": 1, "aliases": ["监听员", "監聽員", "1379"]},
            {"label": "不要回答", "weight": 3, "aliases": ["不要回答", "不要回复", "不要回覆"]},
            {"label": "三體訊息", "weight": 1, "aliases": ["三体", "三體", "信息", "訊息", "信号", "訊號"]},
        ],
        "questions": [
            "三體監聽員第一次收到地球訊息後，給地球的警告是什麼？",
            "那個遙遠文明中比較善意的值守者，為什麼要連續警告地球不要做某件事？",
            "1379 監聽員 不要回答",
            "紅岸訊號被接收後，三體世界中負責監聽的人對地球發出了哪句核心警告？",
        ],
    },
    {
        "id": "MIX-TB1-05",
        "book": "三體1：瘋狂年代",
        "standard_answer": "葉文潔利用太陽作為放大器向宇宙發送訊息。",
        "criteria": [
            {"label": "葉文潔", "weight": 1, "aliases": ["叶文洁", "葉文潔"]},
            {"label": "太陽", "weight": 2, "aliases": ["太阳", "太陽"]},
            {"label": "放大訊號", "weight": 2, "aliases": ["放大", "增益", "发射", "發射", "信号", "訊號", "信息", "訊息"]},
        ],
        "questions": [
            "葉文潔是利用什麼天體放大紅岸基地發出的訊號？",
            "紅岸基地裡，葉文潔發現可以把哪個天體當成巨大天線的一部分？",
            "葉文潔 太陽 放大 訊號",
            "如果把紅岸工程的突破說成「借用恆星增益」，那個被借用的天體是什麼？",
        ],
    },
    {
        "id": "MIX-TB1-06",
        "book": "三體1：瘋狂年代",
        "standard_answer": "三體遊戲用亂紀元、恆紀元和三日凌空呈現三體世界的生存危機。",
        "criteria": [
            {"label": "亂紀元", "weight": 1, "aliases": ["乱纪元", "亂紀元"]},
            {"label": "恆紀元", "weight": 1, "aliases": ["恒纪元", "恆紀元"]},
            {"label": "三日凌空", "weight": 1, "aliases": ["三日凌空", "三个太阳", "三個太陽"]},
            {"label": "三體世界危機", "weight": 2, "aliases": ["三体世界", "三體世界", "毁灭", "毀滅", "脱水", "脫水", "生存"]},
        ],
        "questions": [
            "三體遊戲如何讓玩家理解三體世界的天文災難？",
            "玩家在遊戲裡反覆看到文明被寒冷、酷熱與三個太陽摧毀，這是在說明什麼？",
            "三體遊戲 亂紀元 恆紀元 三日凌空",
            "從新手玩家角度看，《三體》遊戲中脫水、復活和三顆太陽的設定，想傳達哪個世界的危機？",
        ],
    },
    {
        "id": "MIX-TB1-07",
        "book": "三體1：瘋狂年代",
        "standard_answer": "地球三體組織主要分成降臨派、拯救派和倖存派等派別。",
        "criteria": [
            {"label": "降臨派", "weight": 2, "aliases": ["降临派", "降臨派"]},
            {"label": "拯救派", "weight": 2, "aliases": ["拯救派"]},
            {"label": "倖存派", "weight": 1, "aliases": ["幸存派", "倖存派"]},
        ],
        "questions": [
            "地球三體組織內部有哪些主要派別？",
            "ETO 並不是鐵板一塊，小說裡提到它內部大致分成哪些陣營？",
            "ETO 降臨派 拯救派 倖存派",
            "如果一個人問地球叛軍中誰希望毀滅人類、誰崇拜三體文明，他其實是在問哪幾個派別？",
        ],
    },
    {
        "id": "MIX-TB1-08",
        "book": "三體1：瘋狂年代",
        "standard_answer": "古筝行动是在巴拿馬運河用飛刃納米絲切割審判日號，以奪取三體資訊。",
        "criteria": [
            {"label": "古筝行动", "weight": 1, "aliases": ["古筝行动", "古箏行動", "古筝计划", "古箏計劃"]},
            {"label": "審判日號", "weight": 1, "aliases": ["审判日", "審判日"]},
            {"label": "巴拿馬運河", "weight": 1, "aliases": ["巴拿马运河", "巴拿馬運河", "盖拉德水道", "蓋拉德水道"]},
            {"label": "飛刃納米絲", "weight": 1, "aliases": ["飞刃", "飛刃", "纳米丝", "納米絲", "奈米絲"]},
            {"label": "三體資訊", "weight": 1, "aliases": ["三体信息", "三體信息", "三体资料", "三體資料"]},
        ],
        "questions": [
            "古筝行动是什麼？",
            "那個用很多看不見的細線把伊文斯巨輪切成薄片的作戰計畫是什麼？",
            "古箏計劃 審判日號 飛刃 巴拿馬",
            "人類為了在不炸毀伺服器的情況下取得第二紅岸基地資料，於巴拿馬運河採取了哪個行動？",
        ],
    },
    {
        "id": "MIX-TB1-09",
        "book": "三體1：瘋狂年代",
        "standard_answer": "智子是三體文明把質子展開並改造成的超級智能粒子，用來監視地球並干擾基礎科學。",
        "criteria": [
            {"label": "智子", "weight": 1, "aliases": ["智子"]},
            {"label": "質子", "weight": 1, "aliases": ["质子", "質子"]},
            {"label": "監視地球", "weight": 1, "aliases": ["监视", "監視", "观察", "觀察"]},
            {"label": "干擾科學", "weight": 2, "aliases": ["干扰", "干擾", "高能加速器", "基础科学", "基礎科學", "锁死", "鎖死"]},
        ],
        "questions": [
            "智子是什麼？",
            "三體文明用來監視人類、干擾高能物理實驗的微觀裝置是什麼？",
            "智子 質子 高能加速器 鎖死科學",
            "如果把三體對地球科技的封鎖說成一種微觀層級的監控工程，核心工具是什麼？",
        ],
    },
    {
        "id": "MIX-TB1-10",
        "book": "三體1：瘋狂年代",
        "standard_answer": "史強用「蟲子」比喻鼓舞汪淼和丁儀，說蟲子從未被真正戰勝。",
        "criteria": [
            {"label": "史強", "weight": 1, "aliases": ["史强", "史強", "大史"]},
            {"label": "蟲子", "weight": 2, "aliases": ["虫子", "蟲子"]},
            {"label": "沒有被戰勝", "weight": 2, "aliases": ["没有被战胜", "沒有被戰勝", "从来没有真正战胜", "從來沒有真正戰勝"]},
        ],
        "questions": [
            "大史為什麼帶汪淼和丁儀去看蟲子？",
            "在士氣崩潰時，史強用哪種弱小生命提醒人類不要放棄？",
            "大史 蟲子 從未戰勝",
            "三體第一部結尾，誰用田野裡的昆蟲向科學家說明弱者仍有生存韌性？",
        ],
    },
    {
        "id": "MIX-TB2-01",
        "book": "三體2：黑暗森林",
        "standard_answer": "面壁者包括泰勒、雷迪亞茲、希恩斯和羅輯。",
        "criteria": [
            {"label": "泰勒", "weight": 1, "aliases": ["泰勒"]},
            {"label": "雷迪亞茲", "weight": 1, "aliases": ["雷迪亚兹", "雷迪亞茲"]},
            {"label": "希恩斯", "weight": 1, "aliases": ["希恩斯"]},
            {"label": "羅輯", "weight": 2, "aliases": ["罗辑", "羅輯"]},
        ],
        "questions": [
            "四位面壁者分別是誰？",
            "聯合國選出的四個要對三體隱藏真實戰略的人是哪幾位？",
            "面壁者 泰勒 雷迪亞茲 希恩斯 羅輯",
            "危機紀元初期，人類把希望寄託在四名可以欺騙敵人的人物身上，他們是誰？",
        ],
    },
    {
        "id": "MIX-TB2-02",
        "book": "三體2：黑暗森林",
        "standard_answer": "黑暗森林理論由羅輯提出，核心包含宇宙文明公理、猜疑鏈與技術爆炸。",
        "criteria": [
            {"label": "羅輯", "weight": 1, "aliases": ["罗辑", "羅輯"]},
            {"label": "宇宙文明公理", "weight": 1, "aliases": ["宇宙文明公理"]},
            {"label": "猜疑鏈", "weight": 2, "aliases": ["猜疑链", "猜疑鏈"]},
            {"label": "技術爆炸", "weight": 1, "aliases": ["技术爆炸", "技術爆炸"]},
        ],
        "questions": [
            "黑暗森林理論的核心推理包括哪些概念？",
            "羅輯向大史解釋宇宙文明為何互相恐懼時，提到了哪兩個關鍵機制？",
            "黑暗森林 猜疑鏈 技術爆炸",
            "如果宇宙像一片不能暴露位置的森林，小說用哪些公理和推論支撐這個判斷？",
        ],
    },
    {
        "id": "MIX-TB2-03",
        "book": "三體2：黑暗森林",
        "standard_answer": "羅輯用對恆星發出咒語的方式驗證黑暗森林威懾。",
        "criteria": [
            {"label": "羅輯", "weight": 1, "aliases": ["罗辑", "羅輯"]},
            {"label": "咒語", "weight": 1, "aliases": ["咒语", "咒語"]},
            {"label": "恆星", "weight": 1, "aliases": ["恒星", "恆星", "187J3X1"]},
            {"label": "黑暗森林威懾", "weight": 2, "aliases": ["黑暗森林", "威慑", "威懾", "坐标", "座標"]},
        ],
        "questions": [
            "羅輯的「咒語」實驗是為了驗證什麼？",
            "那個向宇宙暴露一顆恆星坐標的行動，後來證明了哪個宇宙規律？",
            "羅輯 咒語 恆星 黑暗森林",
            "從檢索角度看，羅輯把一組星際坐標送出去後等待結果，這件事和哪種威懾思想有關？",
        ],
    },
    {
        "id": "MIX-TB2-04",
        "book": "三體2：黑暗森林",
        "standard_answer": "水滴是三體文明的強互作用力宇宙探測器。",
        "criteria": [
            {"label": "水滴", "weight": 1, "aliases": ["水滴"]},
            {"label": "三體文明", "weight": 1, "aliases": ["三体文明", "三體文明", "三体世界", "三體世界"]},
            {"label": "強互作用力", "weight": 2, "aliases": ["强互作用力", "強互作用力"]},
            {"label": "宇宙探測器", "weight": 1, "aliases": ["宇宙探测器", "宇宙探測器", "探测器", "探測器"]},
        ],
        "questions": [
            "水滴是什麼？",
            "那個外形像一滴水、表面極度光滑的三體造物，正式說法是什麼？",
            "水滴 強互作用力 探測器",
            "如果新人把水滴當成和平信物，後續劇情揭露它真正是三體文明的哪種裝置？",
        ],
    },
    {
        "id": "MIX-TB2-05",
        "book": "三體2：黑暗森林",
        "standard_answer": "末日戰役中，水滴摧毀了人類太空艦隊。",
        "criteria": [
            {"label": "末日戰役", "weight": 1, "aliases": ["末日战役", "末日戰役"]},
            {"label": "水滴", "weight": 2, "aliases": ["水滴"]},
            {"label": "摧毀艦隊", "weight": 2, "aliases": ["摧毁", "摧毀", "舰队", "艦隊", "战舰", "戰艦"]},
        ],
        "questions": [
            "末日戰役中真正摧毀人類艦隊的是什麼？",
            "人類以為要迎接三體主力艦隊，結果哪個小型物體擊潰了太空力量？",
            "末日戰役 水滴 艦隊",
            "如果問三體第二部裡人類最大太空軍事災難的直接武器，答案應該是什麼？",
        ],
    },
    {
        "id": "MIX-TB2-06",
        "book": "三體2：黑暗森林",
        "standard_answer": "章北海劫持自然選擇號逃離太陽系。",
        "criteria": [
            {"label": "章北海", "weight": 2, "aliases": ["章北海"]},
            {"label": "自然選擇號", "weight": 2, "aliases": ["自然选择号", "自然選擇號"]},
            {"label": "逃離", "weight": 1, "aliases": ["逃离", "逃離", "离开太阳系", "離開太陽系"]},
        ],
        "questions": [
            "章北海帶走的是哪一艘戰艦？",
            "那位長期隱藏失敗主義信念的軍官，最後劫持哪艘船逃離？",
            "章北海 自然選擇號 逃離",
            "在黑暗森林中，哪個人物讓一艘星艦成為逃亡人類文明的開端？",
        ],
    },
    {
        "id": "MIX-TB2-07",
        "book": "三體2：黑暗森林",
        "standard_answer": "思想鋼印會把特定信念永久刻入人的思想。",
        "criteria": [
            {"label": "思想鋼印", "weight": 2, "aliases": ["思想钢印", "思想鋼印"]},
            {"label": "信念", "weight": 1, "aliases": ["信念", "思想"]},
            {"label": "永久刻入", "weight": 2, "aliases": ["永久", "刻入", "钢印", "鋼印", "不可改变", "不可改變"]},
        ],
        "questions": [
            "思想鋼印的作用是什麼？",
            "希恩斯相關計畫裡，那個能把某種信念壓進人腦深處的技術叫什麼？",
            "思想鋼印 信念 永久",
            "如果用心理控制角度描述面壁計畫中的一項危險技術，它如何改變人的信念？",
        ],
    },
    {
        "id": "MIX-TB2-08",
        "book": "三體2：黑暗森林",
        "standard_answer": "羅輯成為第一代執劍者，建立黑暗森林威懾。",
        "criteria": [
            {"label": "羅輯", "weight": 2, "aliases": ["罗辑", "羅輯"]},
            {"label": "執劍者", "weight": 2, "aliases": ["执剑人", "執劍人", "执剑者", "執劍者"]},
            {"label": "威懾", "weight": 1, "aliases": ["威慑", "威懾", "黑暗森林"]},
        ],
        "questions": [
            "第一代執劍者是誰？",
            "三體危機中，誰以同歸於盡式的坐標廣播建立威懾？",
            "第一代 執劍者 羅輯",
            "如果新讀者問拿著引力波廣播開關守住地球的人是誰，標準答案是什麼？",
        ],
    },
    {
        "id": "MIX-TB2-09",
        "book": "三體2：黑暗森林",
        "standard_answer": "青銅時代號和藍色空間號在逃亡後形成了星艦人類的雛形。",
        "criteria": [
            {"label": "青銅時代號", "weight": 1, "aliases": ["青铜时代", "青銅時代"]},
            {"label": "藍色空間號", "weight": 1, "aliases": ["蓝色空间", "藍色空間"]},
            {"label": "星艦人類", "weight": 2, "aliases": ["星舰人类", "星艦人類", "星舰地球", "星艦地球"]},
            {"label": "逃亡", "weight": 1, "aliases": ["逃亡", "离开太阳系", "離開太陽系"]},
        ],
        "questions": [
            "哪些星艦和星艦人類的誕生有關？",
            "末日戰役後，逃離太陽系的兩艘關鍵戰艦是哪兩艘？",
            "青銅時代 藍色空間 星艦人類",
            "如果把人類文明分成地球人類與太空逃亡者，後者最早和哪些艦船有關？",
        ],
    },
    {
        "id": "MIX-TB2-10",
        "book": "三體2：黑暗森林",
        "standard_answer": "雪地工程試圖用太空塵埃顯示三體艦隊航跡，但沒有真正成功。",
        "criteria": [
            {"label": "雪地工程", "weight": 2, "aliases": ["雪地工程"]},
            {"label": "太空塵埃", "weight": 1, "aliases": ["太空尘埃", "太空塵埃", "尘埃", "塵埃"]},
            {"label": "三體艦隊航跡", "weight": 1, "aliases": ["三体舰队", "三體艦隊", "航迹", "航跡", "尾迹", "尾跡"]},
            {"label": "未成功", "weight": 1, "aliases": ["未能", "没有成功", "沒有成功", "从来未能", "從來未能"]},
        ],
        "questions": [
            "雪地工程原本想達成什麼目的？",
            "羅輯提出的那個利用塵埃觀測敵方航跡的工程，為什麼重要但沒有真正完成？",
            "雪地工程 太空塵埃 三體艦隊",
            "如果有人問用一片人造宇宙灰塵來捕捉水滴或艦隊尾跡的構想，這是什麼工程？",
        ],
    },
    {
        "id": "MIX-TB3-01",
        "book": "三體3：死神永生",
        "standard_answer": "階梯計畫把雲天明的大腦送向三體艦隊。",
        "criteria": [
            {"label": "階梯計畫", "weight": 1, "aliases": ["阶梯计划", "階梯計畫"]},
            {"label": "雲天明", "weight": 2, "aliases": ["云天明", "雲天明"]},
            {"label": "大腦", "weight": 1, "aliases": ["大脑", "大腦", "脑", "腦"]},
            {"label": "三體艦隊", "weight": 1, "aliases": ["三体舰队", "三體艦隊"]},
        ],
        "questions": [
            "階梯計畫送往三體艦隊的是誰的大腦？",
            "PIA 那個只能送出極小質量的探測方案，最後選中了哪個人的腦？",
            "階梯計畫 雲天明 大腦",
            "如果把第三部開頭的人體發射任務說成一次星際情報投送，它送出的核心載荷是什麼？",
        ],
    },
    {
        "id": "MIX-TB3-02",
        "book": "三體3：死神永生",
        "standard_answer": "雲天明暗戀程心，並把一顆星星送給她。",
        "criteria": [
            {"label": "雲天明", "weight": 1, "aliases": ["云天明", "雲天明"]},
            {"label": "程心", "weight": 2, "aliases": ["程心"]},
            {"label": "送星星", "weight": 2, "aliases": ["送给她一颗星星", "送給她一顆星星", "买星星", "買星星", "DX3906"]},
        ],
        "questions": [
            "雲天明暗戀的大學同學是誰？",
            "那位身患絕症的男人買下一顆星送給誰？",
            "雲天明 程心 星星",
            "如果新讀者只記得有個人臨死前送出一顆恆星，這份禮物的對象是誰？",
        ],
    },
    {
        "id": "MIX-TB3-03",
        "book": "三體3：死神永生",
        "standard_answer": "程心接替羅輯成為第二任執劍者，但威懾在交接後失敗。",
        "criteria": [
            {"label": "程心", "weight": 2, "aliases": ["程心"]},
            {"label": "第二任執劍者", "weight": 1, "aliases": ["第二任", "执剑人", "執劍人", "执剑者", "執劍者"]},
            {"label": "羅輯", "weight": 1, "aliases": ["罗辑", "羅輯"]},
            {"label": "威懾失敗", "weight": 1, "aliases": ["威慑", "威懾", "失败", "失敗", "交接"]},
        ],
        "questions": [
            "誰接替羅輯成為第二任執劍者？",
            "威懾控制權交接時，人類選出的新執劍人是誰，結果如何？",
            "程心 第二任 執劍者 威懾失敗",
            "如果問題問的是羅輯交出開關後那位沒有按下廣播的人，答案是哪位角色？",
        ],
    },
    {
        "id": "MIX-TB3-04",
        "book": "三體3：死神永生",
        "standard_answer": "威懾失敗後，智子要求人類遷往澳大利亞並解除武裝。",
        "criteria": [
            {"label": "智子", "weight": 1, "aliases": ["智子"]},
            {"label": "澳大利亞", "weight": 2, "aliases": ["澳大利亚", "澳大利亞"]},
            {"label": "解除武裝", "weight": 1, "aliases": ["解除武装", "解除武裝", "裸移民"]},
            {"label": "威懾失敗", "weight": 1, "aliases": ["威慑", "威懾", "失败", "失敗"]},
        ],
        "questions": [
            "威懾失敗後，智子要求人類主要遷往哪裡？",
            "三體世界重新取得主導權後，把地球人類圈定到哪個保留地？",
            "智子 澳大利亞 裸移民",
            "如果問威懾後人類被要求解除武裝並集中遷移到哪裡，答案是什麼？",
        ],
    },
    {
        "id": "MIX-TB3-05",
        "book": "三體3：死神永生",
        "standard_answer": "藍色空間號和萬有引力號最終啟動引力波廣播，暴露三體星系坐標。",
        "criteria": [
            {"label": "藍色空間號", "weight": 1, "aliases": ["蓝色空间", "藍色空間"]},
            {"label": "萬有引力號", "weight": 1, "aliases": ["万有引力", "萬有引力"]},
            {"label": "引力波廣播", "weight": 2, "aliases": ["引力波", "广播", "廣播"]},
            {"label": "坐標暴露", "weight": 1, "aliases": ["坐标", "座標", "暴露", "三体星系", "三體星系"]},
        ],
        "questions": [
            "哪兩艘飛船最終啟動引力波廣播？",
            "水滴追擊失敗後，哪組星艦把三體世界的位置發送到宇宙中？",
            "藍色空間 萬有引力 引力波廣播",
            "如果把黑暗森林威懾真正引爆的那次廣播視為星艦人類的行動，涉及哪兩艘船？",
        ],
    },
    {
        "id": "MIX-TB3-06",
        "book": "三體3：死神永生",
        "standard_answer": "雲天明用三個童話故事向人類傳遞關鍵情報。",
        "criteria": [
            {"label": "雲天明", "weight": 1, "aliases": ["云天明", "雲天明"]},
            {"label": "三個童話", "weight": 2, "aliases": ["三个故事", "三個故事", "童话", "童話"]},
            {"label": "傳遞情報", "weight": 2, "aliases": ["情报", "情報", "信息", "訊息", "传递", "傳遞"]},
        ],
        "questions": [
            "雲天明用什麼形式向人類傳遞三體世界允許範圍內的情報？",
            "程心與雲天明見面時，那些看似兒童故事的內容其實承載了什麼作用？",
            "雲天明 童話 三個故事 情報",
            "如果讀者問第三部中最像謎語的情報傳遞方式是什麼，應該指向哪段情節？",
        ],
    },
    {
        "id": "MIX-TB3-07",
        "book": "三體3：死神永生",
        "standard_answer": "掩體計畫讓人類躲到巨行星背後，以避開黑暗森林打擊。",
        "criteria": [
            {"label": "掩體計畫", "weight": 2, "aliases": ["掩体计划", "掩體計畫"]},
            {"label": "巨行星", "weight": 1, "aliases": ["巨行星", "木星", "土星", "海王星"]},
            {"label": "躲避打擊", "weight": 2, "aliases": ["躲避", "避开", "避開", "黑暗森林打击", "黑暗森林打擊"]},
        ],
        "questions": [
            "掩體計畫的基本想法是什麼？",
            "人類後期為了不被黑暗森林打擊直接摧毀，選擇把文明藏到哪類天體背後？",
            "掩體計畫 巨行星 黑暗森林打擊",
            "如果把第三部的人類自救方案說成「躲在行星陰影裡」，這是哪個計畫？",
        ],
    },
    {
        "id": "MIX-TB3-08",
        "book": "三體3：死神永生",
        "standard_answer": "最終摧毀太陽系的降維武器是二向箔。",
        "criteria": [
            {"label": "二向箔", "weight": 3, "aliases": ["二向箔"]},
            {"label": "降維", "weight": 1, "aliases": ["降维", "降維", "二维化", "二維化"]},
            {"label": "太陽系", "weight": 1, "aliases": ["太阳系", "太陽系"]},
        ],
        "questions": [
            "最終摧毀太陽系的降維武器叫什麼？",
            "歌者文明清理太陽系時，投下的那個能把空間壓成二維的東西是什麼？",
            "二向箔 降維 太陽系",
            "如果有人只記得太陽系像畫一樣被壓平，那個武器名稱是什麼？",
        ],
    },
    {
        "id": "MIX-TB3-09",
        "book": "三體3：死神永生",
        "standard_answer": "羅輯在冥王星上守護人類文明博物館。",
        "criteria": [
            {"label": "羅輯", "weight": 2, "aliases": ["罗辑", "羅輯"]},
            {"label": "冥王星", "weight": 1, "aliases": ["冥王星"]},
            {"label": "文明博物館", "weight": 2, "aliases": ["文明博物馆", "文明博物館", "人类文明", "人類文明", "博物馆", "博物館"]},
        ],
        "questions": [
            "冥王星上守護人類文明記憶的人是誰？",
            "太陽系末日來臨前，那位在遙遠矮行星上看守文明遺產的老人是誰？",
            "冥王星 人類文明博物館 羅輯",
            "如果問題提到最後的地球文明記憶被保存在冥王星，負責守護它的是哪位角色？",
        ],
    },
    {
        "id": "MIX-TB3-10",
        "book": "三體3：死神永生",
        "standard_answer": "維德推動光速飛船與曲率驅動相關研究，並與程心在星環城衝突。",
        "criteria": [
            {"label": "維德", "weight": 2, "aliases": ["维德", "維德", "托马斯·维德", "托馬斯·維德"]},
            {"label": "光速飛船", "weight": 1, "aliases": ["光速飞船", "光速飛船", "曲率驱动", "曲率驅動"]},
            {"label": "程心", "weight": 1, "aliases": ["程心"]},
            {"label": "星環城", "weight": 1, "aliases": ["星环城", "星環城"]},
        ],
        "questions": [
            "維德在星環城推動的是哪類飛船技術？",
            "那位願意為人類保留光速逃亡可能的人，和程心在星環城因什麼技術路線衝突？",
            "維德 星環城 光速飛船 曲率驅動",
            "如果從逃離太陽系的技術角度看，維德最執著推動的是哪種航行能力？",
        ],
    },
    {
        "id": "MIX-TB3-11",
        "book": "三體3：死神永生",
        "standard_answer": "程心和 AA 最終進入雲天明送給程心的小宇宙。",
        "criteria": [
            {"label": "程心", "weight": 1, "aliases": ["程心"]},
            {"label": "AA", "weight": 1, "aliases": ["AA", "艾AA"]},
            {"label": "雲天明", "weight": 1, "aliases": ["云天明", "雲天明"]},
            {"label": "小宇宙", "weight": 2, "aliases": ["小宇宙", "647号宇宙", "647號宇宙"]},
        ],
        "questions": [
            "程心和 AA 最後進入了誰送來的小宇宙？",
            "太陽系毀滅後，程心與 AA 躲進的那個封閉世界和哪位人物有關？",
            "程心 AA 雲天明 小宇宙",
            "如果問第三部結尾那個讓兩人暫時脫離大宇宙的避難空間，來源是誰？",
        ],
    },
    {
        "id": "MIX-TB3-12",
        "book": "三體3：死神永生",
        "standard_answer": "關一帆向程心解釋大宇宙、小宇宙與歸還質量等問題。",
        "criteria": [
            {"label": "關一帆", "weight": 2, "aliases": ["关一帆", "關一帆"]},
            {"label": "小宇宙", "weight": 1, "aliases": ["小宇宙"]},
            {"label": "歸還質量", "weight": 2, "aliases": ["归还质量", "歸還質量", "质量", "質量", "大宇宙"]},
        ],
        "questions": [
            "關一帆在結尾主要向程心解釋哪些宇宙尺度的問題？",
            "那位在遠未來遇到程心的人，如何說明小宇宙對大宇宙的影響？",
            "關一帆 小宇宙 歸還質量",
            "如果問題問的是誰把大宇宙重啟與小宇宙質量問題講給程心聽，答案是誰？",
        ],
    },
    {
        "id": "MIX-TB1-11",
        "book": "三體1：瘋狂年代",
        "standard_answer": "葉哲泰在文化大革命批鬥中被紅衛兵毆打致死。",
        "criteria": [
            {"label": "葉哲泰", "weight": 2, "aliases": ["叶哲泰", "葉哲泰"]},
            {"label": "文革批鬥", "weight": 1, "aliases": ["文化大革命", "文革", "批斗", "批鬥"]},
            {"label": "紅衛兵", "weight": 1, "aliases": ["红卫兵", "紅衛兵"]},
            {"label": "死亡", "weight": 1, "aliases": ["死", "死亡", "夺去生命", "奪去生命"]},
        ],
        "questions": [
            "葉文潔的父親葉哲泰是如何去世的？",
            "小說開頭那場批鬥中，被紅衛兵暴力奪去生命的物理學家是誰？",
            "葉哲泰 文革 批鬥 紅衛兵",
            "如果新讀者問葉文潔為何一開始就對人類文明產生巨大創傷，父親遭遇了什麼？",
        ],
    },
    {
        "id": "MIX-TB1-12",
        "book": "三體1：瘋狂年代",
        "standard_answer": "伊文斯建立第二紅岸基地，核心載體是審判日號。",
        "criteria": [
            {"label": "伊文斯", "weight": 1, "aliases": ["伊文斯", "Evans"]},
            {"label": "第二紅岸基地", "weight": 2, "aliases": ["第二红岸基地", "第二紅岸基地"]},
            {"label": "審判日號", "weight": 2, "aliases": ["审判日", "審判日"]},
        ],
        "questions": [
            "伊文斯把第二紅岸基地建在哪裡？",
            "地球三體組織與三體通訊的重要資料，主要藏在伊文斯哪艘巨輪上？",
            "伊文斯 第二紅岸基地 審判日號",
            "如果問題問 ETO 海上基地的核心載體，應該指向哪艘船？",
        ],
    },
    {
        "id": "MIX-TB1-13",
        "book": "三體1：瘋狂年代",
        "standard_answer": "人列計算機是用大量士兵組成人體邏輯門來運算三體問題。",
        "criteria": [
            {"label": "人列計算機", "weight": 2, "aliases": ["人列计算机", "人列計算機"]},
            {"label": "士兵", "weight": 1, "aliases": ["士兵", "秦军", "秦軍"]},
            {"label": "邏輯門", "weight": 1, "aliases": ["逻辑门", "邏輯門", "门电路", "門電路"]},
            {"label": "三體問題", "weight": 1, "aliases": ["三体问题", "三體問題"]},
        ],
        "questions": [
            "人列計算機是怎麼運作的？",
            "秦始皇、牛頓和馮·諾依曼在遊戲中組織大軍計算，這套系統叫什麼？",
            "人列計算機 士兵 邏輯門 三體問題",
            "如果有人問用真人排成電路來預測太陽運行的裝置，答案是什麼？",
        ],
    },
    {
        "id": "MIX-TB1-14",
        "book": "三體1：瘋狂年代",
        "standard_answer": "降臨派希望三體文明降臨並毀滅或懲罰人類。",
        "criteria": [
            {"label": "降臨派", "weight": 2, "aliases": ["降临派", "降臨派"]},
            {"label": "三體降臨", "weight": 1, "aliases": ["三体降临", "三體降臨", "主降临", "主降臨"]},
            {"label": "毀滅人類", "weight": 2, "aliases": ["毁灭全人类", "毀滅全人類", "惩罚", "懲罰"]},
        ],
        "questions": [
            "降臨派的目標是什麼？",
            "ETO 中哪個派別希望三體文明到來並對人類執行懲罰？",
            "降臨派 毀滅全人類 主降臨",
            "如果問伊文斯一脈最極端的政治宗教式願望，答案應該是哪個派別的哪種目標？",
        ],
    },
    {
        "id": "MIX-TB2-11",
        "book": "三體2：黑暗森林",
        "standard_answer": "泰勒的面壁計畫與建立太空力量、宏原子核聚變等構想有關。",
        "criteria": [
            {"label": "泰勒", "weight": 2, "aliases": ["泰勒"]},
            {"label": "太空力量", "weight": 1, "aliases": ["太空力量", "独立的太空力量", "獨立的太空力量"]},
            {"label": "宏原子核聚變", "weight": 2, "aliases": ["宏原子核聚变", "宏原子核聚變"]},
        ],
        "questions": [
            "泰勒的面壁計畫主要涉及什麼武器或力量構想？",
            "那位面壁者一開始找丁儀談宏原子核聚變，他想建立什麼？",
            "泰勒 宏原子核聚變 太空力量",
            "如果問題問四位面壁者中與太空軍和宏聚變武器最相關的人是誰，答案是什麼？",
        ],
    },
    {
        "id": "MIX-TB2-12",
        "book": "三體2：黑暗森林",
        "standard_answer": "雷迪亞茲的計畫與水星和恆星型氫彈威懾有關。",
        "criteria": [
            {"label": "雷迪亞茲", "weight": 2, "aliases": ["雷迪亚兹", "雷迪亞茲"]},
            {"label": "水星", "weight": 1, "aliases": ["水星"]},
            {"label": "氫彈", "weight": 1, "aliases": ["氢弹", "氫彈", "恒星型氢弹", "恆星型氫彈"]},
            {"label": "威懾", "weight": 1, "aliases": ["威慑", "威懾"]},
        ],
        "questions": [
            "雷迪亞茲的面壁計畫和哪顆行星及哪類武器有關？",
            "那個被自己國家民眾處死的面壁者，構想中牽涉到水星與大量氫彈，這人是誰？",
            "雷迪亞茲 水星 氫彈",
            "如果問面壁計畫裡最像用行星級災難反制三體的方案，涉及哪位面壁者？",
        ],
    },
    {
        "id": "MIX-TB2-13",
        "book": "三體2：黑暗森林",
        "standard_answer": "破壁人是三體派來或ETO安排來識破面壁者真實意圖的人。",
        "criteria": [
            {"label": "破壁人", "weight": 2, "aliases": ["破壁人"]},
            {"label": "識破面壁者", "weight": 2, "aliases": ["识破", "識破", "面壁者", "真实意图", "真實意圖"]},
            {"label": "三體或ETO", "weight": 1, "aliases": ["三体", "三體", "ETO", "地球三体组织", "地球三體組織"]},
        ],
        "questions": [
            "破壁人的任務是什麼？",
            "和面壁者相對，那些專門揭穿隱藏戰略的人被稱為什麼？",
            "破壁人 面壁者 真實意圖",
            "如果三體陣營想破解人類面壁計畫，需要派出哪類角色？",
        ],
    },
    {
        "id": "MIX-TB2-14",
        "book": "三體2：黑暗森林",
        "standard_answer": "黑暗森林威懾要求雙方相信坐標一旦暴露就會引來毀滅性打擊。",
        "criteria": [
            {"label": "黑暗森林威懾", "weight": 2, "aliases": ["黑暗森林威慑", "黑暗森林威懾"]},
            {"label": "坐標暴露", "weight": 1, "aliases": ["坐标", "座標", "暴露"]},
            {"label": "毀滅打擊", "weight": 2, "aliases": ["毁灭", "毀滅", "打击", "打擊", "清理"]},
        ],
        "questions": [
            "黑暗森林威懾靠什麼讓三體不敢進攻？",
            "羅輯手中的廣播開關為何能嚇阻三體世界？",
            "黑暗森林威懾 坐標 暴露 毀滅",
            "如果問一個文明的位置被公開後為何會變成武器，這涉及哪種威懾邏輯？",
        ],
    },
    {
        "id": "MIX-TB3-13",
        "book": "三體3：死神永生",
        "standard_answer": "歌者使用光粒摧毀恆星，也使用二向箔清理太陽系。",
        "criteria": [
            {"label": "歌者", "weight": 1, "aliases": ["歌者"]},
            {"label": "光粒", "weight": 2, "aliases": ["光粒"]},
            {"label": "二向箔", "weight": 2, "aliases": ["二向箔"]},
        ],
        "questions": [
            "歌者文明使用過哪些清理工具？",
            "那個在宇宙中負責清除暴露文明的角色，和光粒、二向箔有什麼關係？",
            "歌者 光粒 二向箔",
            "如果問第三部中宇宙清理者如何處理暴露目標，應該檢索哪些武器名稱？",
        ],
    },
    {
        "id": "MIX-TB3-14",
        "book": "三體3：死神永生",
        "standard_answer": "黑域是低光速區域，能讓文明對外顯示安全但也限制自身發展。",
        "criteria": [
            {"label": "黑域", "weight": 2, "aliases": ["黑域"]},
            {"label": "低光速", "weight": 2, "aliases": ["低光速", "光速降低", "光速为每秒16.7千米", "光速為每秒16.7千米"]},
            {"label": "安全聲明", "weight": 1, "aliases": ["安全声明", "安全聲明", "安全", "隔绝", "隔絕"]},
        ],
        "questions": [
            "黑域是什麼？",
            "第三部裡，一個文明把自己包在低光速區域中，這代表什麼策略？",
            "黑域 低光速 安全聲明",
            "如果問讓外界知道自己不再具備威脅、但也近乎自我封閉的宇宙工程，是什麼概念？",
        ],
    },
    {
        "id": "MIX-TB3-15",
        "book": "三體3：死神永生",
        "standard_answer": "光速飛船依靠曲率驅動，航跡可能留下低光速痕跡。",
        "criteria": [
            {"label": "光速飛船", "weight": 2, "aliases": ["光速飞船", "光速飛船"]},
            {"label": "曲率驅動", "weight": 2, "aliases": ["曲率驱动", "曲率驅動"]},
            {"label": "航跡", "weight": 1, "aliases": ["航迹", "航跡", "痕迹", "痕跡"]},
        ],
        "questions": [
            "光速飛船依靠什麼推進方式？",
            "雲天明童話暗示的高速逃亡技術，在科學解讀中對應哪種驅動？",
            "光速飛船 曲率驅動 航跡",
            "如果問第三部裡真正能逃離黑暗森林打擊的飛船技術，核心詞是什麼？",
        ],
    },
    {
        "id": "MIX-TB3-16",
        "book": "三體3：死神永生",
        "standard_answer": "程心多次因道德選擇放棄更激進方案，影響威懾與光速飛船路線。",
        "criteria": [
            {"label": "程心", "weight": 2, "aliases": ["程心"]},
            {"label": "道德選擇", "weight": 1, "aliases": ["道德", "选择", "選擇", "责任", "責任"]},
            {"label": "威懾", "weight": 1, "aliases": ["威慑", "威懾", "执剑", "執劍"]},
            {"label": "光速飛船", "weight": 1, "aliases": ["光速飞船", "光速飛船", "维德", "維德"]},
        ],
        "questions": [
            "程心的道德選擇主要影響了哪些關鍵路線？",
            "如果用角色弧線來看，程心在哪些大事件中因不願採取極端手段而改變人類命運？",
            "程心 道德選擇 威懾 光速飛船",
            "第三部裡，那位多次代表人性良知卻也承擔巨大後果的角色是誰？",
        ],
    },
    {
        "id": "MIX-TB1-15",
        "book": "三體1：瘋狂年代",
        "standard_answer": "科學邊界與多位科學家自殺和基礎物理危機相關。",
        "criteria": [
            {"label": "科學邊界", "weight": 2, "aliases": ["科学边界", "科學邊界"]},
            {"label": "科學家自殺", "weight": 1, "aliases": ["科学家自杀", "科學家自殺", "自杀", "自殺"]},
            {"label": "基礎物理危機", "weight": 2, "aliases": ["物理学不存在", "物理學不存在", "基础物理", "基礎物理", "高能加速器"]},
        ],
        "questions": [
            "科學邊界和小說開頭的科學家自殺有什麼關係？",
            "汪淼接觸的那個學術組織，為什麼會和物理學危機聯繫在一起？",
            "科學邊界 科學家自殺 物理學不存在",
            "如果問第一部裡讓科學共同體陷入崩潰的組織與現象，應該檢索哪個名稱？",
        ],
    },
    {
        "id": "MIX-TB1-16",
        "book": "三體1：瘋狂年代",
        "standard_answer": "紅岸基地是葉文潔工作的秘密軍事工程基地，也是她向三體發訊息的地方。",
        "criteria": [
            {"label": "紅岸基地", "weight": 2, "aliases": ["红岸基地", "紅岸基地", "红岸", "紅岸"]},
            {"label": "葉文潔", "weight": 1, "aliases": ["叶文洁", "葉文潔"]},
            {"label": "秘密軍事工程", "weight": 1, "aliases": ["秘密", "军事", "軍事", "工程"]},
            {"label": "發訊息", "weight": 1, "aliases": ["发送", "發送", "发射", "發射", "信息", "訊息", "信号", "訊號"]},
        ],
        "questions": [
            "紅岸基地在葉文潔故事中扮演什麼角色？",
            "那座位於雷達峰、讓葉文潔接觸外星文明的秘密工程基地是什麼？",
            "紅岸基地 葉文潔 發送訊號",
            "如果問三體第一部中人類第一次主動聯絡三體的地點，答案是哪裡？",
        ],
    },
    {
        "id": "MIX-TB2-15",
        "book": "三體2：黑暗森林",
        "standard_answer": "東方延緒是自然選擇號艦長，與章北海的逃亡行動密切相關。",
        "criteria": [
            {"label": "東方延緒", "weight": 2, "aliases": ["东方延绪", "東方延緒"]},
            {"label": "自然選擇號", "weight": 2, "aliases": ["自然选择号", "自然選擇號"]},
            {"label": "艦長", "weight": 1, "aliases": ["舰长", "艦長"]},
        ],
        "questions": [
            "自然選擇號的艦長是誰？",
            "章北海實施逃亡時，那艘戰艦的年輕女艦長叫什麼？",
            "東方延緒 自然選擇號 艦長",
            "如果問星艦人類開端中與章北海同船的艦長，答案是哪位角色？",
        ],
    },
    {
        "id": "MIX-TB2-16",
        "book": "三體2：黑暗森林",
        "standard_answer": "大低谷是危機紀元中人類社會長期崩潰、人口銳減的災難時期。",
        "criteria": [
            {"label": "大低谷", "weight": 2, "aliases": ["大低谷"]},
            {"label": "危機紀元", "weight": 1, "aliases": ["危机纪元", "危機紀元"]},
            {"label": "社會崩潰", "weight": 1, "aliases": ["崩溃", "崩潰", "灾难", "災難"]},
            {"label": "人口銳減", "weight": 1, "aliases": ["人口", "锐减", "銳減", "死亡"]},
        ],
        "questions": [
            "大低谷指的是什麼？",
            "三體危機中，人類曾經歷一段長期社會崩潰和人口大減的時期，叫什麼？",
            "大低谷 危機紀元 人口",
            "如果問黑暗森林時間線裡人類文明最慘烈的低潮期，應該檢索哪個詞？",
        ],
    },
    {
        "id": "MIX-TB3-17",
        "book": "三體3：死神永生",
        "standard_answer": "澳大利亞保留地是威懾失敗後三體要求地球人類集中遷入的區域。",
        "criteria": [
            {"label": "澳大利亞", "weight": 2, "aliases": ["澳大利亚", "澳大利亞"]},
            {"label": "保留地", "weight": 1, "aliases": ["保留地"]},
            {"label": "三體要求", "weight": 1, "aliases": ["三体", "三體", "智子", "要求"]},
            {"label": "遷移", "weight": 1, "aliases": ["移民", "迁移", "遷移", "迁往", "遷往"]},
        ],
        "questions": [
            "澳大利亞保留地是什麼？",
            "威懾後第一年，人類為什麼被迫大規模前往澳大利亞？",
            "澳大利亞 保留地 智子 移民",
            "如果問三體接管地球後給人類劃出的主要生存區，答案是哪裡？",
        ],
    },
    {
        "id": "MIX-TB3-18",
        "book": "三體3：死神永生",
        "standard_answer": "星環集團與程心、維德、光速飛船研究有關。",
        "criteria": [
            {"label": "星環集團", "weight": 2, "aliases": ["星环集团", "星環集團", "星环", "星環"]},
            {"label": "程心", "weight": 1, "aliases": ["程心"]},
            {"label": "維德", "weight": 1, "aliases": ["维德", "維德"]},
            {"label": "光速飛船", "weight": 1, "aliases": ["光速飞船", "光速飛船", "曲率驱动", "曲率驅動"]},
        ],
        "questions": [
            "星環集團和光速飛船研究有什麼關係？",
            "程心擁有的那個企業後來被維德用來推動哪項高風險技術？",
            "星環集團 程心 維德 光速飛船",
            "如果問第三部裡商業組織如何成為逃亡技術研發平台，應該查哪個集團？",
        ],
    },
]


DIMENSION_VARIANTS = [
    {
        "answer_style": "factoid",
        "prompt_style": "direct",
        "length_style": "concise_natural",
        "phrasing": "document_similar",
        "user_level": "expert",
    },
    {
        "answer_style": "open_ended",
        "prompt_style": "with_premise",
        "length_style": "verbose_natural",
        "phrasing": "document_distant",
        "user_level": "novice",
    },
    {
        "answer_style": "factoid",
        "prompt_style": "direct",
        "length_style": "short_search_query",
        "phrasing": "document_similar",
        "user_level": "expert",
    },
    {
        "answer_style": "open_ended",
        "prompt_style": "with_premise",
        "length_style": "long_search_query",
        "phrasing": "document_distant",
        "user_level": "novice",
    },
]


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    questions = build_questions()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    questions_path = eval_dir / f"questions_trilogy_mixed200_{timestamp}.json"
    markdown_path = eval_dir / f"questions_trilogy_mixed200_{timestamp}.md"
    raw_path = eval_dir / f"mixed200_retrieval_upper_bound_raw_{timestamp}.jsonl"
    report_path = eval_dir / f"mixed200_retrieval_upper_bound_report_{timestamp}.md"

    questions_path.write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_questions_markdown(questions), encoding="utf-8")

    knowledge_base = active_knowledge_base(project_root=ROOT)
    chunks = load_index(knowledge_base.index_dir / "chunks.json")
    embeddings = load_embedding_matrix(knowledge_base.index_dir / "embeddings.npy")
    qdrant = QdrantVectorStore.in_memory(chunks, embeddings, collection_name=COLLECTION_NAME)

    candidate_k = 50
    rerank_top_k = 8
    final_context_k = 8
    records = []
    started = time.perf_counter()
    with raw_path.open("w", encoding="utf-8") as raw_file:
        for item in questions:
            q_started = time.perf_counter()
            results = _rrf_parent_context_results(
                question=item["question"],
                rewritten_query=item["question"],
                chunks=chunks,
                embeddings=None,
                top_k=rerank_top_k,
                candidate_k=candidate_k,
                final_context_k=final_context_k,
                vector_store=qdrant,
            )
            scored = score_retrieved_context(results, item)
            record = {
                **{key: item.get(key, "") for key in ("id", "book", "answer_style", "prompt_style", "length_style", "phrasing", "user_level")},
                "question": item["question"],
                "standard_answer": item.get("standard_answer", ""),
                "retrieval_upper_bound_score": scored["score"],
                "max_score": scored["max_score"],
                "matched": scored["matched"],
                "missed": scored["missed"],
                "contexts": [_context_record(chunk) for chunk in results],
                "elapsed_seconds": round(time.perf_counter() - q_started, 3),
            }
            records.append(record)
            raw_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            raw_file.flush()
            print(
                f"{record['id']} retrieval_upper={record['retrieval_upper_bound_score']}/{record['max_score']} "
                f"contexts={len(record['contexts'])} elapsed={record['elapsed_seconds']}s",
                flush=True,
            )

    write_report(
        report_path=report_path,
        questions_path=questions_path,
        markdown_path=markdown_path,
        raw_path=raw_path,
        records=records,
        elapsed_seconds=round(time.perf_counter() - started, 3),
        candidate_k=candidate_k,
        rerank_top_k=rerank_top_k,
        final_context_k=final_context_k,
    )
    print(f"Questions JSON: {questions_path}")
    print(f"Questions Markdown: {markdown_path}")
    print(f"Raw JSONL: {raw_path}")
    print(f"Report: {report_path}")
    return 0


def build_questions():
    questions = []
    for fact_index, fact in enumerate(FACTS, start=1):
        if len(fact["questions"]) != 4:
            raise ValueError(f"{fact['id']} must define exactly 4 question variants.")
        for variant_index, question in enumerate(fact["questions"], start=1):
            dimensions = DIMENSION_VARIANTS[variant_index - 1]
            questions.append(
                {
                    "id": f"{fact['id']}-V{variant_index}",
                    "fact_id": fact["id"],
                    "book": fact["book"],
                    "question": question,
                    "standard_answer": fact["standard_answer"],
                    "criteria": fact["criteria"],
                    **dimensions,
                }
            )
    if len(questions) != 200:
        raise ValueError(f"Expected 200 questions, got {len(questions)}")
    return questions


def score_retrieved_context(chunks, item: dict) -> dict:
    context_text = normalize_text(
        "\n".join(
            f"{chunk.get('parent_title', '')}\n{chunk.get('title', '')}\n{chunk.get('content', '')}"
            for chunk in chunks
        )
    )
    score = 0
    matched = []
    missed = []
    for criterion in item.get("criteria", []):
        aliases = [normalize_text(alias) for alias in criterion.get("aliases", [])]
        matched_alias = next((alias for alias in aliases if alias and alias in context_text), "")
        if matched_alias:
            weight = int(criterion.get("weight", 1))
            score += weight
            matched.append({"label": criterion.get("label", ""), "weight": weight, "matched_alias": matched_alias})
        else:
            missed.append(criterion.get("label", ""))
    return {"score": min(score, max_score(item)), "max_score": max_score(item), "matched": matched, "missed": missed}


def write_report(
    report_path: Path,
    questions_path: Path,
    markdown_path: Path,
    raw_path: Path,
    records,
    elapsed_seconds: float,
    candidate_k: int,
    rerank_top_k: int,
    final_context_k: int,
) -> None:
    total_score = sum(record["retrieval_upper_bound_score"] for record in records)
    total_max = sum(record["max_score"] for record in records)
    perfect = sum(1 for record in records if record["retrieval_upper_bound_score"] == record["max_score"])
    percent = (total_score / total_max * 100) if total_max else 0.0
    lines = [
        "# 三體三部曲 Mixed200 Retrieval Upper Bound",
        "",
        "本報告只測 Retrieval Upper Bound：檢查 Top 8 Context 是否包含評分規準需要的 evidence，不呼叫 QA Agent。",
        "",
        "## 設定",
        "",
        f"- Questions JSON: `evals/three_body_trilogy/{questions_path.name}`",
        f"- Questions Markdown: `evals/three_body_trilogy/{markdown_path.name}`",
        f"- Raw JSONL: `evals/three_body_trilogy/{raw_path.name}`",
        f"- Candidate K: `{candidate_k}`",
        f"- Rerank Top K: `{rerank_top_k}`",
        f"- Final Context K: `{final_context_k}`",
        "- Pipeline: `BM25(original question) + Qdrant Dense(original question) -> RRF Merge -> Reranker -> Parent Chunk Expansion -> Top 8 Context`",
        f"- Total: **{total_score}/{total_max} = {percent:.1f}%**",
        f"- Perfect Questions: `{perfect}/{len(records)}`",
        f"- Elapsed Seconds: `{elapsed_seconds}`",
        "",
        "## By Book",
        "",
        render_group_table(records, "book"),
        "",
        "## By Answer Style",
        "",
        render_group_table(records, "answer_style"),
        "",
        "## By Prompt Style",
        "",
        render_group_table(records, "prompt_style"),
        "",
        "## By Length Style",
        "",
        render_group_table(records, "length_style"),
        "",
        "## By Phrasing",
        "",
        render_group_table(records, "phrasing"),
        "",
        "## By User Level",
        "",
        render_group_table(records, "user_level"),
        "",
        "## Missed / Partial",
        "",
        "| ID | Book | Dimensions | Score | Standard Answer | Missed | Question | Top Contexts |",
        "| --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    missed_records = [record for record in records if record["retrieval_upper_bound_score"] < record["max_score"]]
    if missed_records:
        for record in missed_records:
            dimensions = ", ".join(
                str(record.get(key, ""))
                for key in ("answer_style", "prompt_style", "length_style", "phrasing", "user_level")
            )
            contexts = "<br>".join(
                f"{index + 1}. {Path(context['source']).name} / {context['title']}"
                for index, context in enumerate(record["contexts"][:8])
            )
            missed = ", ".join(record.get("missed", []))
            lines.append(
                f"| {record['id']} | {record.get('book', '')} | {dimensions} | "
                f"`{record['retrieval_upper_bound_score']}/{record['max_score']}` | "
                f"{record.get('standard_answer', '')} | {missed or '-'} | {record['question']} | {contexts or '-'} |"
            )
    else:
        lines.append("| - | - | - | - | - | - | - | - |")

    lines.extend(["", "## Question Table", "", "| ID | Book | Dimensions | Score | Standard Answer | Question |", "| --- | --- | --- | ---: | --- | --- |"])
    for record in records:
        dimensions = ", ".join(
            str(record.get(key, ""))
            for key in ("answer_style", "prompt_style", "length_style", "phrasing", "user_level")
        )
        lines.append(
            f"| {record['id']} | {record.get('book', '')} | {dimensions} | "
            f"`{record['retrieval_upper_bound_score']}/{record['max_score']}` | {record.get('standard_answer', '')} | {record['question']} |"
        )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_group_table(records, key: str) -> str:
    lines = ["| Group | Count | Retrieval Upper Bound | Perfect Questions |", "| --- | ---: | ---: | ---: |"]
    for value, grouped in _group_records(records, key).items():
        score = sum(record["retrieval_upper_bound_score"] for record in grouped)
        max_total = sum(record["max_score"] for record in grouped)
        percent = (score / max_total * 100) if max_total else 0.0
        perfect = sum(1 for record in grouped if record["retrieval_upper_bound_score"] == record["max_score"])
        lines.append(f"| {value or '-'} | {len(grouped)} | `{score}/{max_total} = {percent:.1f}%` | `{perfect}/{len(grouped)}` |")
    return "\n".join(lines)


def render_questions_markdown(questions) -> str:
    lines = ["# 三體三部曲 Mixed200 Questions", "", "| ID | Book | Dimensions | Standard Answer | Question |", "| --- | --- | --- | --- | --- |"]
    for item in questions:
        dimensions = ", ".join(
            str(item.get(key, ""))
            for key in ("answer_style", "prompt_style", "length_style", "phrasing", "user_level")
        )
        lines.append(f"| {item['id']} | {item['book']} | {dimensions} | {item['standard_answer']} | {item['question']} |")
    return "\n".join(lines) + "\n"


def max_score(item: dict) -> int:
    return sum(int(criterion.get("weight", 1)) for criterion in item.get("criteria", []))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()


def _group_records(records, key: str):
    grouped = {}
    for record in records:
        grouped.setdefault(str(record.get(key, "")), []).append(record)
    return grouped


def _context_record(chunk):
    return {
        "id": chunk.get("id", ""),
        "source": chunk.get("source", ""),
        "parent_title": chunk.get("parent_title", ""),
        "title": chunk.get("title", ""),
        "score": round(float(chunk.get("score", 0.0)), 6),
        "retrieval_method": chunk.get("retrieval_method", ""),
        "rerank_trace": chunk.get("rerank_trace", ""),
        "content_preview": str(chunk.get("content", ""))[:300],
    }


if __name__ == "__main__":
    raise SystemExit(main())
