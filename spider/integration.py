# spider/integration.py - 爬虫题库与现有系统的整合
import random
from spider.database import (
    get_yuwen_questions,
    get_yingyu_questions,
    get_shuxue_questions,
    get_db_stats
)

# 年级中文转数字
GRADE_NUM = {
    "一年级": "1", "二年级": "2", "三年级": "3",
    "四年级": "4", "五年级": "5", "六年级": "6"
}

# 年级数字转中文
GRADE_NUM_REVERSE = {
    "1": "一年级", "2": "二年级", "3": "三年级",
    "4": "四年级", "5": "五年级", "6": "六年级"
}

def format_grade_for_db(grade):
    """将年级格式化为数据库存储格式"""
    if not grade:
        return None
    if "年级" in grade:
        return grade
    if grade.isdigit():
        return f"{grade}年级"
    return GRADE_NUM.get(grade, grade)

ENGLISH_GRADES = {"三年级": "3", "四年级": "4", "五年级": "5", "六年级": "6"}

# ==================== 内置模拟题库 ====================
# 当题库为空时使用的示例题目

BUILTIN_YUWEN = {
    "阅读理解": [
        {"title": "春天的早晨", "content": "春天的早晨，阳光明媚。小鸟在枝头唱歌，花儿张开了笑脸。小明背着小书包，去学校上学。路上，他看见柳树发出了嫩绿的芽，小草也探出了头。春天真美啊！\n\n1. 短文共有几个自然段？\n2. 春天里有哪些景物？\n3. 小明去干什么？"},
        {"title": "可爱的小猫", "content": "我家有一只可爱的小猫。它的毛是白色的，像雪一样。小猫的眼睛是蓝色的，像两颗宝石。它喜欢吃鱼，也喜欢玩毛线球。每天早上，它都会蹲在窗台上晒太阳。\n\n1. 小猫的毛是什么颜色的？\n2. 小猫的眼睛像什么？\n3. 小猫喜欢做什么？"},
        {"title": "公园的秋天", "content": "秋天到了，公园里的树叶变黄了。一阵秋风吹过，树叶纷纷飘落，像一只只金色的蝴蝶。孩子们在树下捡落叶，老人们在长椅上聊天。秋天的公园真美！\n\n1. 秋天树叶发生了什么变化？\n2. 树叶像什么？\n3. 孩子们在做什么？"},
    ],
    "古诗文默写": [
        {"title": "静夜思", "content": "床前明月光，疑是地上霜。举头望明月，低头思故乡。\n\n1. 这首诗的作者是谁？\n2. \"疑\"字是什么意思？\n3. 默写全诗。"},
        {"title": "春晓", "content": "春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少。\n\n1. 这首诗描写的是什么季节？\n2. \"处处闻啼鸟\"是什么意思？\n3. 默写全诗。"},
        {"title": "咏鹅", "content": "鹅鹅鹅，曲项向天歌。白毛浮绿水，红掌拨清波。\n\n1. 诗中描写的是哪种动物？\n2. \"白毛浮绿水\"描写了什么景象？\n3. 默写全诗。"},
    ],
    "拼音练习": [
        {"title": "拼音乐园", "content": "一、用拼音写出下列汉字\nbà ba（爸爸）mā ma（妈妈）\n\n二、给加点字选择正确的读音\n1. 春天（chūn tūn） 2. 花开（huā fā）\n\n三、看拼音写词语\nchūn tiān（    ） huā kāi（    ）"},
        {"title": "拼音测试", "content": "一、读拼音写词语\nzhong guo（    ） ren min（    ）\n\n二、给多音字注音\n1. 长大（zhǎng/cháng） 2. 行走（háng/xíng）\n\n三、选择正确读音\n1. 音乐（yuè/lè） 2. 快乐（yuè/lè）"},
    ],
}

BUILTIN_YINGYU = {
    "阅读理解": [
        {"title": "My Family", "content": "I have a happy family. There are four people in my family. My father is a teacher. My mother is a nurse. I am a student. My sister is a baby. We love each other.\n\n1. How many people are there in the family?\n2. What does father do?\n3. What does mother do?"},
        {"title": "My School", "content": "I go to school every day. My school is big and beautiful. I have many friends. We study Chinese, Math and English. I like English best. My teachers are kind.\n\n1. How does the writer go to school?\n2. What subjects does the writer study?\n3. Which subject does the writer like best?"},
        {"title": "A Nice Day", "content": "Today is Sunday. The weather is fine. I go to the park with my parents. We fly a kite. The kite is high in the sky. We are very happy.\n\n1. What day is it today?\n2. How is the weather?\n3. Where do they go?"},
    ],
    "单词拼写": [
        {"title": "Word Spelling", "content": "一、补全单词\n1. b__k（书） 2. c__t（猫） 3. d__g（狗）\n\n二、用所给词的适当形式填空\n1. I ___ (be) a student.\n2. She ___ (have) a red bag.\n3. They ___ (go) to school."},
        {"title": "Vocabulary Test", "content": "一、写出对应词\n1. boy ___ 2. girl ___ 3. father ___\n\n二、英译汉\n1. apple ___ 2. banana ___ 3. orange ___\n\n三、汉译英\n1. 苹果___ 2. 香蕉___ 3. 橙子___"},
    ],
}

# ==================== 语文题库接口 ====================

def get_yuwen_from_bank(question_type, grade, count=20):
    """从题库获取语文题目（智能匹配 + 内置题库）"""
    grade_for_db = format_grade_for_db(grade)

    type_map = {
        "阅读理解": "yuedu",
        "古诗文默写": "gushi",
        "拼音练习": "pinyin",
        "汉字组词": "hanzi",
        "词语解释": "ciyu",
    }

    db_type = type_map.get(question_type, question_type)

    # 1. 尝试从数据库获取
    questions = get_yuwen_questions(q_type=db_type, grade=grade_for_db, count=count)
    if not questions:
        questions = get_yuwen_questions(q_type=db_type, count=count)
    if not questions:
        questions = get_yuwen_questions(grade=grade_for_db, count=count)
    if not questions:
        questions = get_yuwen_questions(count=count)

    # 2. 如果数据库为空，使用内置题库
    if not questions and question_type in BUILTIN_YUWEN:
        for item in BUILTIN_YUWEN[question_type]:
            questions.append({
                "question_type": question_type,
                "title": item["title"],
                "content": item["content"],
                "answer": ""
            })

    # 3. 如果还是为空且是其他题型，通用处理
    if not questions:
        questions.append({
            "question_type": question_type,
            "title": f"{grade}{question_type}",
            "content": f"这是一道{grade}{question_type}练习题。\n请认真完成以下问题：\n1. 第一题...\n2. 第二题...\n3. 第三题...",
            "answer": ""
        })

    result = []
    for q in questions[:count]:
        result.append({
            "type": q.get("question_type", question_type),
            "title": q.get("title", ""),
            "content": q.get("content", ""),
            "answer": q.get("answer", ""),
        })

    return result

# ==================== 英语题库接口 ====================

def get_yingyu_from_bank(question_type, grade, count=20):
    """从题库获取英语题目（智能匹配 + 内置题库）"""
    grade_for_db = format_grade_for_db(grade)

    type_map = {
        "阅读理解": "yuedu",
        "单词拼写": "danci",
        "单词连线": "danci",
        "单词填空": "danci",
        "语法练习": "yufa",
        "情景对话": "duihua",
    }

    db_type = type_map.get(question_type, question_type)

    # 1. 尝试从数据库获取
    questions = get_yingyu_questions(q_type=db_type, grade=grade_for_db, count=count)
    if not questions:
        questions = get_yingyu_questions(q_type=db_type, count=count)
    if not questions:
        questions = get_yingyu_questions(grade=grade_for_db, count=count)
    if not questions:
        questions = get_yingyu_questions(count=count)

    # 2. 如果数据库为空，使用内置题库
    if not questions and question_type in BUILTIN_YINGYU:
        for item in BUILTIN_YINGYU[question_type]:
            questions.append({
                "question_type": question_type,
                "title": item["title"],
                "content": item["content"],
                "answer": ""
            })

    # 3. 如果还是为空
    if not questions:
        questions.append({
            "question_type": question_type,
            "title": f"{grade}{question_type}",
            "content": f"This is a {question_type} exercise for {grade}.\n\n1. Question one...\n2. Question two...\n3. Question three...",
            "answer": ""
        })

    result = []
    for q in questions[:count]:
        result.append({
            "type": q.get("question_type", question_type),
            "title": q.get("title", ""),
            "content": q.get("content", ""),
            "answer": q.get("answer", ""),
            "options": q.get("options"),
        })

    return result

# ==================== 其他接口保持不变 ====================

def generate_yuwen_with_bank(question_type, grade, count=20, bank_ratio=0.5):
    bank_count = int(count * bank_ratio)
    gen_count = count - bank_count
    results = []
    if bank_count > 0:
        bank_questions = get_yuwen_from_bank(question_type, grade, bank_count)
        results.extend(bank_questions)
    if gen_count > 0:
        results.extend([{"type": question_type, "content": f"[生成] {question_type}", "answer": ""} for _ in range(gen_count)])
    random.shuffle(results)
    return results[:count]

def generate_yuwen_fallback(question_type, grade, count):
    return [{"type": question_type, "content": f"[自动生成] {question_type} 题目", "answer": ""} for _ in range(count)]

def generate_yingyu_with_bank(question_type, grade, count=20, bank_ratio=0.5):
    if grade not in ENGLISH_GRADES:
        return []
    bank_count = int(count * bank_ratio)
    gen_count = count - bank_count
    results = []
    if bank_count > 0:
        bank_questions = get_yingyu_from_bank(question_type, grade, bank_count)
        results.extend(bank_questions)
    if gen_count > 0:
        results.extend([{"type": question_type, "content": f"[Generated] {question_type}", "answer": ""} for _ in range(gen_count)])
    random.shuffle(results)
    return results[:count]

def generate_yingyu_fallback(question_type, grade, count):
    return [{"type": question_type, "content": f"[Auto] {question_type}", "answer": ""} for _ in range(count)]

def get_shuxue_from_bank(q_type, grade, count=10):
    grade_num = GRADE_NUM.get(grade, "3")
    questions = get_shuxue_questions(q_type=q_type, grade=grade_num, count=count)
    result = []
    for q in questions:
        result.append((q["question_type"], q["question"], q["answer"]))
    return result

def get_spider_questions(grade, q_types=None, count=10):
    type_map = {
        "cb_age": "age", "cb_tree": "tree", "cb_chicken_rabbit": "chicken_rabbit",
        "cb_sum_diff": "sum_diff", "cb_project": "project", "cb_form": "form",
        "cb_concentration": "concentration", "cb_find_rule": "find_rule", "cb_logic": "logic",
    }
    results = []
    if q_types:
        for qt in q_types:
            db_type = type_map.get(qt)
            if db_type:
                questions = get_shuxue_from_bank(db_type, grade, count // len(q_types))
                results.extend(questions)
    else:
        questions = get_shuxue_questions(grade=GRADE_NUM.get(grade, "3"), count=count)
        for q in questions:
            results.append((q["question_type"], q["question"], q["answer"]))
    random.shuffle(results)
    return results[:count]

def get_bank_status():
    stats = get_db_stats()
    has_data = stats["yuwen"] > 0 or stats["yingyu"] > 0 or stats["shuxue"] > 0
    return {
        "has_data": has_data,
        "yuwen_count": stats["yuwen"],
        "yingyu_count": stats["yingyu"],
        "shuxue_count": stats["shuxue"],
        "total": stats["total"],
        "status": "已爬取" if has_data else "待爬取"
    }

def is_bank_ready():
    return get_db_stats()["total"] > 0
