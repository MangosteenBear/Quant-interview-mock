-- 量化题库 PostgreSQL 性能索引
-- 执行：psql $DATABASE_URL -f create_indexes.sql

-- 列表/筛选最常用：status + id（覆盖默认排序）
CREATE INDEX IF NOT EXISTS idx_questions_status_id
    ON questions (status, id);

-- 按来源筛选
CREATE INDEX IF NOT EXISTS idx_questions_source_status
    ON questions (source_id, status);

-- 按题型筛选
CREATE INDEX IF NOT EXISTS idx_questions_type_status
    ON questions (question_type, status);

-- 按难度筛选
CREATE INDEX IF NOT EXISTS idx_questions_diff_status
    ON questions (difficulty, status);

-- 前后题导航（adjacent 查询）
CREATE INDEX IF NOT EXISTS idx_questions_status_id_desc
    ON questions (status, id DESC);

-- 作答记录按设备查询（未来统计/错题本用）
CREATE INDEX IF NOT EXISTS idx_attempt_device_id
    ON attempt_logs (device_id);

CREATE INDEX IF NOT EXISTS idx_attempt_device_question
    ON attempt_logs (device_id, question_id);

-- 收藏按设备查询
CREATE INDEX IF NOT EXISTS idx_favorites_device_id
    ON favorites (device_id);

-- 全文搜索：pg_trgm GIN 索引（支持 ILIKE '%keyword%' 走索引）
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_questions_stem_trgm
    ON questions USING GIN (stem_markdown gin_trgm_ops);
