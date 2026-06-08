# zhenti_core.py - 真题试卷搜索核心模块
# 使用 Scrapling 智能爬虫框架（反反爬虫）

import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass, field


# ══════════════════════════════════════════════════════════
#  数据库模块
# ══════════════════════════════════════════════════════════

DB_PATH = Path(__file__).parent / "question_bank.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS yuwen_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_type TEXT NOT NULL,
                grade TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                answer TEXT,
                source_url TEXT,
                source_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS yingyu_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_type TEXT NOT NULL,
                grade TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                answer TEXT,
                options TEXT,
                source_url TEXT,
                source_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shuxue_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_type TEXT NOT NULL,
                grade TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                answer TEXT,
                source_url TEXT,
                source_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_db_stats():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        stats = {}
        for table in ["yuwen_questions", "yingyu_questions", "shuxue_questions"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        return stats
    finally:
        conn.close()

def add_question(table, question_type, grade, content, title=None, answer=None,
                 options=None, source_url=None, source_name=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if table == "yingyu_questions":
            cursor.execute(
                f"INSERT INTO {table} (question_type, grade, title, content, answer, options, source_url, source_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (question_type, grade, title, content, answer, options, source_url, source_name)
            )
        else:
            cursor.execute(
                f"INSERT INTO {table} (question_type, grade, title, content, answer, source_url, source_name) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (question_type, grade, title, content, answer, source_url, source_name)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def add_yuwen_question(question_type, grade, content, **kwargs):
    add_question("yuwen_questions", question_type, grade, content, **kwargs)

def add_yingyu_question(question_type, grade, content, **kwargs):
    add_question("yingyu_questions", question_type, grade, content, **kwargs)

def add_shuxue_question(question_type, grade, content, **kwargs):
    add_question("shuxue_questions", question_type, grade, content, **kwargs)

def get_questions(table, grade=None, question_type=None, limit=50):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = f"SELECT * FROM {table} WHERE 1=1"
        params = []
        if grade:
            query += " AND grade = ?"
            params.append(grade)
        if question_type:
            query += " AND question_type = ?"
            params.append(question_type)
        query += f" ORDER BY RANDOM() LIMIT {limit}"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_yuwen_questions(grade=None, question_type=None, limit=50):
    return get_questions("yuwen_questions", grade, question_type, limit)

def get_yingyu_questions(grade=None, question_type=None, limit=50):
    return get_questions("yingyu_questions", grade, question_type, limit)

def get_shuxue_questions(grade=None, question_type=None, limit=50):
    return get_questions("shuxue_questions", grade, question_type, limit)


# ══════════════════════════════════════════════════════════
#  集成模块
# ══════════════════════════════════════════════════════════

GRADE_NUM = {
    "一年级": "1", "二年级": "2", "三年级": "3",
    "四年级": "4", "五年级": "5", "六年级": "6"
}

GRADE_NUM_REVERSE = {v: k for k, v in GRADE_NUM.items()}

def format_grade_for_db(grade):
    if not grade:
        return None
    if "年级" in grade:
        return grade
    if grade.isdigit():
        return f"{grade}年级"
    return GRADE_NUM.get(grade, grade)

def get_yuwen_from_bank(grade, q_type=None, count=10):
    return get_yuwen_questions(grade=format_grade_for_db(grade), question_type=q_type, limit=count)

def get_yingyu_from_bank(grade, q_type=None, count=10):
    return get_yingyu_questions(grade=format_grade_for_db(grade), question_type=q_type, limit=count)

def get_spider_questions(grade, q_types=None, count=10):
    return get_shuxue_questions(grade=format_grade_for_db(grade), limit=count)

def get_bank_status():
    return get_db_stats()

def is_bank_ready():
    return any(v > 0 for v in get_db_stats().values())


# ══════════════════════════════════════════════════════════
#  爬虫模块 (使用 Scrapling)
# ══════════════════════════════════════════════════════════

@dataclass
class PlatformConfig:
    """平台配置"""
    name: str                           # 平台名称
    base_url: str                       # 基础URL
    link_pattern: str                   # 链接正则模式
    grade_map: Dict[str, tuple]         # 年级 -> (url_path, display_name)
    subject_map: Dict[str, tuple] = field(default_factory=dict)  # 学科 -> (url_path, display_name)
    min_title_len: int = 8              # 标题最小长度
    exclude_keywords: List[str] = field(default_factory=lambda: ["语文试卷", "数学试卷", "英语试卷"])
    grade_display: Dict[str, str] = field(default_factory=dict)  # 年级显示映射


# 平台配置
PLATFORM_CONFIGS = {
    "shijuan1": PlatformConfig(
        name="第一试卷网",
        base_url="https://www.shijuan1.com",
        link_pattern=r'<a[^>]+href="(/a/sj\w+/\d+\.html)"[^>]*>(.*?)</a>',
        grade_map={
            "1": ("a/sjyw1", "一年级"), "2": ("a/sjyw2", "二年级"), "3": ("a/sjyw3", "三年级"),
            "4": ("a/sjyw4", "四年级"), "5": ("a/sjyw5", "五年级"), "6": ("a/sjyw6", "六年级"),
            "7": ("a/sjyw7", "七年级"), "8": ("a/sjyw8", "八年级"), "9": ("a/sjyw9", "九年级"),
            "10": ("a/sjywg1", "高一"), "11": ("a/sjywg2", "高二"), "12": ("a/sjywg3", "高三"),
        },
        grade_display={
            "初一": "七年级", "初二": "八年级", "初三": "九年级",
            "七年级": "七年级", "八年级": "八年级", "九年级": "九年级",
        },
    ),
    "szxuexiao": PlatformConfig(
        name="中小学试卷网",
        base_url="https://appsj.szxuexiao.com",
        link_pattern=r'<a[^>]+href="([^"]+\.html)"[^>]*>(.*?)</a>',
        grade_map={
            "1": ("yinianji", "一年级"), "2": ("ernianji", "二年级"),
            "3": ("sannianji", "三年级"), "4": ("sinianji", "四年级"),
            "5": ("wunianji", "五年级"), "6": ("liunianji", "六年级"),
        },
        subject_map={"语文": "语文", "数学": "数学", "英语": "英语", "科学": "科学"},
        min_title_len=8,
        exclude_keywords=["备案", "Copyright", "http://", "javascript:", "登录", "注册",
                          "网站首页", "上一页", "下一页", "小学试卷网", "中小学试卷网",
                          "粤ICP备", "京ICP备", "沪ICP备", "浙ICP备", "人教", "部编", "统编"],
    ),
    "yishijuan": PlatformConfig(
        name="新一试卷",
        base_url="https://www.yishijuan.com",
        link_pattern=r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        grade_map={
            "1": ("xiaoxueshijuan", "一年级"), "2": ("xiaoxueshijuan", "二年级"),
            "3": ("xiaoxueshijuan", "三年级"), "4": ("xiaoxueshijuan", "四年级"),
            "5": ("xiaoxueshijuan", "五年级"), "6": ("xiaoxueshijuan", "六年级"),
            "7": ("chuzhongshijuan", "七年级"), "8": ("chuzhongshijuan", "八年级"),
            "9": ("chuzhongshijuan", "九年级"),
            "10": ("gaozhongshijuan", "高一"), "11": ("gaozhongshijuan", "高二"),
            "12": ("gaozhongshijuan", "高三"),
        },
        exclude_keywords=["备案", "Copyright", "收藏", "登录", "注册", "关于", "帮助", "javascript"],
    ),
    "shijuan_net": PlatformConfig(
        name="试卷网",
        base_url="https://www.shijuan.net",
        link_pattern=r'<a[^>]+href="([^"]+\.html)"[^>]*>(.*?)</a>',
        grade_map={
            "1": ("yinianji", "一年级"), "2": ("ernianji", "二年级"),
            "3": ("sannianji", "三年级"), "4": ("sinianji", "四年级"),
            "5": ("wunianji", "五年级"), "6": ("liunianji", "六年级"),
            "7": ("qinianji", "七年级"), "8": ("banianji", "八年级"),
            "9": ("jiunianji", "九年级"),
        },
        min_title_len=5,
    ),
    "xbjy": PlatformConfig(
        name="心标教育",
        base_url="https://www.xbjy.com",
        link_pattern=r'<a[^>]+href="(/xhtml/[^"]+\.html)"[^>]*>(.*?)</a>',
        grade_map={
            "1": {"yuwen": "/ynjyw/", "shuxue": "/ynjsxs/"},
            "2": {"yuwen": "/enjyw/", "shuxue": "/enjsxs/"},
            "3": {"yuwen": "/snjywsc/", "shuxue": "/snjsxs/"},
            "4": {"yuwen": "/fnjywsc/", "shuxue": "/fnjsxs/"},
            "5": {"yuwen": "/wnjywsc/", "shuxue": "/wnjsxs/"},
            "6": {"yuwen": "/lnjywsc/", "shuxue": "/lnjsxs/"},
        },
        subject_map={"yuwen": "语文", "shuxue": "数学"},
        min_title_len=10,
    ),
}


class ScraplingScraper:
    """使用 Scrapling 的智能爬虫"""

    def __init__(self):
        self.fetcher = None

    def _safe_get(self, url, timeout=15):
        """安全抓取页面，返回 (html, error)"""
        try:
            import requests
            response = requests.get(url, timeout=timeout, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            if response.status_code == 200:
                content = response.content
                for enc in ['utf-8', 'gb2312', 'gbk', 'gb18030']:
                    try:
                        html = content.decode(enc)
                        if 'html' in html.lower() or 'title' in html.lower():
                            return html, None
                    except Exception:
                        continue
                return content.decode('utf-8', errors='ignore'), None
            else:
                return None, f"HTTP {response.status_code}"
        except Exception as e:
            return None, str(e)

    def _extract_links(self, html, pattern, base_url):
        """从HTML中提取链接"""
        links = []
        for match in re.finditer(pattern, html, re.DOTALL):
            href = match.group(1)
            text = match.group(2) if len(match.groups()) > 1 else ""
            title = re.sub(r'<[^>]+>', '', text).strip()

            # 构建完整URL
            if href.startswith("/"):
                full_url = base_url + href
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = base_url + "/" + href

            links.append((full_url, title))
        return links

    def _filter_title(self, title, config, year="", keyword=""):
        """过滤标题"""
        if not title or len(title) < config.min_title_len:
            return None
        if any(x in title for x in config.exclude_keywords):
            return None
        if year and year not in title:
            return None
        if keyword and keyword not in title:
            return None
        return title

    def _identify_grade(self, title, url_grade, config):
        """识别年级"""
        # 从标题中识别
        grade_patterns = r'(初一|初二|初三|[一二三四五六七八九]年级|高一|高二|高三)'
        match = re.search(grade_patterns, title)
        if match:
            grade_text = match.group(1)
            return config.grade_display.get(grade_text, grade_text)

        # 从URL参数推断
        if url_grade.startswith('g'):
            return f"高{url_grade[1:]}"
        elif url_grade.isdigit():
            grade_names = {"1": "一年级", "2": "二年级", "3": "三年级",
                          "4": "四年级", "5": "五年级", "6": "六年级",
                          "7": "七年级", "8": "八年级", "9": "九年级"}
            return grade_names.get(url_grade, f"{url_grade}年级")
        return url_grade

    def _search_generic(self, platform_key, subject="", grade="", year="", keyword="",
                       result_callback=None, stop_event=None, progress_callback=None) -> List[Dict]:
        """通用搜索方法"""
        config = PLATFORM_CONFIGS.get(platform_key)
        if not config:
            return []

        results = []
        seen_urls = set()

        # 确定要爬取的年级
        grades_to_crawl = []
        if grade:
            if grade in config.grade_map:
                grades_to_crawl = [grade]
            else:
                return results  # 指定年级不在支持范围内
        else:
            grades_to_crawl = list(config.grade_map.keys())

        if progress_callback:
            progress_callback(f"{config.name}: 开始搜索...")

        for grade_key in grades_to_crawl:
            if stop_event and stop_event.is_set():
                break

            grade_info = config.grade_map[grade_key]

            # 处理不同的配置格式
            if isinstance(grade_info, tuple):
                url_path, grade_name = grade_info
                urls_to_crawl = [(grade_name, grade_key, f"{config.base_url}/{url_path}/")]
            elif isinstance(grade_info, dict):
                # xbjy 格式：{subject: url_path}
                grade_name = f"{grade_key}年级"
                urls_to_crawl = []
                for subj_key, subj_path in grade_info.items():
                    if subject:
                        subj_display = config.subject_map.get(subj_key, "")
                        if subj_display != subject:
                            continue
                    urls_to_crawl.append((grade_name, grade_key, f"{config.base_url}{subj_path}"))
            else:
                continue

            for grade_name, g, url in urls_to_crawl:
                if stop_event and stop_event.is_set():
                    break

                html, error = self._safe_get(url)
                if error or html is None:
                    continue

                links = self._extract_links(html, config.link_pattern, config.base_url)

                for full_url, title in links:
                    try:
                        if stop_event and stop_event.is_set():
                            break

                        title = self._filter_title(title, config, year, keyword)
                        if not title:
                            continue

                        # 过滤无效链接
                        if not re.search(r'/\d+\.html$', full_url):
                            if platform_key not in ["yishijuan"]:
                                continue

                        if full_url in seen_urls:
                            continue
                        seen_urls.add(full_url)

                        # 确定学科
                        subject_text = self._detect_subject(title, subject, config)

                        # 确定年级
                        grade_text = self._identify_grade(title, g, config)

                        item = {
                            "platform": config.name,
                            "title": title[:100],
                            "subject": subject_text,
                            "grade": grade_text,
                            "url": full_url
                        }
                        results.append(item)
                        if result_callback:
                            result_callback(item)
                    except Exception:
                        continue

        if progress_callback:
            progress_callback(f"{config.name}完成，共 {len(results)} 个结果")

        return results

    def _detect_subject(self, title, requested_subject, config):
        """从标题中检测学科"""
        if requested_subject:
            return requested_subject

        subject_keywords = {
            "语文": "语文", "数学": "数学", "英语": "英语",
            "物理": "物理", "化学": "化学", "生物": "生物",
            "历史": "历史", "地理": "地理", "政治": "政治",
            "道德与法治": "道德与法治", "道法": "道德与法治",
            "科学": "科学",
        }
        for keyword, subject in subject_keywords.items():
            if keyword in title:
                return subject
        return "综合"

    def search_shijuan1(self, **kwargs):
        return self._search_generic("shijuan1", **kwargs)

    def search_szxuexiao(self, **kwargs):
        return self._search_generic("szxuexiao", **kwargs)

    def search_yishijuan(self, **kwargs):
        return self._search_generic("yishijuan", **kwargs)

    def search_shijuan_net(self, **kwargs):
        return self._search_generic("shijuan_net", **kwargs)

    def search_xbjy(self, **kwargs):
        return self._search_generic("xbjy", **kwargs)

    def get_download_info(self, url):
        """获取试卷的下载信息"""
        try:
            html, error = self._safe_get(url, timeout=15)
            if error or html is None:
                return {"type": "none", "url": "", "filename": "", "message": f"无法访问页面: {error}"}

            # 第一试卷网：直接下载链接
            if "shijuan1.com" in url:
                match = re.search(r'href="(/uploads/[^"]+\.(?:rar|zip|doc|docx|pdf|xls|xlsx))"', html, re.I)
                if match:
                    download_url = "https://www.shijuan1.com" + match.group(1)
                    filename = download_url.split("/")[-1]
                    return {"type": "direct", "url": download_url, "filename": filename,
                            "message": f"找到下载链接: {filename}"}

            # shijuan.net：网盘链接
            if "shijuan.net" in url:
                match = re.search(r'href="(https?://[^"]*lanzou[^"]*)"', html, re.I)
                if match:
                    return {"type": "cloud", "url": match.group(1), "filename": "",
                            "message": f"网盘链接: {match.group(1)}"}
                match = re.search(r'href="(https?://[^"]*(?:pan|yun|cloud|drive)[^"]*)"', html, re.I)
                if match:
                    return {"type": "cloud", "url": match.group(1), "filename": "",
                            "message": f"网盘链接: {match.group(1)}"}

            # 中小学试卷网
            if "szxuexiao" in url:
                match = re.search(r'href="([^"]*(?:download|file)[^"]*\.(?:rar|zip|doc|docx|pdf))"', html, re.I)
                if match:
                    download_url = match.group(1)
                    if not download_url.startswith("http"):
                        download_url = "https://appsj.szxuexiao.com" + download_url
                    filename = download_url.split("/")[-1]
                    return {"type": "direct", "url": download_url, "filename": filename,
                            "message": f"找到下载链接: {filename}"}

            return {"type": "none", "url": "", "filename": "", "message": "未找到下载链接"}

        except Exception as e:
            return {"type": "none", "url": "", "filename": "", "message": f"获取下载信息失败: {e}"}

    def download_file(self, url, save_dir, progress_callback=None):
        """下载文件到指定目录"""
        import requests
        try:
            import os
            from urllib.parse import urlparse, unquote

            if progress_callback:
                progress_callback("正在下载...")

            resp = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, stream=True)

            if resp.status_code != 200:
                return {"success": False, "filepath": "", "message": f"下载失败: HTTP {resp.status_code}"}

            filename = ""
            if 'Content-Disposition' in resp.headers:
                cd = resp.headers['Content-Disposition']
                match = re.search(r'filename[^;=\n]*=([\"\']?)([^;\"\']+)\1', cd)
                if match:
                    filename = unquote(match.group(2))

            if not filename:
                parsed = urlparse(url)
                filename = unquote(parsed.path.split("/")[-1])

            if not filename:
                filename = "download.rar"

            os.makedirs(save_dir, exist_ok=True)
            filepath = os.path.join(save_dir, filename)
            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return {"success": True, "filepath": filepath, "message": f"下载成功: {filename}"}

        except Exception as e:
            return {"success": False, "filepath": "", "message": f"下载失败: {e}"}


# 全局爬虫实例
_scraper = None

def _get_scraper():
    global _scraper
    if _scraper is None:
        _scraper = ScraplingScraper()
    return _scraper


def search_papers(platform, subject="", grade="", year="", keyword="",
                  result_callback=None, stop_event=None, progress_callback=None) -> List[Dict]:
    """搜索真题试卷"""
    scraper = _get_scraper()
    results = []

    platform_map = {
        "https://www.shijuan1.com": "shijuan1",
        "https://appsj.szxuexiao.com": "szxuexiao",
        "https://www.yishijuan.com": "yishijuan",
        "https://www.shijuan.net": "shijuan_net",
        "https://www.xbjy.com": "xbjy",
        "第一试卷网": "shijuan1",
        "中小学试卷网": "szxuexiao",
        "新一试卷": "yishijuan",
        "试卷网": "shijuan_net",
        "心标教育": "xbjy"
    }

    platform_key = platform_map.get(platform, platform)

    try:
        search_methods = {
            "shijuan1": scraper.search_shijuan1,
            "szxuexiao": scraper.search_szxuexiao,
            "yishijuan": scraper.search_yishijuan,
            "shijuan_net": scraper.search_shijuan_net,
            "xbjy": scraper.search_xbjy,
        }

        if platform_key:
            method = search_methods.get(platform_key)
            if method:
                results.extend(method(
                    subject=subject, grade=grade, year=year, keyword=keyword,
                    result_callback=result_callback, stop_event=stop_event,
                    progress_callback=progress_callback
                ))
        else:
            # 搜索所有平台
            for method in search_methods.values():
                results.extend(method(
                    subject=subject, grade=grade, year=year, keyword=keyword,
                    result_callback=result_callback, stop_event=stop_event,
                    progress_callback=progress_callback
                ))
    except Exception as e:
        if progress_callback:
            progress_callback(f"爬取出错: {e}")

    return results


# ══════════════════════════════════════════════════════════
#  兼容旧接口
# ══════════════════════════════════════════════════════════

class MultiPlatformScraper:
    """兼容旧接口的爬虫类"""

    def __init__(self, headless=True):
        self.scraper = ScraplingScraper()

    async def launch(self):
        pass

    async def search(self, platform, subject="", grade="", year="", keyword="", result_callback=None, stop_event=None):
        return search_papers(platform, subject, grade, year, keyword, result_callback, stop_event)

    async def close(self):
        pass
