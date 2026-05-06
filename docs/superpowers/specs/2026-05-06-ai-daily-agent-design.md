---
title: AI Daily News Agent 设计文档
date: 2026-05-06
status: draft
---

# AI Daily News Agent 设计文档

## 1. 项目概述

构建一个 AI 驱动的日报自动生成系统，每日自动从多个渠道采集 AI 领域最新资讯，经过筛选、分类、摘要、排版，生成一份美观的 Web 端日报。

### 核心目标

- 每日自动产出 10-15 条精选 AI 资讯（2-3 篇深度 + 8-12 条快讯）
- 通过 "真 Agent"（Editor-in-Chief Agent）自主决策内容策划和质量把控
- 提供简洁美观的原浆木纸风格前端
- 支持每日定时发布+历史归档

## 2. 架构设计

### 2.1 混合架构：固定采集 + Agent 编排

系统分为两层：

**层 1: 固定采集层**
- 定时触发，确定性执行
- 并行抓取固定数据源（LinuxDO、Reddit、Twitter/X）
- 产出约 30-50 条原始文章，存入 Raw Pool

**层 2: 编辑 Agent（核心）**
- 基于 LangGraph 实现的 Editor-in-Chief Agent
- 从 Raw Pool 取材，自主决策选、挖、写、排
- 通过工具调用 + 自我反思循环保证输出质量

### 2.2 每日流程时间线

```
06:00  定时触发
06:00-06:30  采集层并行抓取 LinuxDO / Reddit / X
06:30-06:35  原始文章存入 Raw Pool (~30-50条)
06:35  Editor Agent 启动，浏览全貌
06:40  Agent 决策：头条/普通/过滤
06:45-07:15  Agent 循环：取内容→写摘要→反思→重写→分类
07:20  排版 + 生成完整日报
07:30  日报上线
```

### 2.3 最终输出量级

```
原始采集:  ~30-50 条/天
Agent筛选: → 15-20 条
最终日报:  → 10-15 条
  ├── 头条深度: 2-3 篇 (含背景搜索+深度摘要)
  └── 快讯简讯: 8-12 条 (一句话摘要+原文链接)
```

## 3. 数据源策略

### 3.1 固定基础源

| 源 | 方式 | 内容类型 |
|----|------|---------|
| LinuxDO | 爬虫 | 中文 AI 讨论/分享 |
| Reddit | PRAW API (r/MachineLearning, r/artificial, r/LocalLLaMA) | 英文技术讨论 |
| Twitter/X | API 或爬虫 | 研究者动态/官方发布 |

### 3.2 Agent 自扩展

Agent 通过 `web_search` 工具自行挖掘更多资料，不为 Agent 限定死的数据源列表。

## 4. Agent 系统设计

### 4.1 Editor-in-Chief Agent

核心是一个 Tool-Using Agent，通过 LangGraph 编排：

```
scan_sources() → Agent 决策选材
  → 对头条: fetch_content + web_search + write_summary → critique → rewrite
  → 对快讯: write_summary → critique
  → classify()
  → manage_daily_report()
```

### 4.2 工具清单

| 工具 | 功能 | 备注 |
|------|------|------|
| `scan_sources(keywords?)` | 并行扫描基础源，返回标题+链接+热度 | 采集层能力封装 |
| `fetch_content(url)` | 获取文章正文，自动清洗 | Playwright + BS4 |
| `web_search(query)` | 搜索背景资料/多方评论 | 搜索结果摘要 |
| `write_summary(article, style)` | 按风格生成摘要 | 深度/简讯/一句话 |
| `classify(content)` | 归入栏目+打标签+评估重要度 | 1-5 分 |
| `critique(content)` | 自审摘要质量 | 返回修改建议或通过 |

### 4.3 Reflection 循环

每条内容在生成摘要后执行自审：

```
write_summary → critique
  → 合格 → 通过
  → 不合格 → 返回修改建议 → 重写 → critique...
```

**反思维度：**
- 是否覆盖 5W1H？
- 关键数据/数字是否保留？
- 是否客观无幻觉？
- 长度是否合适（头条 ~200 字 / 快讯 ~50 字）？

### 4.4 不采用的范式

- **Plan-and-Execute**: 日报流程是确定性固定流程，无需 LLM 自行规划步骤
- **ReAct**: 每个 Node 做单一明确的 LLM 调用，无需 reasoning-acting 循环
- **Reflection**: ✅ 部分采用，聚焦摘要质量自审

## 5. 数据模型

### 5.1 articles 表

不设固定分类字段。Agent 通过语义标签聚类，动态决定当日栏目结构。

```sql
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    source VARCHAR(50) NOT NULL,          -- linuxdo/reddit/twitter
    source_id TEXT,
    raw_content TEXT,
    cleaned_text TEXT,
    summary TEXT,
    tags TEXT[],                          -- Agent 打的语义标签，如 ['模型发布','Anthropic']
    section VARCHAR(50),                  -- Agent 分配的当日栏目名，如 "模型进展"
    importance_score INTEGER CHECK (importance_score BETWEEN 1 AND 5),
    status VARCHAR(20) DEFAULT 'raw',    -- raw/cleaned/classified/summarized/published
    published_date DATE,
    metadata JSONB,                       -- 原文、作者、链接等
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 5.2 daily_reports 表

```sql
CREATE TABLE daily_reports (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL UNIQUE,
    title TEXT NOT NULL,                  -- "AI日报 · 2026年5月6日"
    article_order INTEGER[],              -- 文章ID排序
    sections JSONB,                       -- Agent 规划的当日栏目结构
    editor_notes TEXT,                    -- Agent的编辑手记
    total_articles INTEGER,
    status VARCHAR(20) DEFAULT 'draft',   -- draft/published
    created_at TIMESTAMP DEFAULT NOW()
);
```

**sections JSONB 示例** — Agent 每日动态决定栏目结构：

```json
{
  "layout": [
    {"name": "模型发布", "order": 1, "color": "#D4C5A9"},
    {"name": "开源动态", "order": 2, "color": "#EDE4D4"},
    {"name": "行业融资", "order": 3, "color": "#F5F0E8"}
  ]
}
```

### 5.3 动态分类逻辑

Agent 不写入固定分类字段，而是在所有文章处理完毕后执行一次"版面规划"：

1. **语义聚类** — 识别文章之间的主题关联，自动分组
2. **栏目命名** — 为每组生成 2-4 字栏目名
3. **排序决策** — 决定栏目先后顺序
4. **写入 report** — 将栏目结构存入 `daily_reports.sections`

## 6. 技术栈

| 层 | 技术选型 |
|---|---------|
| **编排层** | LangGraph (Agent 工作流) |
| **Agent 模型** | DeepSeek API |
| **采集工具** | Playwright + PRAW (Reddit) + Feedparser |
| **存储** | PostgreSQL + Redis (缓存/队列) |
| **API** | FastAPI |
| **前端** | React + Tailwind CSS (原浆木纸色系) |
| **定时调度** | APScheduler → 触发 LangGraph |
| **部署** | Docker Compose → VPS |

### 前端色板

| 用途 | 色值 | 说明 |
|------|------|------|
| 背景 | `#F5F0E8` | 原浆纸色 |
| 卡片 | `#EDE4D4` | 浅木色 |
| 卡片(白) | `#FFFFFF` | 普通卡片 |
| 强调边框 | `#D4C5A9` | 深木色 |
| 次要文字 | `#8B7D6B` | 暖灰褐 |
| 主要文字 | `#5C4F3F` | 暖褐色 |
| 标题 | `#2C2820` | 深褐 |

## 7. 前端页面设计

### 7.1 首页 — 简洁卡片流

- 顶部：品牌标识 + 日期 + 栏目导航（Agent 动态生成）
- 头条置顶：暖色卡片，标题+摘要+标签+来源
- 普通文章：按 Agent 规划的栏目分组展示，每组有标题
- 无栏目概念的日子：纯按分数排列
- 底部：统计信息（今日篇数 + 来源标注）

### 7.2 文章详情页

- 阅读进度条
- 分类标签 + 标题 + 日期/来源
- 原文链接（显眼位置）
- AI 摘要正文 + 关键要点
- 相关标签云
- 无评论区/点赞功能

### 7.3 归档浏览

- 按日期维度的历史日报列表
- 支持按栏目筛选
- 全文搜索

## 8. 项目目录结构

```
ai-news/
├── agent/                       # LangGraph Agent
│   ├── __init__.py
│   ├── graph.py                 # 工作流图定义
│   ├── state.py                 # State 定义
│   ├── tools/                   # Agent 工具
│   │   ├── __init__.py
│   │   ├── scanner.py           # 扫源
│   │   ├── fetcher.py           # 抓取+清洗
│   │   ├── searcher.py          # 搜索
│   │   ├── summarizer.py        # 摘要生成
│   │   └── classifier.py        # 分类打标
│   ├── prompts/                 # 提示词模板
│   │   ├── summarizer.yaml
│   │   ├── classifier.yaml
│   │   └── critique.yaml
│   └── reflection.py            # 自审逻辑
├── collector/                   # 固定采集层
│   ├── __init__.py
│   ├── base.py                  # 采集器基类
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── linuxdo.py
│   │   ├── reddit.py
│   │   └── twitter.py
│   └── pipeline.py              # 采集管道
├── api/                         # FastAPI
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/                  # SQLAlchemy 模型
│   ├── routes/
│   │   ├── articles.py
│   │   ├── reports.py
│   │   ├── admin.py
│   │   └── search.py
│   └── dependencies.py
├── frontend/                    # React + Tailwind
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── Article.tsx
│   │   │   └── Archive.tsx
│   │   ├── components/
│   │   │   ├── Card.tsx
│   │   │   ├── Tag.tsx
│   │   │   ├── FilterBar.tsx
│   │   │   └── Header.tsx
│   │   ├── api/
│   │   └── styles/
│   └── package.json
├── db/
│   ├── schema.sql
│   └── migrations/
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.frontend
├── requirements.txt
└── config.yaml                   # 来源、定时、LLM 配置
```

## 9. 部署方案

### 9.1 本地开发

```bash
docker-compose up -d db redis    # 启动 PostgreSQL + Redis
pip install -r requirements.txt  # 安装后端依赖
cd frontend && npm install && npm run dev  # 启动前端
uvicorn api.main:app             # 启动 API
```

### 9.2 生产部署

Docker Compose 一键部署：
- API + Agent 容器
- PostgreSQL 容器
- Redis 容器
- Nginx（前端静态文件 + 反向代理）

## 10. 未来扩展（V2）

- 用户订阅 + 邮件推送
- 用户偏好学习（Agent 根据点击调整选材）
- 更多数据源（插件化）
- 多语言日报
- LLM 成本追踪 + 预算控制
