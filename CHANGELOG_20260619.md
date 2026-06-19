# 2026-06-19 会话记忆

## ⚠️ 关键决策

### Twitter CLI认证+首条推文发布 (15:19-15:52)
- **认证方式**: 从Chrome Cookie数据库提取`auth_token`(40字符)+`ct0`(160字符)，使用`browser-cookie3`库。账号`@lts409(拉菲特)`。
- **永久配置**: Cookie写入`~/.agent-reach-venv/bin/activate`和`~/.zshrc`。⚠️一次性，登出后需重新导出。
- **支持命令**: `twitter post/reply/feed/user/user-posts/search/article`全部可用。
- **发推命令**: `source ~/.agent-reach-venv/bin/activate && twitter post "内容"`
- **发推能力**: X免费用户可发5000字符，无140限制。
- **推文4条**: AI Sentiment Index(15:39→15:52重写), 钽电容带图(16:05), PCIE交换芯片带图(16:17)

### GitHub永久认证 (15:46-15:52)
- **Token**: `ghp_vi...Dp4f`已写入`~/.zshrc`和venv
- **SSH Key**: 双重认证
- **仓库**: `lts409/ai-sentiment-index`(公开) + `lts409/jiege-trading-dashboard`(公开)

### Twitter AI产业链监控账号 (15:32-15:35)
- **10个监控账号**: cron `24710ece` 每日08:00推送
- **核心5个**: @yiqifacai, @aleabitoreddit, @chnki089, @cnfinancewatch, @SemiAnalysis_
- **行业5个**: @freearkshaw, @momotea19, @qinbafrank, @jiayuan_jy, @dwarkesh_sp

### Dashboard v3.0数据源：A-Stock Data (16:50-17:00)
- **用户要求**: 使用A-Stock Data数据源，不要直接用腾讯API
- **架构**: mootdx TCP（主价格）+ 腾讯API（补充字段）双源合并
- **修复bug**: AI_ECOSYSTEM前缀双重编码（sh688041→shsh688041）→ AI Sentiment从0%→92.3%
- **通用版**: `candidates.json`回退 + README重写 + 无需Key启动

## 📝 后续待办
1. **Twitter发推自动化cron**: 每天08:00自动发AI Sentiment当日读数
2. **后续推文**: 800V HVDC → PCIE赛道 → 钽电容 → MLCC第一性原理
3. **Dashboard验证**: 6/22(周一)开盘验证mootdx稳定性
4. **Agent Reach补完**: 小红书/雪球Cookie
