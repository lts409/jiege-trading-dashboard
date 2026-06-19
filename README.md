# 📊 杰哥交易仪表盘 v3.0

AI产业链全栈监控Web仪表盘。数据源全部免费（腾讯财经API），无需任何API Key。

## 功能

| 模块 | 说明 |
|:----|:------|
| 📈 大盘指数 | 上证/深证/创业板/科创50实时行情 |
| 🧠 双情绪监控 | 全市场880005 + AI产业链专属情绪指数（12板块×39标的） |
| 💼 持仓监控 | 实时盈亏、关键价位预警 |
| 🎯 候选池 | 赛道跟踪、买入区间、优先级筛选 |
| 📊 板块行情 | 持仓所属板块涨跌推导 |

## 截图

（页面打开即显示数据）

## 快速启动

```bash
# 1. 下载
git clone https://github.com/lts409/jiege-trading-dashboard.git
cd jiege-trading-dashboard

# 2. 安装依赖
pip3 install flask requests

# 3. 编辑配置
vim config.json    # 修改持仓、指数、板块

# 4. 启动
python3 app.py

# 5. 浏览器打开
open http://127.0.0.1:8899
```

## 配置

### config.json

```json
{
  "positions": [
    {"name": "股票名称", "code": "002585", "shares": 10000, "cost": 10.0, "avg_volume": 50000000}
  ],
  "indices": [
    {"name": "上证指数", "code": "000001"}
  ],
  "sectors": [
    {"name": "MLCC板块", "code": "BK0890"}
  ],
  "key_levels": {
    "股票名称": {
      "support": [9.0, 8.5],
      "resistance": [11.0, 12.5]
    }
  }
}
```

### candidates.json（可选）

创建 `candidates.json` 配置候选池：

```json
{
  "赛道列表": [
    {
      "赛道": "赛道名称",
      "阶段": "萌芽期 ⭐⭐",
      "候选标的": [
        {"name": "标的名称", "code": "000001", "entry_zone": "¥10-12", "priority": "⭐⭐⭐"}
      ]
    }
  ]
}
```

### AI Sentiment Index（无需配置）

内置12大板块×39只AI核心标的，启动即用：
- 🔬 AI芯片、💾 存储芯片、🔗 光通信/CPO
- 💻 AI服务器、🔋 AI电源/液冷、📦 MLCC/被动
- 🖥️ 半导体设备、🔌 AI PCB、🤖 灵巧手
- 🧠 AI应用、🚗 智能驾驶、🧩 PCIE/互联

## 情绪阈值

| AI Sentiment | 含义 | 操作 |
|:-------------|:-----|:-----|
| ≥80% | 🔥 AI科技牛 | 全线普涨，持股不动 |
| 60-80% | 🟢 科技偏强 | 结构良好，可加仓 |
| 40-60% | 🟡 分化 | 调仓到强势板块 |
| 20-40% | 🔴 AI调整 | 减仓防御 |
| <20% | ⚫ AI冰点 | 轻仓或空仓 |

## 技术栈

- Flask (Python)
- 腾讯财经API（免费、无Key、不封IP）
- Vanilla JS（无前端框架依赖）

## 项目结构

```
dashboard/
├── app.py              # Flask后端
├── config.json         # 配置（持仓/指数/板块/关键价位）
├── candidates.json     # 候选池（可选）
├── requirements.txt    # Python依赖
├── start.sh            # 启动脚本
├── templates/
│   └── index.html      # Web前端
└── README.md
```
