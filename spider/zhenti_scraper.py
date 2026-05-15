# spider/zhenti_scraper.py - 多平台真题试卷搜索爬虫
import asyncio
import re
from playwright.async_api import async_playwright
from typing import List, Dict, Callable, Optional


class PaperSearcher:
    """多平台试卷搜索器"""
    
    # 各平台的搜索URL模板
    SEARCH_URLS = {
        "shijuan1": {
            "name": "第一试卷网",
            "base": "https://www.shijuan1.com",
            "subjects": {
                "yuwen": "/a/sjyw", "shuxue": "/a/sjsx", "yingyu": "/a/sjyy",
                "kexue": "/a/sjkx", "daode": "/a/sjdd", "wuli": "/a/sjwl",
                "huaxue": "/a/sjhx", "lishi": "/a/sjls"
            },
            "grades": {"1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6",
                      "7": "7", "8": "8", "9": "9"}
        },
        "szxuexiao": {
            "name": "中小学试卷网",
            "base": "https://appsj.szxuexiao.com",
            "search_url": "/search?q={keyword}"
        },
        "yishijuan": {
            "name": "新一试卷",
            "base": "https://www.yishijuan.com",
            "subjects": {
                "yuwen": "/yuanchuang/yw", "shuxue": "/yuanchuang/sx", "yingyu": "/yuanchuang/yy",
                "wuli": "/yuanchuang/wl", "huaxue": "/yuanchuang/hx", "lishi": "/yuanchuang/ls"
            }
        }
    }
    
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.playwright = None
    
    async def init_browser(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            channel="msedge"
        )
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def search_shijuan1(self, subject: str, grade: str, year: str, 
                              keyword: str, progress_callback: Optional[Callable] = None,
                              result_callback: Optional[Callable] = None) -> List[Dict]:
        """搜索第一试卷网 - 并发爬取优化版（保持顺序）"""
        results = []
        seen_urls = set()
        results_lock = asyncio.Lock()
        
        config = self.SEARCH_URLS["shijuan1"]
        base = config["base"]
        
        subject_paths = {
            "yuwen": "sjyw", "shuxue": "sjsx", "yingyu": "sjyy",
            "kexue": "sjkx", "daode": "sjdd", "wuli": "sjwl",
            "huaxue": "sjhx", "lishi": "sjls"
        }
        subject_names = {
            "yuwen": "语文", "shuxue": "数学", "yingyu": "英语",
            "kexue": "科学", "daode": "道德与法治", "wuli": "物理",
            "huaxue": "化学", "lishi": "历史"
        }
        
        page_ids = {
            "yuwen": { "1": 106, "2": 107, "3": 108, "4": 109, "5": 110, "6": 111, "7": 121, "8": 122, "9": 123 },
            "shuxue": { "1": 112, "2": 113, "3": 114, "4": 115, "5": 116, "6": 117, "7": 118, "8": 119, "9": 120 },
            "yingyu": { "1": 604, "2": 605, "3": 606, "4": 607, "5": 608, "6": 609, "7": 610, "8": 611, "9": 612 },
            "wuli": { "7": 700, "8": 702, "9": 701 },
            "huaxue": { "7": 696, "8": 698, "9": 697 },
            "daode": { "7": 712, "8": 713, "9": 714 },
            "lishi": { "7": 734, "8": 735, "9": 736 },
            "kexue": { "7": 751, "8": 752, "9": 753 }
        }
        
        grade_display = {
            "初一": "初一/七年级", "初二": "初二/八年级", "初三": "初三/九年级",
            "七年级": "初一/七年级", "八年级": "初二/八年级", "九年级": "初三/九年级",
            "一年级": "一年级", "二年级": "二年级", "三年级": "三年级",
            "四年级": "四年级", "五年级": "五年级", "六年级": "六年级",
            "高一": "高一", "高二": "高二", "高三": "高三"
        }
        
        MAX_PAGES_PER_GRADE = 15
        
        subjects_to_crawl = []
        if subject and subject in subject_paths:
            subjects_to_crawl = [(subject, subject_paths[subject], subject_names[subject])]
        else:
            for sk, sp in subject_paths.items():
                subjects_to_crawl.append((sk, sp, subject_names.get(sk, "")))
        
        grades_to_crawl = []
        if grade:
            grades_to_crawl = [grade]
        else:
            grades_to_crawl = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        
        # 生成所有页面的URL，记录顺序key
        tasks_to_crawl = []
        order_counter = 0
        for subj_key, subj_path, subj_name in subjects_to_crawl:
            for g in grades_to_crawl:
                first_page_url = f"{base}/a/{subj_path}{g}/"
                tasks_to_crawl.append((order_counter, subj_key, subj_path, subj_name, g, first_page_url, 1))
                order_counter += 1
                
                subj_page_ids = page_ids.get(subj_key, {})
                if g in subj_page_ids:
                    page_id = subj_page_ids[g]
                    for page_num in range(2, MAX_PAGES_PER_GRADE + 1):
                        page_url = f"{base}/a/{subj_path}{g}/list_{page_id}_{page_num}.html"
                        tasks_to_crawl.append((order_counter, subj_key, subj_path, subj_name, g, page_url, page_num))
                        order_counter += 1
        
        if progress_callback:
            progress_callback(f"🚀 第一试卷网: 共 {len(tasks_to_crawl)} 个页面待爬...")
        
        # 单个页面爬取函数
        async def crawl_single_page(order_key, subj_key, subj_path, subj_name, g, page_url, page_num):
            page_results = []
            p = await self.browser.new_page()
            p.set_default_timeout(8000)
            
            try:
                await p.goto(page_url, wait_until="domcontentloaded", timeout=8000)
                
                links = await p.query_selector_all("a")
                
                for el in links:
                    try:
                        href = await el.get_attribute("href")
                        text = await el.inner_text()
                        
                        if not href or not text:
                            continue
                        
                        if not re.match(r'/a/sj\w+\d+/\d+\.html', href):
                            continue
                        
                        title = text.strip()
                        
                        if len(title) < 8:
                            continue
                        if any(x in title for x in ["语文试卷", "数学试卷", "英语试卷", "科学试卷"]):
                            continue
                        
                        if year and year not in title:
                            continue
                        
                        if keyword and keyword not in title:
                            continue
                        
                        grade_match = re.search(r'(初一|初二|初三|高一|高二|高三|[一二三四五六七八九]年级)', title)
                        if grade_match:
                            grade_text = grade_display.get(grade_match.group(1), grade_match.group(1))
                        else:
                            grade_text = f"年级{g}"
                        
                        full_url = base + href
                        
                        async with results_lock:
                            if full_url not in seen_urls:
                                seen_urls.add(full_url)
                                item = {
                                    "platform": "第一试卷网",
                                    "title": title[:80],
                                    "subject": subj_name,
                                    "grade": grade_text,
                                    "url": full_url,
                                    "_order_key": order_key
                                }
                                results.append(item)
                                
                                if result_callback:
                                    result_callback(item)
                                
                    except:
                        continue
                        
            except:
                pass
            finally:
                await p.close()
            
            return page_results
        
        # 并发控制：最多6个页面同时爬取
        semaphore = asyncio.Semaphore(6)
        
        async def crawl_with_limit(order_key, subj_key, subj_path, subj_name, g, page_url, page_num):
            async with semaphore:
                if progress_callback:
                    progress_callback(f"📄 [{subj_name}年级{g}] 第{page_num}/15页... {len(results)}个")
                await crawl_single_page(order_key, subj_key, subj_path, subj_name, g, page_url, page_num)
        
        # 创建所有并发任务
        tasks = [crawl_with_limit(*task) for task in tasks_to_crawl]
        
        # 并行执行
        await asyncio.gather(*tasks)
        
        # 按原始顺序排序
        results.sort(key=lambda x: x["_order_key"])
        # 移除排序key
        for item in results:
            item.pop("_order_key", None)
        
        if progress_callback:
            progress_callback(f"✅ 第一试卷网完成，共 {len(results)} 个结果")
        
        return results
    
    async def search_yishijuan(self, subject: str, grade: str, year: str,
                               keyword: str, progress_callback: Optional[Callable] = None,
                               result_callback: Optional[Callable] = None) -> List[Dict]:
        """搜索新一试卷"""
        results = []
        config = self.SEARCH_URLS["yishijuan"]
        
        # 学科映射
        subject_map = {
            "yuwen": "语文", "shuxue": "数学", "yingyu": "英语",
            "wuli": "物理", "huaxue": "化学", "lishi": "历史"
        }
        
        # 年级中文映射
        grade_chinese = {
            "7": "七年级", "8": "八年级", "9": "九年级",
            "10": "高一", "11": "高二", "12": "高三"
        }
        
        # 组合关键词
        search_kw = keyword or ""
        if subject:
            search_kw = subject_map.get(subject, subject) + " " + search_kw
        if grade:
            search_kw += f" {grade_chinese.get(grade, '')}"
        if year:
            search_kw += f" {year}"
        
        # 如果没有有效关键词，使用默认搜索词
        if not search_kw.strip():
            search_kw = "试卷"
        
        if progress_callback:
            progress_callback(f"正在搜索新一试卷: {search_kw.strip()}...")
        
        page = await self.browser.new_page()
        page.set_default_timeout(45000)
        
        try:
            # 新一试卷搜索URL
            search_terms = search_kw.strip()
            search_url = f"{config['base']}/search?q={search_terms}"
            
            await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            # 滚动页面触发懒加载
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(1)
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(1)
            
            # 查找试卷链接
            links = await page.query_selector_all("a")
            
            seen_urls = set()
            for el in links:
                try:
                    href = await el.get_attribute("href")
                    text = await el.inner_text()
                    
                    if not href or not text:
                        continue
                    
                    title = text.strip()
                    
                    # 过滤无效标题
                    if len(title) < 8:
                        continue
                    if any(x in title for x in ["备案", "Copyright", "收藏", "登录", "注册", "关于", "帮助", "http", "javascript"]):
                        continue
                    
                    # 筛选新一试卷内部链接
                    if ".yishijuan.com" not in href and not href.startswith("/"):
                        continue
                    
                    # 构建完整URL
                    if href.startswith("/"):
                        full_url = config["base"] + href
                    elif href.startswith("http"):
                        full_url = href
                    else:
                        full_url = config["base"] + "/" + href
                    
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)
                    
                    # 按年份筛选
                    if year and year not in title:
                        continue
                    
                    # 提取学科
                    subject_text = "综合"
                    if subject:
                        subject_text = subject_map.get(subject, "综合")
                    else:
                        for subj_key, subj_name in subject_map.items():
                            if subj_name in title:
                                subject_text = subj_name
                                break
                    
                    # 提取年级
                    grade_match = re.search(r'(初一|初二|初三|高一|高二|高三|[一二三四五六七八九]年级|\d+年级)', title)
                    if grade_match:
                        raw_grade = grade_match.group(1)
                        grade_display = {
                            "初一": "初一/七年级", "初二": "初二/八年级", "初三": "初三/九年级",
                            "七年级": "初一/七年级", "八年级": "初二/八年级", "九年级": "初三/九年级",
                            "高一": "高一", "高二": "高二", "高三": "高三"
                        }
                        grade_text = grade_display.get(raw_grade, raw_grade)
                    else:
                        grade_text = "全部"
                    
                    result_item = {
                        "platform": "新一试卷",
                        "title": title[:100],
                        "subject": subject_text,
                        "grade": grade_text,
                        "url": full_url
                    }
                    results.append(result_item)
                    
                    # 实时回调
                    if result_callback:
                        result_callback(result_item)
                        
                except Exception as e:
                    continue
            
            if progress_callback:
                progress_callback(f"新一试卷: 找到 {len(results)} 个结果")
                    
        except Exception as e:
            if progress_callback:
                progress_callback(f"新一试卷出错: {e}")
        finally:
            await page.close()
        
        return results
    
    async def search_szxuexiao(self, subject: str, grade: str, year: str,
                               keyword: str, progress_callback: Optional[Callable] = None,
                               result_callback: Optional[Callable] = None) -> List[Dict]:
        """搜索中小学试卷网 - 高速并发爬取，每年级60页，边爬边显示"""
        
        base_url = self.SEARCH_URLS["szxuexiao"]["base"]
        results = []
        seen_urls = set()
        results_lock = asyncio.Lock()
        
        # 年级URL映射（拼音格式）
        grade_urls = {
            "1": ("yinianji", "一年级"),
            "2": ("ernianji", "二年级"),
            "3": ("sannianji", "三年级"),
            "4": ("sinianji", "四年级"),
            "5": ("wunianji", "五年级"),
            "6": ("liunianji", "六年级"),
            "7": ("qinianji", "七年级/初一"),
            "8": ("banianji", "八年级/初二"),
            "9": ("jiunianji", "九年级/初三"),
            "10": ("gaoyi", "高一"),
            "11": ("gaoer", "高二"),
            "12": ("gaosan", "高三"),
        }
        
        async def crawl_page(grade_pinyin: str, grade_name: str, page_num: int):
            """爬取单个页面，立即发送结果"""
            # 构建URL
            if page_num == 1:
                url = f"{base_url}/{grade_pinyin}/index.html"
            else:
                url = f"{base_url}/{grade_pinyin}/index_{page_num}.html"
            
            p = await self.browser.new_page()
            p.set_default_timeout(12000)
            
            try:
                await p.goto(url, wait_until="domcontentloaded")
                
                links = await p.query_selector_all("a")
                
                for el in links:
                    try:
                        href = await el.get_attribute("href")
                        text = await el.inner_text()
                        
                        if not href or not text:
                            continue
                        
                        title = text.strip()
                        
                        # 过滤条件
                        if len(title) < 8:
                            continue
                        if any(x in title for x in [
                            "备案", "Copyright", "http://", "javascript:", "#",
                            "登录", "注册", "找回", "关于", "联系",
                            "网站首页", "查看所有", "上一页", "下一页",
                            "Previous", "Next", "page",
                            "小学试卷网", "中小学试卷网", "城市学校网", "精品资源网",
                            "粤ICP备", "京ICP备", "沪ICP备", "浙ICP备", "ICP备",
                            "人教", "部编", "统编",
                            "一年级上", "一年级下", "二年级上", "二年级下",
                            "三年级上", "三年级下", "四年级上", "四年级下",
                            "五年级上", "五年级下", "六年级上", "六年级下",
                        ]):
                            continue
                        
                        # 必须包含试卷关键词
                        if not any(x in title for x in ["试卷", "试题", "考试", "测试", "练习", "真题", "模拟", "期中", "期末", "单元"]):
                            continue
                        
                        # 构建完整URL
                        if href.startswith("http"):
                            full_url = href
                        elif href.startswith("/"):
                            full_url = base_url + href
                        else:
                            full_url = base_url + "/" + href
                        
                        # 年份筛选
                        if year and year not in title:
                            continue
                        
                        # 关键词筛选
                        if keyword and keyword not in title:
                            continue
                        
                        # 提取学科
                        subject_text = "综合"
                        for kw, subj in [("语文", "语文"), ("数学", "数学"), ("英语", "英语"), 
                                        ("科学", "科学"), ("物理", "物理"), ("化学", "化学"), 
                                        ("历史", "历史"), ("道法", "道德与法治")]:
                            if kw in title:
                                subject_text = subj
                                break
                        
                        # 线程安全地添加结果
                        async with results_lock:
                            if full_url not in seen_urls:
                                seen_urls.add(full_url)
                                item = {
                                    "platform": "中小学试卷网",
                                    "title": title[:100],
                                    "subject": subject_text,
                                    "grade": grade_name,
                                    "url": full_url
                                }
                                results.append(item)
                                # 立即回调，实时显示
                                if result_callback:
                                    result_callback(item)
                                
                    except:
                        continue
                        
            except:
                pass
            finally:
                await p.close()
        
        # 确定要爬取的年级
        grades_to_crawl = []
        if grade and grade in grade_urls:
            pinyin, name = grade_urls[grade]
            grades_to_crawl = [(grade, pinyin, name)]
        else:
            for gk, (pinyin, name) in grade_urls.items():
                grades_to_crawl.append((gk, pinyin, name))
        
        if progress_callback:
            progress_callback(f"🚀 开始爬取 {len(grades_to_crawl)} 个年级，每年级60页...")
        
        # 构建所有页面的爬取任务
        all_tasks = []
        for grade_key, grade_pinyin, grade_name in grades_to_crawl:
            for page_num in range(1, 61):  # 60页
                all_tasks.append((grade_pinyin, grade_name, page_num))
        
        # 全局并发控制：最多15个页面同时爬
        semaphore = asyncio.Semaphore(15)
        
        async def crawl_with_progress(gp, gn, pn):
            async with semaphore:
                if progress_callback:
                    progress_callback(f"[{gn}] 第{pn}/60页... 已找到 {len(results)} 个")
                await crawl_page(gp, gn, pn)
        
        # 创建所有任务
        tasks = [crawl_with_progress(gp, gn, pn) for gp, gn, pn in all_tasks]
        
        # 使用 as_completed 边完成边处理，实现实时显示
        for coro in asyncio.as_completed(tasks):
            await coro
        
        if progress_callback:
            progress_callback(f"✅ 中小学试卷网完成，共 {len(results)} 个结果")
        
        return results


async def search_papers(platform: str, subject: str, grade: str, year: str,
                        keyword: str, progress_callback: Optional[Callable] = None,
                        result_callback: Optional[Callable] = None) -> List[Dict]:
    """
    搜索真题试卷 - 平台并行爬取
    
    Args:
        platform: 平台URL，空则搜索所有
        subject: 学科
        grade: 年级
        year: 年份
        keyword: 关键词
        progress_callback: 进度回调函数
        result_callback: 每找到一条结果就回调（实时显示用）
    
    Returns:
        试卷列表
    """
    results = []
    results_lock = asyncio.Lock()
    
    searcher = PaperSearcher(headless=True)
    
    try:
        await searcher.init_browser()
        
        # 平台映射
        platform_map = {
            "https://www.shijuan1.com": "shijuan1",
            "https://appsj.szxuexiao.com": "szxuexiao",
            "https://www.yishijuan.com": "yishijuan"
        }
        
        # 确定要搜索的平台
        platforms_to_search = [platform_map[platform]] if platform in platform_map else []
        
        # 包装函数，统一处理结果和回调
        async def search_platform(p_name):
            platform_results = []
            
            try:
                if p_name == "shijuan1":
                    platform_results = await searcher.search_shijuan1(
                        subject, grade, year, keyword, progress_callback, result_callback
                    )
                elif p_name == "szxuexiao":
                    platform_results = await searcher.search_szxuexiao(
                        subject, grade, year, keyword, progress_callback, result_callback
                    )
                elif p_name == "yishijuan":
                    platform_results = await searcher.search_yishijuan(
                        subject, grade, year, keyword, progress_callback, result_callback
                    )
            except Exception as e:
                if progress_callback:
                    progress_callback(f"⚠️ {p_name} 爬取出错: {e}")
            
            return platform_results
        
        # 搜索选定的平台
        platform_results = await asyncio.gather(*[
            search_platform(p) for p in platforms_to_search
        ])
        
        # 合并结果
        for pr in platform_results:
            results.extend(pr)
        
        # 去重（已经在各平台内去重了，这里简单处理）
        return results
        
    finally:
        await searcher.close()
