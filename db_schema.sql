-- ============================================
-- 个人AI学习教练系统 V1.0 数据库 Schema
-- SQLite (WAL 模式, 外键约束开启)
-- ============================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ============================================
-- 1. 用户表 (预留多用户支持, V1.0 写死 user_id=1)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY DEFAULT 1,
    name            TEXT NOT NULL DEFAULT '学生',
    grade           TEXT,
    avatar_url      TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认用户
INSERT OR IGNORE INTO users (user_id, name, grade) VALUES (1, '学生', '');

-- ============================================
-- 2. 错题本表
-- ============================================
CREATE TABLE IF NOT EXISTS error_records (
    record_id       TEXT PRIMARY KEY,
    user_id         INTEGER DEFAULT 1,
    question_id     TEXT NOT NULL,
    subject         TEXT NOT NULL CHECK(subject IN ('math', 'chinese', 'english', 'physics', 'chemistry')),
    problem_text    TEXT NOT NULL,
    latex           TEXT,
    knowledge_points TEXT,  -- JSON数组: ["函数求导", "幂函数"]
    wrong_answer    TEXT,
    correct_answer  TEXT,
    difficulty      TEXT DEFAULT 'medium' CHECK(difficulty IN ('easy', 'medium', 'hard')),
    comment         TEXT,  -- 批改评语
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ============================================
-- 3. 错题复习记录表 (间隔重复)
-- ============================================
CREATE TABLE IF NOT EXISTS review_records (
    review_id       TEXT PRIMARY KEY,
    record_id       TEXT NOT NULL,
    user_id         INTEGER DEFAULT 1,
    review_date     DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_correct      BOOLEAN NOT NULL,
    review_count    INTEGER DEFAULT 1,
    next_review_date DATETIME,
    status          TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'reviewing', 'mastered')),
    FOREIGN KEY (record_id) REFERENCES error_records(record_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ============================================
-- 4. 试卷表
-- ============================================
CREATE TABLE IF NOT EXISTS exams (
    exam_id         TEXT PRIMARY KEY,
    user_id         INTEGER DEFAULT 1,
    subject         TEXT NOT NULL,
    grade           TEXT,
    chapter         TEXT,
    total_score     INTEGER DEFAULT 100,
    generated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    status          TEXT DEFAULT 'generated' CHECK(status IN ('generated', 'graded', 'archived')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ============================================
-- 5. 试卷题目表
-- ============================================
CREATE TABLE IF NOT EXISTS exam_questions (
    question_id     TEXT PRIMARY KEY,
    exam_id         TEXT NOT NULL,
    question_num    INTEGER NOT NULL,
    type            TEXT NOT NULL CHECK(type IN ('choice', 'fill_blank', 'calculation', 'essay')),
    content         TEXT NOT NULL,
    latex           TEXT,
    options         TEXT,  -- JSON数组: ["A. 4", "B. 5", ...]
    answer          TEXT,
    score           INTEGER DEFAULT 5,
    difficulty      TEXT DEFAULT 'medium',
    FOREIGN KEY (exam_id) REFERENCES exams(exam_id)
);

-- ============================================
-- 6. 答卷记录表
-- ============================================
CREATE TABLE IF NOT EXISTS exam_attempts (
    attempt_id      TEXT PRIMARY KEY,
    exam_id         TEXT NOT NULL,
    user_id         INTEGER DEFAULT 1,
    total_score     INTEGER,
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    status          TEXT DEFAULT 'in_progress' CHECK(status IN ('in_progress', 'completed', 'graded')),
    FOREIGN KEY (exam_id) REFERENCES exams(exam_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ============================================
-- 7. 答卷题目得分表
-- ============================================
CREATE TABLE IF NOT EXISTS attempt_scores (
    score_id        TEXT PRIMARY KEY,
    attempt_id      TEXT NOT NULL,
    question_id     TEXT NOT NULL,
    student_answer  TEXT,
    is_correct      BOOLEAN,
    score           INTEGER DEFAULT 0,
    comment         TEXT,
    FOREIGN KEY (attempt_id) REFERENCES exam_attempts(attempt_id)
);

-- ============================================
-- 8. 目标表 (目标奖励系统)
-- ============================================
CREATE TABLE IF NOT EXISTS goals (
    goal_id         TEXT PRIMARY KEY,
    user_id         INTEGER DEFAULT 1,
    title           TEXT NOT NULL,
    description     TEXT,
    target_points   INTEGER NOT NULL,
    current_points  INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'active' CHECK(status IN ('active', 'frozen', 'confirmed', 'cancelled')),
    progress_percent INTEGER DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    deadline        DATETIME,
    completed_at    DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ============================================
-- 9. 积分表
-- ============================================
CREATE TABLE IF NOT EXISTS points_ledger (
    point_id        TEXT PRIMARY KEY,
    user_id         INTEGER DEFAULT 1,
    source_type     TEXT NOT NULL,  -- 'exam', 'error_review', 'daily_checkin', 'goal_redeem'
    source_id       TEXT,  -- 关联的业务ID
    points          INTEGER NOT NULL,  -- 正数=获得, 负数=消耗
    description     TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ============================================
-- 10. 积分冻结表 (兑换时冻结积分)
-- ============================================
CREATE TABLE IF NOT EXISTS points_frozen (
    freeze_id       TEXT PRIMARY KEY,
    user_id         INTEGER DEFAULT 1,
    goal_id         TEXT,
    freeze_points   INTEGER NOT NULL,
    freeze_reason   TEXT,
    status          TEXT DEFAULT 'frozen' CHECK(status IN ('frozen', 'deducted', 'released')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    released_at     DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (goal_id) REFERENCES goals(goal_id)
);

-- ============================================
-- 11. 家长推送记录表
-- ============================================
CREATE TABLE IF NOT EXISTS parent_notifications (
    notify_id       TEXT PRIMARY KEY,
    user_id         INTEGER DEFAULT 1,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    send_channel    TEXT DEFAULT 'serverchan',  -- 'serverchan', 'wechat', 'dingtalk'
    send_status     TEXT DEFAULT 'pending' CHECK(send_status IN ('pending', 'sent', 'failed')),
    sent_at         DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ============================================
-- 12. 知识点表 (知识图谱)
-- ============================================
CREATE TABLE IF NOT EXISTS knowledge_points (
    kp_id           TEXT PRIMARY KEY,
    subject         TEXT NOT NULL,
    name            TEXT NOT NULL,
    parent_kp_id    TEXT,  -- 父级知识点
    mastery_level   REAL DEFAULT 0.0 CHECK(mastery_level BETWEEN 0 AND 1),
    life_skill_tags TEXT,  -- JSON数组: ["逻辑思维", "创造力"] (预留字段)
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_kp_id) REFERENCES knowledge_points(kp_id)
);

-- ============================================
-- 13. 知识点关联表 (错题 ↔ 知识点)
-- ============================================
CREATE TABLE IF NOT EXISTS error_knowledge_map (
    map_id          TEXT PRIMARY KEY,
    record_id       TEXT NOT NULL,
    kp_id           TEXT NOT NULL,
    FOREIGN KEY (record_id) REFERENCES error_records(record_id),
    FOREIGN KEY (kp_id) REFERENCES knowledge_points(kp_id)
);

-- ============================================
-- 14. 学习内容表 (微课、听力材料等)
-- ============================================
CREATE TABLE IF NOT EXISTS content_items (
    content_id      TEXT PRIMARY KEY,
    user_id         INTEGER DEFAULT 1,
    type            TEXT NOT NULL CHECK(type IN ('micro_lesson', 'listening', 'dialogue')),
    title           TEXT NOT NULL,
    content_url     TEXT,  -- 音频/视频URL
    content_text    TEXT,  -- 文本内容
    status          TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'published', 'archived')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ============================================
-- 15. 学习内容源预留表 (外部内容源接入)
-- ============================================
CREATE TABLE IF NOT EXISTS content_sources (
    source_id       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,  -- 'web_scrape', 'manual', 'api_feed'
    url             TEXT,
    schedule        TEXT,  -- cron表达式
    status          TEXT DEFAULT 'inactive' CHECK(status IN ('active', 'inactive', 'testing')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 16. 亲子互动消息表
-- ============================================
CREATE TABLE IF NOT EXISTS parent_messages (
    message_id      TEXT PRIMARY KEY,
    sender          TEXT NOT NULL,  -- '妈妈', '爸爸', '老师'
    content         TEXT NOT NULL,
    display_status  TEXT DEFAULT 'pending' CHECK(display_status IN ('pending', 'displayed', 'dismissed')),
    displayed_at    DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 17. 学习日记表
-- ============================================
CREATE TABLE IF NOT EXISTS learning_diaries (
    diary_id        TEXT PRIMARY KEY,
    user_id         INTEGER DEFAULT 1,
    date            DATE NOT NULL,
    mood            TEXT,  -- 'happy', 'focused', 'frustrated', 'tired'
    summary         TEXT,
    audio_url       TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ============================================
-- 索引优化
-- ============================================
CREATE INDEX IF NOT EXISTS idx_error_records_subject ON error_records(subject);
CREATE INDEX IF NOT EXISTS idx_error_records_created ON error_records(created_at);
CREATE INDEX IF NOT EXISTS idx_review_records_next_date ON review_records(next_review_date);
CREATE INDEX IF NOT EXISTS idx_exam_questions_exam ON exam_questions(exam_id);
CREATE INDEX IF NOT EXISTS idx_attempt_scores_attempt ON attempt_scores(attempt_id);
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
CREATE INDEX IF NOT EXISTS idx_points_ledger_user_date ON points_ledger(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_parent_messages_status ON parent_messages(display_status);
CREATE INDEX IF NOT EXISTS idx_knowledge_points_subject ON knowledge_points(subject);
