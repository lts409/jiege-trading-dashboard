# 📊 杰哥交易仪表盘 v3.0

AI产业链全栈监控Web仪表盘。

## 功能

- 📈 **大盘指数**：上证/深证/创业板/科创50实时行情
- 🧠 **双情绪监控**：全市场880005 + AI产业链专属情绪指数
- 💼 **持仓监控**：实时盈亏、关键价位预警
- 🎯 **候选池**：10赛道30+标的筛选展示
- 📊 **板块行情**：MLCC/半导体/光通信/AI芯片等

## 数据源

- **腾讯财经API**（统一数据源，免费不封IP）
- **AI Sentiment Index**（12大板块39只AI核心标的）
- **候选池**（来自 `用户/选股/候选池.json`）

## 快速启动

```bash
cd dashboard
pip3 install flask requests
python3 app.py
# 访问 http://127.0.0.1:8899
```

## 配置

编辑 `config.json` 更新持仓/监控标的。

## 更新

```bash
git pull
python3 app.py
```
