-- M4 搜索升级：solutions 表加 trgm 索引（stem 的已在 create_indexes.sql 中建过）
-- 执行：psql -h 127.0.0.1 -U quantquiz -d postgres -f 002_m4_search.sql
CREATE INDEX IF NOT EXISTS idx_solutions_content_trgm
  ON solutions USING GIN (content_markdown gin_trgm_ops);
