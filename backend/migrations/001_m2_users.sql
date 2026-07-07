-- M2 账号体系迁移：给已有交互表加 user_id
-- users / verification_codes 新表由应用启动时 create_all 自动创建（需先重启一次后端）
-- 执行：psql -h 127.0.0.1 -U quantquiz -d postgres -f 001_m2_users.sql

ALTER TABLE attempt_logs      ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE favorites         ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE question_reports  ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_attempt_user_id  ON attempt_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites (user_id);
