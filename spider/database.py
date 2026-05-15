# spider/database.py - 题库数据库管理
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "question_bank.db"

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """初始化题库数据库"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 创建语文题库表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS yuwen_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_type TEXT NOT NULL,  -- 题型：yuedu(阅读), gushi(古诗文), etc
            grade TEXT NOT NULL,          -- 年级
            title TEXT,                   -- 题目标题（如阅读材料标题）
            content TEXT NOT NULL,        -- 题目内容
            answer TEXT,                  -- 答案
            source_url TEXT,              -- 来源URL
            source_name TEXT,             -- 来源网站名
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建英语题库表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS yingyu_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_type TEXT NOT NULL,  -- 题型：yuedu(阅读), danci(单词), etc
            grade TEXT NOT NULL,           -- 年级
            title TEXT,                    -- 题目标题
            content TEXT NOT NULL,         -- 题目内容
            answer TEXT,                   -- 答案
            options TEXT,                  -- 选项(JSON格式)
            source_url TEXT,               -- 来源URL
            source_name TEXT,              -- 来源网站名
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建数学题库表（用于存储爬取的真题）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shuxue_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_type TEXT NOT NULL,  -- 题型
            grade TEXT NOT NULL,           -- 年级
            question TEXT NOT NULL,       -- 题目
            answer TEXT,                  -- 答案
            difficulty TEXT,              -- 难度
            source_url TEXT,              -- 来源URL
            source_name TEXT,             -- 来源网站名
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_yuwen_type ON yuwen_questions(question_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_yuwen_grade ON yuwen_questions(grade)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_yingyu_type ON yingyu_questions(question_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_yingyu_grade ON yingyu_questions(grade)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shuxue_type ON shuxue_questions(question_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shuxue_grade ON shuxue_questions(grade)")
    
    conn.commit()
    conn.close()
    print(f"[DB] 题库数据库初始化完成: {DB_PATH}")

# ==================== 语文题库操作 ====================

def add_yuwen_question(q_type, grade, title, content, answer, source_url=""):
    """添加语文题目"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO yuwen_questions (question_type, grade, title, content, answer, source_url, source_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (q_type, grade, title, content, answer, source_url, "shijuan1.com"))
    conn.commit()
    qid = cursor.lastrowid
    conn.close()
    return qid

def get_yuwen_questions(q_type=None, grade=None, count=10):
    """获取语文题目"""
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = "SELECT * FROM yuwen_questions WHERE 1=1"
    params = []
    if q_type:
        sql += " AND question_type = ?"
        params.append(q_type)
    if grade:
        sql += " AND grade = ?"
        params.append(grade)
    sql += " ORDER BY RANDOM() LIMIT ?"
    params.append(count)
    
    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

# ==================== 英语题库操作 ====================

def add_yingyu_question(q_type, grade, title, content, answer, options=None, source_url=""):
    """添加英语题目"""
    conn = get_connection()
    cursor = conn.cursor()
    options_json = json.dumps(options) if options else None
    cursor.execute("""
        INSERT INTO yingyu_questions (question_type, grade, title, content, answer, options, source_url, source_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (q_type, grade, title, content, answer, options_json, source_url, "shijuan1.com"))
    conn.commit()
    qid = cursor.lastrowid
    conn.close()
    return qid

def get_yingyu_questions(q_type=None, grade=None, count=10):
    """获取英语题目"""
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = "SELECT * FROM yingyu_questions WHERE 1=1"
    params = []
    if q_type:
        sql += " AND question_type = ?"
        params.append(q_type)
    if grade:
        sql += " AND grade = ?"
        params.append(grade)
    sql += " ORDER BY RANDOM() LIMIT ?"
    params.append(count)
    
    cursor.execute(sql, params)
    results = []
    for row in cursor.fetchall():
        item = dict(row)
        if item.get('options'):
            item['options'] = json.loads(item['options'])
        results.append(item)
    conn.close()
    return results

# ==================== 数学题库操作 ====================

def add_shuxue_question(q_type, grade, question, answer, difficulty="", source_url=""):
    """添加数学题目"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO shuxue_questions (question_type, grade, question, answer, difficulty, source_url, source_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (q_type, grade, question, answer, difficulty, source_url, "shijuan1.com"))
    conn.commit()
    qid = cursor.lastrowid
    conn.close()
    return qid

def get_shuxue_questions(q_type=None, grade=None, count=10):
    """获取数学题目"""
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = "SELECT * FROM shuxue_questions WHERE 1=1"
    params = []
    if q_type:
        sql += " AND question_type = ?"
        params.append(q_type)
    if grade:
        sql += " AND grade = ?"
        params.append(grade)
    sql += " ORDER BY RANDOM() LIMIT ?"
    params.append(count)
    
    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

# ==================== 统计信息 ====================

def get_db_stats():
    """获取题库统计信息"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM yuwen_questions")
    yuwen_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM yingyu_questions")
    yingyu_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM shuxue_questions")
    shuxue_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "yuwen": yuwen_count,
        "yingyu": yingyu_count,
        "shuxue": shuxue_count,
        "total": yuwen_count + yingyu_count + shuxue_count
    }

if __name__ == "__main__":
    init_database()
    stats = get_db_stats()
    print(f"[DB] 题库统计: {stats}")
