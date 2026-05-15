# spider/__init__.py - 爬虫模块初始化
"""
试卷爬虫模块
用于从shijuan1.com等网站爬取真题到本地题库
"""

from spider.database import (
    init_database,
    get_db_stats,
    add_yuwen_question,
    add_yingyu_question,
    add_shuxue_question,
    get_yuwen_questions,
    get_yingyu_questions,
    get_shuxue_questions,
)

from spider.integration import (
    get_yuwen_from_bank,
    get_yingyu_from_bank,
    get_spider_questions,
    get_bank_status,
    is_bank_ready,
    generate_yuwen_with_bank,
    generate_yingyu_with_bank,
)

__all__ = [
    "init_database",
    "get_db_stats",
    "add_yuwen_question",
    "add_yingyu_question",
    "add_shuxue_question",
    "get_yuwen_questions",
    "get_yingyu_questions",
    "get_shuxue_questions",
    "get_yuwen_from_bank",
    "get_yingyu_from_bank",
    "get_spider_questions",
    "get_bank_status",
    "is_bank_ready",
    "generate_yuwen_with_bank",
    "generate_yingyu_with_bank",
]
