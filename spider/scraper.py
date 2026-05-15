import asyncio
import re
from playwright.async_api import async_playwright


class PlatformScraper:
    def __init__(self, name, base_url):
        self.name = name
        self.base_url = base_url
        self.browser = None
        self.playwright = None
    
    async def launch(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            channel="msedge"
        )
    
    async def close(self):
        if self.browser:
            try:
                await self.browser.close(timeout=3000)
            except:
                pass
            self.browser = None
        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass
            self.playwright = None


class Shijuan1Scraper(PlatformScraper):
    SUBJECTS = {
        "yuwen": ("sjyw", "语文"),
        "shuxue": ("sjsx", "数学"),
        "yingyu": ("sjyy", "英语"),
        "wuli": ("sjwl", "物理"),
        "huaxue": ("sjhx", "化学"),
        "daode": ("sjzz", "政治"),
        "lishi": ("sjls", "历史"),
        "dili": ("sjdl", "地理"),
        "shengwu": ("sjsw", "生物")
    }
    
    PAGE_IDS = {
        "yuwen": {"1": 106, "2": 107, "3": 108, "4": 109, "5": 110, "6": 111, "7": 121, "8": 122, "9": 123},
        "shuxue": {"1": 112, "2": 113, "3": 114, "4": 115, "5": 116, "6": 117, "7": 118, "8": 119, "9": 120},
        "yingyu": {"1": 604, "2": 605, "3": 606, "4": 607, "5": 608, "6": 609, "7": 610, "8": 611, "9": 612},
        "wuli": {"8": 702, "9": 703},
        "huaxue": {"9": 704},
        "daode": {"7": 712, "8": 713, "9": 714},
        "lishi": {"7": 734, "8": 735, "9": 736},
        "dili": {"7": 737, "8": 738, "9": 739},
        "shengwu": {"7": 751, "8": 752}
    }
    
    SUBJECT_GRADE_MAP = {
        "wuli": ["8", "9"],
        "huaxue": ["9"],
        "lishi": ["7", "8", "9"],
        "dili": ["7", "8", "9"],
        "shengwu": ["7", "8"],
        "daode": ["7", "8", "9"],
        "yuwen": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "shuxue": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "yingyu": ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    }
    
    GRADE_DISPLAY = {
        "初一": "初一/七年级", "初二": "初二/八年级", "初三": "初三/九年级",
        "七年级": "初一/七年级", "八年级": "初二/八年级", "九年级": "初三/九年级",
        "一年级": "一年级", "二年级": "二年级", "三年级": "三年级",
        "四年级": "四年级", "五年级": "五年级", "六年级": "六年级"
    }
    
    def __init__(self):
        super().__init__("第一试卷网", "https://www.shijuan1.com")
    
    async def search(self, subject="", grade="", year="", keyword="", result_callback=None, stop_event=None):
        results = []
        seen_urls = set()
        last_result_time = None
        empty_page_count = 0
        max_empty_pages = 3
        
        subjects_to_crawl = []
        if subject and subject in self.SUBJECTS:
            subjects_to_crawl = [(subject, self.SUBJECTS[subject][0], self.SUBJECTS[subject][1])]
        else:
            for key, (path, name) in self.SUBJECTS.items():
                subjects_to_crawl.append((key, path, name))
        
        tasks = []
        for subj_key, subj_path, subj_name in subjects_to_crawl:
            valid_grades = self.SUBJECT_GRADE_MAP.get(subj_key, ["1", "2", "3", "4", "5", "6", "7", "8", "9"])
            
            if grade:
                if grade in valid_grades:
                    selected_grades = [grade]
                else:
                    continue
            else:
                selected_grades = valid_grades
            
            for g in selected_grades:
                first_url = f"{self.base_url}/a/{subj_path}{g}/"
                tasks.append((subj_name, g, first_url, 1))
                
                page_ids = self.PAGE_IDS.get(subj_key, {})
                if g in page_ids:
                    page_id = page_ids[g]
                    for page_num in range(2, 16):
                        url = f"{self.base_url}/a/{subj_path}{g}/list_{page_id}_{page_num}.html"
                        tasks.append((subj_name, g, url, page_num))
        
        for subj_name, g, url, page_num in tasks:
            if stop_event and stop_event.is_set():
                break
            
            if last_result_time is not None:
                elapsed = (asyncio.get_event_loop().time() - last_result_time)
                if elapsed > 5:
                    break
            
            if empty_page_count >= max_empty_pages:
                break
            
            page = await self.browser.new_page()
            page.set_default_timeout(8000)
            page_found_results = False
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=8000)
                
                if stop_event and stop_event.is_set():
                    break
                
                links = await page.query_selector_all("a")
                for el in links:
                    if stop_event and stop_event.is_set():
                        break
                    
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
                        if any(x in title for x in ["语文试卷", "数学试卷", "英语试卷"]):
                            continue
                        
                        if year and year not in title:
                            continue
                        if keyword and keyword not in title:
                            continue
                        
                        grade_match = re.search(r'(初一|初二|初三|[一二三四五六七八九]年级)', title)
                        if grade_match:
                            grade_text = self.GRADE_DISPLAY.get(grade_match.group(1), grade_match.group(1))
                        else:
                            grade_text = f"年级{g}"
                        
                        full_url = self.base_url + href
                        
                        if full_url not in seen_urls:
                            seen_urls.add(full_url)
                            item = {
                                "platform": self.name,
                                "title": title[:80],
                                "subject": subj_name,
                                "grade": grade_text,
                                "url": full_url
                            }
                            results.append(item)
                            page_found_results = True
                            last_result_time = asyncio.get_event_loop().time()
                            empty_page_count = 0
                            
                            if result_callback:
                                result_callback(item)
                            
                    except:
                        continue
            except:
                pass
            finally:
                await page.close()
            
            if not page_found_results:
                empty_page_count += 1
        
        return results


class SzxuexiaoScraper(PlatformScraper):
    GRADE_URLS = {
        "1": ("yinianji", "一年级"), "2": ("ernianji", "二年级"),
        "3": ("sannianji", "三年级"), "4": ("sinianji", "四年级"),
        "5": ("wunianji", "五年级"), "6": ("liunianji", "六年级")
    }
    
    def __init__(self):
        super().__init__("中小学试卷网", "https://appsj.szxuexiao.com")
    
    async def search(self, subject="", grade="", year="", keyword="", result_callback=None, stop_event=None):
        results = []
        seen_urls = set()
        
        grades_to_crawl = []
        if grade and grade in self.GRADE_URLS:
            pinyin, name = self.GRADE_URLS[grade]
            grades_to_crawl = [(grade, pinyin, name)]
        else:
            for gk, (pinyin, name) in self.GRADE_URLS.items():
                grades_to_crawl.append((gk, pinyin, name))
        
        subject_filters = {
            "语文": ["语文"],
            "数学": ["数学"],
            "英语": ["英语"],
            "科学": ["科学"]
        }
        
        selected_filter = subject_filters.get(subject, [])
        
        for grade_key, grade_pinyin, grade_name in grades_to_crawl:
            if stop_event and stop_event.is_set():
                break
            
            for page_num in range(1, 16):
                if stop_event and stop_event.is_set():
                    break
                
                page_url = f"{self.base_url}/{grade_pinyin}/index.html" if page_num == 1 else f"{self.base_url}/{grade_pinyin}/index_{page_num}.html"
                page = await self.browser.new_page()
                page.set_default_timeout(12000)
                
                try:
                    await page.goto(page_url, wait_until="domcontentloaded")
                    
                    if stop_event and stop_event.is_set():
                        break
                    
                    links = await page.query_selector_all("a")
                    for el in links:
                        if stop_event and stop_event.is_set():
                            break
                        
                        try:
                            href = await el.get_attribute("href")
                            text = await el.inner_text()
                            
                            if not href or not text:
                                continue
                            
                            title = text.strip()
                            
                            if len(title) < 8:
                                continue
                            if any(x in title for x in ["备案", "Copyright", "http://", "javascript:", "#", "登录", "注册", 
                                                        "网站首页", "上一页", "下一页", "小学试卷网", "中小学试卷网",
                                                        "粤ICP备", "京ICP备", "沪ICP备", "浙ICP备", "人教", "部编", "统编"]):
                                continue
                            if not any(x in title for x in ["试卷", "试题", "考试", "测试", "练习", "真题", "模拟", "期中", "期末", "单元"]):
                                continue
                            
                            if href.startswith("http"):
                                full_url = href
                            elif href.startswith("/"):
                                full_url = self.base_url + href
                            else:
                                full_url = self.base_url + "/" + href
                            
                            if year and year not in title:
                                continue
                            if keyword and keyword not in title:
                                continue
                            
                            subject_text = "综合"
                            found_subject = ""
                            for kw, subj in [("语文", "语文"), ("数学", "数学"), ("英语", "英语"), 
                                            ("科学", "科学"), ("物理", "物理"), ("化学", "化学"), 
                                            ("历史", "历史"), ("道法", "道德与法治"), ("生物", "生物"), ("地理", "地理")]:
                                if kw in title:
                                    subject_text = subj
                                    found_subject = kw
                                    break
                            
                            if selected_filter and found_subject not in selected_filter:
                                continue
                            
                            if full_url not in seen_urls:
                                seen_urls.add(full_url)
                                item = {
                                    "platform": self.name,
                                    "title": title[:100],
                                    "subject": subject_text,
                                    "grade": grade_name,
                                    "url": full_url
                                }
                                results.append(item)
                                
                                if result_callback:
                                    result_callback(item)
                                
                        except:
                            continue
                except:
                    pass
                finally:
                    await page.close()
        
        return results


class YishijuanScraper(PlatformScraper):
    PRIMARY_SUBJECT_MAP = {
        "yuwen": ("语文", 4),
        "shuxue": ("数学", 5),
        "yingyu": ("英语", 6),
        "kexue": ("科学", 27),
        "quanke": ("全科", 25)
    }
    
    JUNIOR_SUBJECT_MAP = {
        "yuwen": ("语文", 7),
        "shuxue": ("数学", 8),
        "yingyu": ("英语", 9),
        "wuli": ("物理", 10),
        "dili": ("地理", 11),
        "shengwu": ("生物", 12),
        "lishi": ("历史", 13),
        "huaxue": ("化学", 14),
        "daode": ("道德与法治", 15),
        "quanke": ("全科", 26)
    }
    
    GRADE_MAP = {
        "1": ("一年级", "xiaoxueshijuan"),
        "2": ("二年级", "xiaoxueshijuan"),
        "3": ("三年级", "xiaoxueshijuan"),
        "4": ("四年级", "xiaoxueshijuan"),
        "5": ("五年级", "xiaoxueshijuan"),
        "6": ("六年级", "xiaoxueshijuan"),
        "7": ("七年级", "chuzhongshijuan"),
        "8": ("八年级", "chuzhongshijuan"),
        "9": ("九年级", "chuzhongshijuan")
    }
    
    def __init__(self):
        super().__init__("新一试卷", "https://www.yishijuan.com")
    
    async def search(self, subject="", grade="", year="", keyword="", result_callback=None, stop_event=None):
        results = []
        seen_urls = set()
        last_result_time = None
        
        grades_to_crawl = []
        if grade and grade in self.GRADE_MAP:
            grades_to_crawl = [(grade, self.GRADE_MAP[grade][0], self.GRADE_MAP[grade][1])]
        else:
            for key, (name, prefix) in self.GRADE_MAP.items():
                grades_to_crawl.append((key, name, prefix))
        
        for grade_key, grade_name, prefix in grades_to_crawl:
            if stop_event and stop_event.is_set():
                break
            
            grade_int = int(grade_key)
            if grade_int <= 6:
                subject_map = self.PRIMARY_SUBJECT_MAP
            else:
                subject_map = self.JUNIOR_SUBJECT_MAP
            
            subjects_to_crawl = []
            if subject and subject in subject_map:
                subjects_to_crawl = [(subject, subject_map[subject][0], subject_map[subject][1])]
            else:
                for key, (name, catid) in subject_map.items():
                    subjects_to_crawl.append((key, name, catid))
            
            for subj_key, subj_name, catid in subjects_to_crawl:
                if stop_event and stop_event.is_set():
                    break
                
                for page_num in range(1, 16):
                    if stop_event and stop_event.is_set():
                        break
                    
                    if last_result_time is not None:
                        elapsed = (asyncio.get_event_loop().time() - last_result_time)
                        if elapsed > 4:
                            return results
                    
                    if page_num == 1:
                        url = f"{self.base_url}/{prefix}/search-htm-kw-{grade_name}-catid-{catid}.html"
                    else:
                        url = f"{self.base_url}/{prefix}/search-htm-kw-{grade_name}-catid-{catid}-page-{page_num}.html"
                    
                    page = await self.browser.new_page()
                    page.set_default_timeout(12000)
                    
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=12000)
                        
                        if stop_event and stop_event.is_set():
                            break
                        
                        links = await page.query_selector_all("a")
                        for el in links:
                            if stop_event and stop_event.is_set():
                                break
                            
                            try:
                                href = await el.get_attribute("href")
                                text = await el.inner_text()
                                
                                if not href or not text:
                                    continue
                                
                                title = text.strip()
                                
                                if len(title) < 8:
                                    continue
                                if any(x in title for x in ["备案", "Copyright", "收藏", "登录", "注册", "关于", "帮助", "http", "javascript"]):
                                    continue
                                
                                if ".yishijuan.com" not in href and not href.startswith("/"):
                                    continue
                                
                                if href.startswith("/"):
                                    full_url = self.base_url + href
                                elif href.startswith("http"):
                                    full_url = href
                                else:
                                    full_url = self.base_url + "/" + href
                                
                                if year and year not in title:
                                    continue
                                if keyword and keyword not in title:
                                    continue
                                
                                if full_url in seen_urls:
                                    continue
                                seen_urls.add(full_url)
                                
                                item = {
                                    "platform": self.name,
                                    "title": title[:100],
                                    "subject": subj_name,
                                    "grade": grade_name,
                                    "url": full_url
                                }
                                results.append(item)
                                last_result_time = asyncio.get_event_loop().time()
                                
                                if result_callback:
                                    result_callback(item)
                                
                            except:
                                continue
                    except:
                        pass
                    finally:
                        await page.close()
        
        return results


class MultiPlatformScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.scrapers = {}
    
    async def launch(self):
        self.scrapers["shijuan1"] = Shijuan1Scraper()
        self.scrapers["szxuexiao"] = SzxuexiaoScraper()
        self.scrapers["yishijuan"] = YishijuanScraper()
        
        for scraper in self.scrapers.values():
            await scraper.launch()
    
    async def search(self, platform, subject="", grade="", year="", keyword="", result_callback=None, stop_event=None):
        results = []
        
        if platform in self.scrapers:
            scraper = self.scrapers[platform]
            results = await scraper.search(subject, grade, year, keyword, result_callback, stop_event)
        
        return results
    
    async def close(self):
        tasks = [scraper.close() for scraper in self.scrapers.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        self.scrapers.clear()