-- 注意：articles 表没有固定分类字段，分类由 Agent 动态生成
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    source VARCHAR(50) NOT NULL,          -- linuxdo/reddit/twitter
    source_id VARCHAR(100),
    raw_content TEXT,
    cleaned_text TEXT,
    summary TEXT,                         -- AI 生成的详细摘要
    brief TEXT,                           -- AI 生成的一句话快讯
    tags TEXT[] DEFAULT '{}',             -- Agent 打的语义标签
    section VARCHAR(50),                  -- Agent 分配的当日栏目名
    importance_score INTEGER CHECK (importance_score BETWEEN 1 AND 5),
    status VARCHAR(20) DEFAULT 'raw',    -- raw/fetched/summarized/reviewed/classified/published
    published_date DATE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_reports (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL UNIQUE,
    title TEXT NOT NULL,
    article_order INTEGER[] DEFAULT '{}',
    sections JSONB DEFAULT '[]',          -- Agent 规划的栏目结构
    editor_notes TEXT,
    total_articles INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- updated_at 自动更新触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_articles_updated_at
    BEFORE UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_reports_updated_at
    BEFORE UPDATE ON daily_reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_articles_published_date ON articles(published_date);
CREATE INDEX idx_articles_source ON articles(source);
CREATE INDEX idx_articles_section ON articles(section);
CREATE INDEX idx_reports_date ON daily_reports(report_date DESC);
