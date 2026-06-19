#!/usr/bin/env python3
"""
每日20:05复盘反思生成器 — 基于杰哥策略体系的3问
输出: 用户/反思/YYYY-MM-DD_每日复盘.md
"""
import json, os, requests
from datetime import datetime

REFLECT_DIR = os.path.join(os.path.dirname(__file__), "..", "用户", "反思")
POS_FILE = os.path.join(os.path.dirname(__file__), "..", "用户", "持仓", "持仓清单.json")

def get_positions() -> tuple:
    """获取持仓数据和实时行情"""
    if not os.path.exists(POS_FILE):
        return [], 0
    with open(POS_FILE, "r") as f:
        raw = json.load(f)
    
    holdings = {}
    if "信用账户" in raw and "持仓" in raw["信用账户"]:
        holdings = raw["信用账户"]["持仓"]
    
    codes = [v["code"] for v in holdings.values() if "code" in v]
    if not codes:
        return [], 0
    
    prefixed = ["sh" + c if c.startswith(("6", "9")) else "sz" + c for c in codes]
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    r.encoding = "gbk"
    
    prices = {}
    for line in r.text.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        vals = line.split('"')[1].split("~")
        if len(vals) < 35:
            continue
        code = vals[2]
        prices[code] = {
            "price": float(vals[3]) if vals[3] else 0,
            "change_pct": float(vals[32]) if vals[32] else 0,
            "name": vals[1],
        }
    
    rows = []
    total_gain = 0
    for name, pos in holdings.items():
        code = pos.get("code", "")
        p = prices.get(code, {})
        price = p.get("price", 0) or pos.get("price", 0)
        cost = pos.get("cost", 0)
        shares = pos.get("shares", 0)
        gain_pct = round((price - cost) / cost * 100, 2) if cost and price else 0
        gain_amt = round((price - cost) * shares, 2)
        total_gain += gain_amt
        change = round(p.get("change_pct", 0), 2)
        rows.append({
            "name": p.get("name", name),
            "code": code,
            "shares": shares,
            "cost": cost,
            "price": price,
            "change": change,
            "gain_pct": gain_pct,
            "gain_amt": gain_amt,
        })
    
    return rows, total_gain

def get_ai_sentiment() -> dict:
    try:
        r = requests.get("http://127.0.0.1:8899/api/ai-sentiment", timeout=10)
        return r.json()
    except:
        return {"ratio": 0, "label": "获取失败"}

def fmt_pct(val):
    if val > 0:
        return "+{:.2f}%".format(val)
    return "{:.2f}%".format(val)

def generate_questions(positions, total_gain, sentiment):
    """基于杰哥策略体系+今日数据，动态生成3个问题"""
    questions = []
    
    # === 问题一：仓位管理 ===
    if positions:
        heavy = [p for p in positions if abs(p["gain_amt"]) > abs(total_gain) * 0.3]
        weak = [p for p in positions if abs(p["gain_pct"]) < 3 and abs(p["gain_amt"]) > 10000]
        
        if heavy:
            names = "、".join([p["name"] for p in heavy])
            q = (
                "**仓位管理：{}贡献了主要盈亏，是否符合杰哥\"高确定性才上仓位\"的原则？**\n\n"
                "当前持仓{}只，总盈亏¥{:+,.0f}。"
                "按杰哥体系：主升行情推仓位、分歧时重仓、确定性不够的标的只做博弈仓。"
                "你现在的仓位分配是否体现了对每个标的确定性的真实判断？"
            ).format(names, len(positions), total_gain)
            questions.append(q)
        elif weak:
            names = "、".join([p["name"] for p in weak])
            q = (
                "**仓位管理：{}仓位较重但收益不明显，是否占用了主线的仓位？**\n\n"
                "杰哥说过\"浪费仓位比亏钱更不划算\"——仓位是稀缺资源，"
                "配置在低确定性/低效率的标的上，意味着错过了高确定性的加仓机会。"
                "这些仓位是否有更好的去处？"
            ).format(names)
            questions.append(q)
        else:
            top = max(positions, key=lambda x: abs(x["gain_amt"]))
            q = (
                "**仓位管理：{}目前是最大盈亏来源，仓位是否匹配确定性？**\n\n"
                "杰哥框架：确定性5星->重仓推，1星->博弈仓/观察仓。"
                "检查每个持仓的确定性评级与仓位占比是否匹配——"
                "有没有\"低确定性高仓位\"或\"高确定性低仓位\"的结构错配？"
            ).format(top["name"])
            questions.append(q)
    else:
        questions.append("**仓位管理：当前无持仓，空仓是否基于确定性判断还是观望情绪？**")
    
    # === 问题二：情绪周期+风险控制 ===
    sent_ratio = sentiment.get("ratio", 0)
    sent_label = sentiment.get("label", "?")
    chase_holds = [p for p in positions if p["change"] > 7] if positions else []
    gain_loss = [p for p in positions if p["gain_pct"] < 0] if positions else []
    
    if sent_ratio >= 80:
        if gain_loss:
            names = "、".join([p["name"] for p in gain_loss])
            q = (
                "**情绪+风控：AI情绪{}%{}全线强势，但{}逆势下跌/不涨，是否触发了风控信号？**\n\n"
                "杰哥风控核心：\"控制回撤是第一位\"。在大盘和板块都强势的环境下持仓不涨甚至下跌，"
                "往往意味着该标的基本面或资金面出了问题。是继续持有等轮动，还是果断砍仓换到主线？"
            ).format(sent_ratio, sent_label, names)
            questions.append(q)
        elif chase_holds:
            chg_strs = ["+" + str(p["change"]) + "%" for p in chase_holds]
            names = "、".join([p["name"] for p in chase_holds])
            q = (
                "**情绪+风控：{}今日大涨{}，AI情绪{}%{}——是否考虑移动止盈？**\n\n"
                "杰哥原则：\"接近5日线降仓位\"。大涨不卖是散户通病，"
                "在情绪极端亢奋时（AI情绪>80%），反而是逐步锁定利润的时机。"
                "你有计划在哪个位置减仓吗？"
            ).format(names, "/".join(chg_strs), sent_ratio, sent_label)
            questions.append(q)
        else:
            q = (
                "**情绪周期：AI情绪{}%{}，全市场亢奋，你在做什么？**\n\n"
                "杰哥体系：情绪周期分为\"冰点->回暖->主升->高潮->退潮\"。"
                "当前属于高潮阶段，按杰哥的经验，高潮期应该逐步收手而不是加码。"
                "你有没有为退潮期做好准备？"
            ).format(sent_ratio, sent_label)
            questions.append(q)
    elif sent_ratio < 40:
        tag = "🔴" if sent_ratio < 20 else "🟡"
        q = (
            "**情绪周期：AI情绪{}%{}，市场偏冷，是否到了杰哥说的\"分歧重仓\"时机？**\n\n"
            "杰哥框架：\"第一次分歧的时候就重仓进去\"——市场分歧/冰点才是布局时机。"
            "你现在是在趁机加仓，还是在恐慌中减仓？是否区分了\"板块退潮\"和\"正常分歧\"？"
        ).format(sent_ratio, tag)
        questions.append(q)
    else:
        q = (
            "**情绪周期：AI情绪{}%🟡，市场结构分化，你的持仓是否在正确的方向上？**\n\n"
            "杰哥体系强调\"主升行情推仓位，平时叫博弈\"。在分化市场中，"
            "你的持仓是顺着主线（AI产业链/MLCC/PCIE）还是逆着主线？"
            "分化期最怕持仓方向和市场主力资金流向不一致。"
        ).format(sent_ratio)
        questions.append(q)
    
    # === 问题三：纪律执行 ===
    has_error = False
    error_note = ""
    for p in positions:
        if "万通" in p["name"] and p["cost"] > 17.5:
            has_error = True
            cost_str = "{:.3f}".format(p["cost"])
            error_note = "  追高记录：万通发展成本" + cost_str + "，高于当日开盘价。"
    
    q3 = "**纪律执行：今天有没有违背自己交易体系的行为？**\n\n"
    if has_error:
        q3 += "杰哥箴言：\"千万不要高估自己\"。" + error_note + "\n\n"
        q3 += "追高=情绪驱动，不等于计划交易。杰哥的做法是：\"舒服的位置推仓位，不追高\"。\n"
        q3 += "**今天有没有其他计划外操作？触发原因是什么（FOMO/焦虑/别人推荐）？**"
    else:
        q3 += "杰哥体系的核心不是预测市场，而是**执行纪律**。\n"
        q3 += "今天有没有严格遵守：①确定性不够不上仓位 ②不追高 ③止损不犹豫 ④计划内交易？\n"
        q3 += "**哪一条执行得最好？哪一条下次需要改进？**"
    
    questions.append(q3)
    return questions

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    positions, total_gain = get_positions()
    sentiment = get_ai_sentiment()
    questions = generate_questions(positions, total_gain, sentiment)
    
    # 持仓表格
    pos_table = ""
    if positions:
        pos_table = "| 标的 | 持仓 | 成本 | 现价 | 今日涨跌 | 累计收益% | 收益额 |\n"
        pos_table += "|:---|:---:|:---:|:---:|:---:|:---:|:---:|\n"
        for p in positions:
            chg = fmt_pct(p["change"])
            gp = fmt_pct(p["gain_pct"])
            ga = "¥{:+,.0f}".format(p["gain_amt"])
            cost = "¥{:.3f}".format(p["cost"])
            price = "¥{:.2f}".format(p["price"])
            shares = "{}股".format(p["shares"])
            row = "| {} | {} | {} | {} | {} | {} | {} |\n".format(
                p["name"], shares, cost, price, chg, gp, ga)
            pos_table += row
        pos_table += "\n**总浮动盈亏：¥{:+,.0f}**\n".format(total_gain)
    else:
        pos_table = "（无持仓数据）\n"
    
    # AI情绪文本
    sent_text = "AI情绪: {}% {}".format(sentiment.get("ratio", "?"), sentiment.get("label", "?"))
    if "sectors" in sentiment:
        strong = [n for n, s in sentiment["sectors"].items() if s["ratio"] >= 80]
        weak = [n for n, s in sentiment["sectors"].items() if s["ratio"] <= 50]
        if strong:
            sent_text += "\n  强势: " + " ".join(strong[:5])
        if weak:
            sent_text += "\n  弱势: " + " ".join(weak[:3])
    
    # 格式化的三问
    q_sections = []
    labels = ["仓位管理", "情绪周期+风控", "纪律执行"]
    for i, q in enumerate(questions):
        label = labels[i] if i < len(labels) else "策略"
        sect = "\n### {}问（{}）\n\n{}\n\n\n---\n\n".format(
            ["第一", "第二", "第三"][i] if i < 3 else "第" + str(i+1),
            label, q)
        q_sections.append(sect)
    
    content = "# {} 每日交易复盘\n\n".format(today)
    content += "> 生成时间: {}\n\n".format(datetime.now().strftime("%Y-%m-%d %H:%M"))
    content += "---\n\n"
    content += "## 📊 持仓快照\n\n{}\n\n".format(pos_table)
    content += "## 🧠 AI产业链情绪\n\n{}\n\n".format(sent_text)
    content += "---\n\n"
    content += "## 🎯 今日三问（基于杰哥策略体系）\n\n"
    content += "".join(q_sections)
    content += "## 📌 明日重点\n\n1. \n2. \n3. \n\n---\n\n## 💡 今日经验沉淀\n\n"
    
    os.makedirs(REFLECT_DIR, exist_ok=True)
    path = os.path.join(REFLECT_DIR, "{}_每日复盘.md".format(today))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("反思已写入: " + path)
    print("持仓{}只 | 总盈亏¥{:+,.0f} | AI情绪{}%".format(
        len(positions), total_gain, sentiment.get("ratio", "?")))
    print("今日三问已生成，请在 用户/反思/{}_每日复盘.md 作答".format(today))

if __name__ == "__main__":
    main()
