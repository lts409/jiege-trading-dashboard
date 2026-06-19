#!/usr/bin/env python3
"""
杰哥交易仪表盘 v3.0 — AI产业链全栈监控
数据源: 腾讯财经API (统一数据源) + AI Sentiment Index + 候选池
"""

import json, os, sqlite3, requests, subprocess
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify

# ── 加载配置 ──
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r") as f:
    CONFIG = json.load(f)

POSITIONS = CONFIG["positions"]
KEY_LEVELS = CONFIG["key_levels"]
STAGES = CONFIG["stages"]

# ── 腾讯财经行情API ──
def tencent_quote(codes: list[str]) -> dict[str, dict]:
    """批量拉取腾讯财经实时行情（A-Stock Data标准接口）"""
    prefixed = []
    for c in codes:
        if c.startswith(("6", "9", "5")):
            prefixed.append(f"sh{c}")
        elif c.startswith("8"):
            prefixed.append(f"bj{c}")
        else:
            prefixed.append(f"sz{c}")
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = "gbk"
        result = {}
        for line in r.text.strip().split(";"):
            if not line.strip() or "=" not in line or '"' not in line:
                continue
            key = line.split("=")[0].split("_")[-1]
            vals = line.split('"')[1].split("~")
            if len(vals) < 53:
                continue
            code = key[2:]
            result[code] = {
                "name": vals[1],
                "price": float(vals[3]) if vals[3] else 0,
                "last_close": float(vals[4]) if vals[4] else 0,
                "open": float(vals[5]) if vals[5] else 0,
                "change_amt": float(vals[31]) if vals[31] else 0,
                "change_pct": float(vals[32]) if vals[32] else 0,
                "high": float(vals[33]) if vals[33] else 0,
                "low": float(vals[34]) if vals[34] else 0,
                "volume": float(vals[6]) if vals[6] else 0,
                "amount_wan": float(vals[37]) if vals[37] else 0,
                "turnover_pct": float(vals[38]) if vals[38] else 0,
                "pe_ttm": float(vals[39]) if vals[39] else 0,
                "mcap_yi": float(vals[44]) if vals[44] else 0,
                "float_mcap_yi": float(vals[45]) if vals[45] else 0,
                "pb": float(vals[46]) if vals[46] else 0,
                "vol_ratio": float(vals[49]) if vals[49] else 0,
                "amplitude_pct": float(vals[43]) if vals[43] else 0,
            }
        return result
    except Exception as e:
        return {"_error": str(e)}

# ── AI产业链情绪指数 ──
AI_ECOSYSTEM = {
    "🔬 AI芯片": ["sh688041", "sh688256", "sz300474"],
    "💾 存储芯片": ["sh603986", "sh688110", "sh688525"],
    "🔗 光通信/CPO": ["sz300308", "sz002281", "sh688048", "sz300502", "sz300394"],
    "💻 AI服务器": ["sh603019", "sz000977", "sz000938"],
    "🔋 AI电源/液冷": ["sz002851", "sz002364", "sz002837", "sz300499"],
    "📦 MLCC/被动": ["sz002585", "sz300408", "sz000636", "sz300285"],
    "🖥️ 半导体设备": ["sh688012", "sh688120", "sz002371"],
    "🔌 AI PCB": ["sz002916", "sh603228", "sz300476"],
    "🤖 灵巧手": ["sz002896", "sh603728", "sz300124"],
    "🧠 AI应用": ["sz002230", "sh688111", "sz300624"],
    "🚗 智能驾驶": ["sz002920", "sz300496"],
    "🧩 PCIE/互联": ["sh600246", "sz300308", "sh688017"],
}

def calc_ai_sentiment() -> dict:
    """计算AI产业链情绪指数"""
    all_codes = list(set(sum(AI_ECOSYSTEM.values(), [])))
    quotes = tencent_quote(all_codes)
    if "_error" in quotes:
        return {"error": quotes["_error"]}
    
    sectors = {}
    total_up = 0
    total_count = 0
    for sector_name, codes in AI_ECOSYSTEM.items():
        up = 0
        details = []
        for code in codes:
            q = quotes.get(code, {})
            if q:
                change_pct = q.get("change_pct", 0)
                up += 1 if change_pct > 0 else 0
                details.append({
                    "code": code,
                    "name": q.get("name", ""),
                    "price": q.get("price", 0),
                    "change_pct": change_pct
                })
        sectors[sector_name] = {
            "up": up,
            "total": len(codes),
            "ratio": round(up / len(codes) * 100, 1) if codes else 0,
            "details": details
        }
        total_up += up
        total_count += len(codes)
    
    overall_ratio = round(total_up / total_count * 100, 1) if total_count else 0
    
    # 情绪阈值判断
    if overall_ratio >= 80:
        label, advice, color = "🔥 AI科技牛", "全线普涨，持股不动", "#ffd700"
    elif overall_ratio >= 60:
        label, advice, color = "🟢 科技偏强", "结构良好，可加仓强势板块", "#00ff88"
    elif overall_ratio >= 40:
        label, advice, color = "🟡 分化", "调仓到强势板块", "#ffa500"
    elif overall_ratio >= 20:
        label, advice, color = "🔴 AI調整", "减仓防御", "#e94560"
    else:
        label, advice, color = "⚫ AI冰点", "轻仓或空仓", "#888888"
    
    return {
        "time": datetime.now().strftime("%m/%d %H:%M"),
        "up": total_up,
        "total": total_count,
        "ratio": overall_ratio,
        "label": label,
        "advice": advice,
        "color": color,
        "sectors": sectors
    }

# ── 候选池 ──
CANDIDATE_PATH = os.path.join(os.path.dirname(__file__), "..", "用户", "选股", "候选池.json")
def load_candidates() -> dict:
    """加载候选池"""
    try:
        with open(CANDIDATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"错误": str(e)}

# ── Flask应用 ──
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# ── 路由 ──
@app.route("/")
def index():
    return render_template("index.html", now=datetime.now().strftime("%m/%d %H:%M"))

@app.route("/api/config")
def api_config():
    return jsonify(CONFIG)

@app.route("/api/positions")
def api_positions():
    """获取持仓实时行情"""
    codes = [p["code"] for p in POSITIONS]
    quotes = tencent_quote(codes)
    result = []
    for p in POSITIONS:
        q = quotes.get(p["code"], {})
        gain_pct = round((q.get("price", 0) - p["cost"]) / p["cost"] * 100, 2) if p["cost"] and q.get("price") else 0
        gain_amt = round((q.get("price", 0) - p["cost"]) * p["shares"], 2)
        result.append({
            "name": p["name"],
            "code": p["code"],
            "shares": p["shares"],
            "cost": p["cost"],
            "price": q.get("price", 0),
            "change_pct": q.get("change_pct", 0),
            "gain_pct": gain_pct,
            "gain_amt": gain_amt,
            "mcap": q.get("mcap_yi", 0),
            "turnover": q.get("turnover_pct", 0),
            "vol_ratio": q.get("vol_ratio", 0),
            "pe": q.get("pe_ttm", 0),
            "pb": q.get("pb", 0),
            "high": q.get("high", 0),
            "low": q.get("low", 0),
            "amount_wan": q.get("amount_wan", 0),
        })
    return jsonify(result)

@app.route("/api/indices")
def api_indices():
    """获取大盘指数（使用正确的前缀）"""
    # 指数代码前缀规则 vs 股票不同
    INDEX_PREFIX = {
        "000001": "sh",  # 上证指数
        "000688": "sh",  # 科创50
        "399001": "sz",  # 深证成指
        "399006": "sz",  # 创业板指
    }
    prefixed = [f"{INDEX_PREFIX.get(idx['code'], 'sh')}{idx['code']}" for idx in CONFIG["indices"]]
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = "gbk"
        result = []
        for line in r.text.strip().split(";"):
            if not line.strip() or "=" not in line or '"' not in line:
                continue
            vals = line.split('"')[1].split("~")
            if len(vals) < 35:
                continue
            code = vals[2]
            result.append({
                "name": vals[1],
                "code": code,
                "price": float(vals[3]) if vals[3] else 0,
                "change_pct": float(vals[32]) if vals[32] else 0,
                "high": float(vals[33]) if vals[33] else 0,
                "low": float(vals[34]) if vals[34] else 0,
                "amount_wan": float(vals[37]) if vals[37] else 0,
            })
        # 按配置顺序排序
        code_order = [idx["code"] for idx in CONFIG["indices"]]
        result.sort(key=lambda x: code_order.index(x["code"]) if x["code"] in code_order else 99)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/sectors")
def api_sectors():
    """获取板块行情（从持仓数据推导）"""
    try:
        codes = [p["code"] for p in POSITIONS]
        quotes = tencent_quote(codes)
        sector_groups = {
            "MLCC": ["双星新材", "风华高科", "三环集团"],
            "光通信": ["光迅科技"],
            "半导体": [],
            "AI芯片": [],
            "PCB": [],
        }
        result = []
        pos_data = {p["name"]: p for p in POSITIONS}
        for sec_name, stocks in sector_groups.items():
            changes = []
            for s in stocks:
                p = pos_data.get(s)
                if p:
                    q = quotes.get(p["code"], {})
                    if q.get("price", 0) > 0:
                        changes.append(q["change_pct"])
            avg = round(sum(changes)/len(changes), 2) if changes else 0
            result.append({"name": sec_name, "change_pct": avg, "count": len(changes)})
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/ai-sentiment")
def api_ai_sentiment():
    """AI产业链情绪指数"""
    return jsonify(calc_ai_sentiment())

@app.route("/api/candidates")
def api_candidates():
    """获取候选池列表"""
    return jsonify(load_candidates())

@app.route("/api/key-levels")
def api_key_levels():
    """关键价位监控"""
    return jsonify(KEY_LEVELS)

@app.route("/api/sentiment")
def api_sentiment():
    """880005全市场情绪(通过fetch_stock_price.py获取)"""
    try:
        sp = os.path.join(os.path.dirname(__file__), "..", "scripts", "fetch_stock_price.py")
        r = subprocess.run(["python3", sp, "000001"], capture_output=True, text=True, timeout=15)
        return jsonify({"up": 1800, "label": "🌥️ 平衡", "note": "880005暂用模拟值"})
    except:
        return jsonify({"up": "--", "label": "待刷新", "error": "数据源暂不可用"})

@app.route("/api/stages")
def api_stages():
    return jsonify(STAGES)

# ── 启动 ──
if __name__ == "__main__":
    host = CONFIG.get("server", {}).get("host", "0.0.0.0")
    port = CONFIG.get("server", {}).get("port", 8899)
    print(f"📊 杰哥交易仪表盘 v3.0")
    print(f"   访问: http://127.0.0.1:{port}")
    app.run(host=host, port=port, debug=False)
