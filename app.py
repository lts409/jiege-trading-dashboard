#!/usr/bin/env python3
"""
杰哥交易仪表盘 v3.0 — AI产业链全栈监控
数据源: A-Stock Data (mootdx TCP + 腾讯财经API双源)
"""

import json, os, requests, subprocess
from datetime import datetime
from flask import Flask, render_template, jsonify

try:
    from mootdx.quotes import Quotes
    _MOOTDX = Quotes.factory(market='std')
    _MOOTDX_OK = True
except:
    _MOOTDX_OK = False

# ── 加载配置 ──
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r") as f:
    CONFIG = json.load(f)
POSITIONS = CONFIG["positions"]
KEY_LEVELS = CONFIG["key_levels"]
STAGES = CONFIG["stages"]

# ════════════════════════════════════════════════════════
# A-Stock Data 数据源（mootdx TCP 主 + 腾讯API补充）
# ════════════════════════════════════════════════════════

def get_prefix(code: str) -> str:
    """A-Stock Data 标准前缀规则"""
    if code.startswith(("6", "9")):
        return "sh"
    elif code.startswith("8"):
        return "bj"
    else:
        return "sz"

def mootdx_quote(codes: list[str]) -> dict[str, dict]:
    """mootdx TCP实时行情（主数据源）"""
    if not _MOOTDX_OK:
        return {}
    try:
        q = _MOOTDX.quotes(symbol=codes)
        if q is None or q.empty:
            return {}
        result = {}
        for _, row in q.iterrows():
            code = str(row["code"]).zfill(6)
            price = float(row["price"])
            last_close = float(row["last_close"])
            change_pct = round((price - last_close) / last_close * 100, 2) if last_close else 0
            result[code] = {
                "name": "",  # mootdx不返回名称，由腾讯API补充
                "price": price,
                "last_close": last_close,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "volume": float(row["vol"]),
                "amount": float(row["amount"]),
                "change_pct": change_pct,
            }
        return result
    except Exception:
        return {}

def tencent_quote(codes: list[str]) -> dict[str, dict]:
    """腾讯财经API补充字段（PE/PB/市值/换手率/量比/名称）"""
    if not codes:
        return {}
    # A-Stock Data标准前缀规则
    prefixed = [f"{get_prefix(c)}{c}" for c in codes]
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
            code = key[2:]  # 去掉sh/sz前缀
            result[code] = {
                "name":         vals[1],
                "price":        float(vals[3]) if vals[3] else 0,
                "last_close":   float(vals[4]) if vals[4] else 0,
                "open":         float(vals[5]) if vals[5] else 0,
                "change_amt":   float(vals[31]) if vals[31] else 0,
                "change_pct":   float(vals[32]) if vals[32] else 0,
                "high":         float(vals[33]) if vals[33] else 0,
                "low":          float(vals[34]) if vals[34] else 0,
                "volume":       float(vals[6]) if vals[6] else 0,
                "amount_wan":   float(vals[37]) if vals[37] else 0,
                "turnover_pct": float(vals[38]) if vals[38] else 0,
                "pe_ttm":       float(vals[39]) if vals[39] else 0,
                "amplitude_pct":float(vals[43]) if vals[43] else 0,
                "mcap_yi":      float(vals[44]) if vals[44] else 0,
                "float_mcap_yi":float(vals[45]) if vals[45] else 0,
                "pb":           float(vals[46]) if vals[46] else 0,
                "limit_up":     float(vals[47]) if vals[47] else 0,
                "limit_down":   float(vals[48]) if vals[48] else 0,
                "vol_ratio":    float(vals[49]) if vals[49] else 0,
                "pe_static":    float(vals[52]) if vals[52] else 0,
            }
        return result
    except Exception as e:
        return {"_error": str(e)}

def get_quotes(codes: list[str]) -> dict[str, dict]:
    """双源合并：mootdx价格+腾讯API补充字段"""
    codes = [c.strip() for c in codes if c.strip()]
    if not codes:
        return {}

    # 主：mootdx TCP（价格/涨跌幅）
    mq = mootdx_quote(codes)

    # 补充：腾讯API（名称/PE/PB/市值/换手率）
    tq = tencent_quote(codes)

    # 合并
    result = {}
    for c in codes:
        result[c] = {**mq.get(c, {}), **tq.get(c, {})}
    return result

# ════════════════════════════════════════════════════════
# AI Sentiment Index
# ════════════════════════════════════════════════════════

AI_ECOSYSTEM = {
    "🔬 AI芯片":     ["sh688041", "sh688256", "sz300474"],
    "💾 存储芯片":   ["sh603986", "sh688110", "sh688525"],
    "🔗 光通信/CPO": ["sz300308", "sz002281", "sh688048", "sz300502", "sz300394"],
    "💻 AI服务器":   ["sh603019", "sz000977", "sz000938"],
    "🔋 AI电源/液冷":["sz002851", "sz002364", "sz002837", "sz300499"],
    "📦 MLCC/被动":  ["sz002585", "sz300408", "sz000636", "sz300285"],
    "🖥️ 半导体设备": ["sh688012", "sh688120", "sz002371"],
    "🔌 AI PCB":     ["sz002916", "sh603228", "sz300476"],
    "🤖 灵巧手":     ["sz002896", "sh603728", "sz300124"],
    "🧠 AI应用":     ["sz002230", "sh688111", "sz300624"],
    "🚗 智能驾驶":   ["sz002920", "sz300496"],
    "🧩 PCIE/互联":  ["sh600246", "sz300308", "sh688017"],
}

def calc_ai_sentiment() -> dict:
    """A-Stock Data驱动AI产业链情绪指数"""
    # 先去前缀取裸代码
    all_bare = list(set(c[2:] for c in sum(AI_ECOSYSTEM.values(), [])))
    quotes = get_quotes(all_bare)
    if "_error" in quotes:
        return {"error": quotes["_error"]}

    sectors = {}
    total_up = 0
    total_count = 0
    for sector_name, codes in AI_ECOSYSTEM.items():
        up = 0
        details = []
        for code in codes:
            bare_code = code[2:]
            q = quotes.get(bare_code, {})
            if q and q.get("price", 0) > 0:
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
    if overall_ratio >= 80:
        label, advice, color = "🔥 AI科技牛", "全线普涨，持股不动", "#ffd700"
    elif overall_ratio >= 60:
        label, advice, color = "🟢 科技偏强", "结构良好，可加仓强势板块", "#00ff88"
    elif overall_ratio >= 40:
        label, advice, color = "🟡 分化", "调仓到强势板块", "#ffa500"
    elif overall_ratio >= 20:
        label, advice, color = "🔴 AI调整", "减仓防御", "#e94560"
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
CANDIDATE_PATH = os.path.join(os.path.dirname(__file__), "candidates.json")
EXTERNAL_CANDIDATE_PATH = os.path.join(os.path.dirname(__file__), "..", "用户", "选股", "候选池.json")
def load_candidates() -> dict:
    for path in [EXTERNAL_CANDIDATE_PATH, CANDIDATE_PATH]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            continue
    return {"赛道列表": [], "说明": "请创建 candidates.json 配置候选池"}

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
    codes = [p["code"] for p in POSITIONS]
    quotes = get_quotes(codes)
    result = []
    for p in POSITIONS:
        q = quotes.get(p["code"], {})
        price = q.get("price", 0) or 0
        cost = p["cost"]
        gain_pct = round((price - cost) / cost * 100, 2) if cost and price else 0
        gain_amt = round((price - cost) * p["shares"], 2)
        result.append({
            "name": q.get("name", p["name"]),
            "code": p["code"],
            "shares": p["shares"],
            "cost": cost,
            "price": price,
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
    """大盘指数（A-Stock Data 腾讯API标准接口）"""
    try:
        prefix_map = {"000001": "sh", "000688": "sh", "399001": "sz", "399006": "sz"}
        prefixed = [f"{prefix_map.get(idx['code'], 'sh')}{idx['code']}" for idx in CONFIG["indices"]]
        url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
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
            })
        code_order = [idx["code"] for idx in CONFIG["indices"]]
        result.sort(key=lambda x: code_order.index(x["code"]) if x["code"] in code_order else 99)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/sectors")
def api_sectors():
    """板块行情（从持仓推导）"""
    try:
        codes = [p["code"] for p in POSITIONS]
        quotes = get_quotes(codes)
        sector_groups = {
            "MLCC":    ["双星新材", "风华高科", "三环集团"],
            "光通信":  ["光迅科技"],
            "半导体":  [],
            "AI芯片":  [],
            "PCB":     [],
        }
        result = []
        pos_map = {p["name"]: p for p in POSITIONS}
        for sec_name, stocks in sector_groups.items():
            changes = []
            for s in stocks:
                p = pos_map.get(s)
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
    return jsonify(calc_ai_sentiment())

@app.route("/api/candidates")
def api_candidates():
    return jsonify(load_candidates())

@app.route("/api/key-levels")
def api_key_levels():
    return jsonify(KEY_LEVELS)

@app.route("/api/sentiment")
def api_sentiment():
    return jsonify({"up": 1800, "label": "🌥️ 平衡", "note": "880005暂用模拟值"})

@app.route("/api/stages")
def api_stages():
    return jsonify(STAGES)

if __name__ == "__main__":
    host = CONFIG.get("server", {}).get("host", "0.0.0.0")
    port = CONFIG.get("server", {}).get("port", 8899)
    ds = "mootdx TCP + 腾讯API"
    if not _MOOTDX_OK:
        ds = "腾讯API(回退)"
    print(f"📊 杰哥交易仪表盘 v3.0")
    print(f"   数据源: {ds}")
    print(f"   访问: http://127.0.0.1:{port}")
    app.run(host=host, port=port, debug=False)
