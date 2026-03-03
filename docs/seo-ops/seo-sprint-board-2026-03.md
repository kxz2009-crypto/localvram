# SEO 30天冲刺看板（2026-03-04 ~ 2026-04-02）

## 1) 冲刺目标（KPI）

- 搜索点击：84 -> 180+
- 平均 CTR：约 4% -> 5.5%+
- Top10 关键词数：+8
- 重点页面 CTR：
  - `/en/models/llama-70b-q4/` 提升 +1.5%
  - `/en/tools/quantization-blind-test/` 提升 +1.5%
- SEO 导入联盟点击：44 -> 80+

## 2) 周节奏（固定）

- 周一：基线复盘（Search Console + conversion funnel）
- 周三：中期发布（标题摘要/内链/模板改动）
- 周五：周报与下周排程（Weekly SEO Report）

## 3) 执行看板（可直接映射 GitHub Projects / Notion）

| ID | 周次 | 工作流 | 任务 | 优先级 | 负责人 | 开始 | 截止 | 完成定义（DoD） | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| SEO-001 | Week 1 | 技术SEO | 模型页注入 `FAQPage + BreadcrumbList` schema | P0 | 开发 | 2026-03-04 | 2026-03-06 | Rich Results Test 通过，线上页面可见 | Todo |
| SEO-002 | Week 1 | 技术SEO | 博客页注入 `Article` schema | P0 | 开发 | 2026-03-04 | 2026-03-06 | 3 篇抽检通过 schema 校验 | Todo |
| SEO-003 | Week 1 | 技术SEO | 工具页注入 `SoftwareApplication` schema | P0 | 开发 | 2026-03-04 | 2026-03-07 | 工具页 schema 无报错 | Todo |
| SEO-004 | Week 1 | CTR优化 | Top20 落地页重写 Title/Description（版本A） | P0 | SEO | 2026-03-04 | 2026-03-08 | Top20 全覆盖，变更记录入表 | Todo |
| SEO-005 | Week 1 | 内链 | 文末三链规则上线（同主题/决策页/转化页） | P0 | 内容+开发 | 2026-03-05 | 2026-03-09 | 新发与更新文章 100% 带三链 | Todo |
| SEO-006 | Week 1 | 监控 | 周报模板固定字段（点击/CTR/Top10/转化） | P0 | SEO | 2026-03-06 | 2026-03-09 | 周报字段稳定输出 | Todo |
| SEO-007 | Week 2 | 内容 | 发布增强版：`best-24gb-vram-models-2026` | P1 | 内容 | 2026-03-11 | 2026-03-13 | 发布+索引提交+内链>=5 | Todo |
| SEO-008 | Week 2 | 内容 | 发布增强版：`rtx4090-vs-rtx3090-for-local-llm` | P1 | 内容 | 2026-03-11 | 2026-03-13 | 发布+索引提交+内链>=5 | Todo |
| SEO-009 | Week 2 | 专题页 | 新增 Pillar：24GB VRAM 选型页 | P1 | 内容+开发 | 2026-03-12 | 2026-03-15 | 子页链接>=8，含对比表 | Todo |
| SEO-010 | Week 2 | 专题页 | 新增 Pillar：OOM 修复索引页 | P1 | 内容+开发 | 2026-03-12 | 2026-03-15 | 子页链接>=8，含排错路径 | Todo |
| SEO-011 | Week 2 | 旧文刷新 | Top 流量旧文更新 8 篇（FAQ/对比/CTA） | P1 | 内容 | 2026-03-11 | 2026-03-17 | 8 篇完成且有更新记录 | Todo |
| SEO-012 | Week 2 | 数据新鲜度 | Search Console 数据刷新频率提升并告警 | P0 | 开发+SEO | 2026-03-11 | 2026-03-17 | 过期阈值告警生效 | Todo |
| SEO-013 | Week 3 | CTR优化 | Top20 标题摘要版本B（A/B 第二轮） | P0 | SEO | 2026-03-18 | 2026-03-22 | Top20 至少 10 页完成 B 版 | Todo |
| SEO-014 | Week 3 | 模板化 | 模型页“对比模块”组件化并复用 | P1 | 开发 | 2026-03-18 | 2026-03-23 | 新老模型页均可渲染 | Todo |
| SEO-015 | Week 3 | 模板化 | 模型页“下一步动作 CTA”模块统一 | P1 | 开发+运营 | 2026-03-18 | 2026-03-23 | CTA 点击追踪正常入漏斗 | Todo |
| SEO-016 | Week 3 | 内链 | 对比文章互链网（3090/4090/24GB/OOM） | P1 | 内容 | 2026-03-19 | 2026-03-24 | 目标文章互链覆盖>=90% | Todo |
| SEO-017 | Week 3 | 监控 | 技术SEO巡检：canonical/hreflang/孤儿页/软404 | P1 | 开发+SEO | 2026-03-20 | 2026-03-24 | 阻断级问题清零 | Todo |
| SEO-018 | Week 4 | 外链 | 社区分发 5 渠道（Reddit/HN/论坛/博客） | P2 | 运营 | 2026-03-25 | 2026-03-30 | 有效外链>=5 | Todo |
| SEO-019 | Week 4 | 数据复盘 | 30天 KPI 复盘 + 下月 OKR 草案 | P0 | SEO+运营 | 2026-03-29 | 2026-04-01 | 复盘报告+下月计划 | Todo |
| SEO-020 | Week 4 | 转化 | SEO->Affiliate 路径诊断与二次优化 | P0 | 开发+运营 | 2026-03-26 | 2026-04-02 | 联盟点击达成阶段目标 | Todo |

## 4) 项目字段建议（GitHub Projects）

- `Status`: Todo / In Progress / In Review / Done / Blocked
- `Priority`: P0 / P1 / P2
- `Owner`: SEO / 开发 / 内容 / 运营
- `Sprint`: Week 1 / Week 2 / Week 3 / Week 4
- `Due Date`: 截止日期
- `KPI Link`: 对应报表或日志链接
- `Risk`: Low / Medium / High

## 5) 阻塞升级规则

- P0 任务逾期 >24h：升级到当日处理
- 周五前未产出周报：阻断下周排程
- 关键指标连续 2 周无提升：启动专项复盘（标题、内链、内容质量、分发各一轮）

## 6) Issue 标题模板（建议）

- `SEO-001 feat(schema): add FAQPage and BreadcrumbList for model pages`
- `SEO-004 feat(seo): refresh meta title/description for top20 landing pages (A)`
- `SEO-013 feat(seo): top20 metadata experiment round B`
- `SEO-020 fix(conversion): optimize seo-to-affiliate funnel path`
