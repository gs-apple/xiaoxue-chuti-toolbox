# -*- coding: utf-8 -*-
"""真题模块离线单测。

约束（评审 4.4 硬规则）：
  * 不联外网：HTTP 一律用桩函数替身。
  * 不读真实数据文件：收藏夹/历史/db 全部走 tempfile 隔离。
  * 不断言"空/0/False"这类恒真事实（比如曾经的"题库恒空"），只断言可证伪的行为。

跑法：python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import constants                                        # noqa: E402
from zhenti import zhenti_core as core                  # noqa: E402
from zhenti import zhenti_ui as ui                      # noqa: E402


# ══════════════════════════════════════════════════════════
#  年级
# ══════════════════════════════════════════════════════════

class GradeTests(unittest.TestCase):
    def setUp(self):
        self.scraper = core.PaperScraper()
        self.config = core.PLATFORM_CONFIGS["shijuan1"]

    def test_identify_grade_never_leaves_value_domain(self):
        """URL 兜底分支曾经返回「高1」，而「高1」不在 GRADES 里。"""
        cases = [
            ("2016-2017学年第一学期期末统测语文试卷", "g1"),
            ("", "g3"),
            ("", "10"),
            ("", "3"),
            ("初二物理期末试卷", "8"),
            ("高一期末统测语文试卷", "g1"),
        ]
        for title, url_grade in cases:
            got = self.scraper._identify_grade(title, url_grade, self.config, fallback="四年级")
            self.assertIn(got, constants.GRADES, f"{title!r}/{url_grade} -> {got!r}")

    def test_identify_grade_alias(self):
        """「初二」是站点别名，要折算成「八年级」而不是原样透传。"""
        got = self.scraper._identify_grade("初二物理期末试卷", "", self.config)
        self.assertEqual(got, "八年级")

    def test_identify_grade_falls_back(self):
        self.assertEqual(
            self.scraper._identify_grade("没有年级字样的试卷", "xyz", self.config, fallback="五年级"),
            "五年级")

    def test_canonical_grade(self):
        self.assertEqual(core.canonical_grade("初一"), "七年级")
        self.assertEqual(core.canonical_grade("高一"), "高一")
        self.assertEqual(core.canonical_grade("高中"), "")
        self.assertEqual(core.canonical_grade(""), "")


# ══════════════════════════════════════════════════════════
#  年份匹配
# ══════════════════════════════════════════════════════════

class YearTests(unittest.TestCase):
    def test_years_in_title_extracts_tokens(self):
        self.assertEqual(core.years_in_title("2016-2017学年四年级语文"), {"2016", "2017"})
        self.assertEqual(core.years_in_title("统编版2024年期中卷"), {"2024"})

    def test_partial_year_does_not_match(self):
        """子串匹配的老写法里 "24" 会命中 "2024"。"""
        years = core.years_in_title("2024年期中试卷")
        self.assertNotIn("24", years)
        self.assertIn("2024", years)

    def test_year_label(self):
        self.assertEqual(core.year_label("统编版2024年期中卷"), "2024")
        self.assertEqual(core.year_label("2023-2024学年四年级语文"), "2023-24")
        self.assertEqual(core.year_label("没有年份的试卷"), "")


# ══════════════════════════════════════════════════════════
#  搜索管线（离线桩）
# ══════════════════════════════════════════════════════════

SZ_LIST_HTML = """
<html><body>
  <a href="/sannianji/1.html" title="2024年春三年级语文期末试卷（附参考答案）">2024年春三年级语文期末试卷（附参考答案）</a>
  <a href="/sannianji/2.html">免费下载（附参考答案）</a>
  <a href="/sannianji/3.html">三年级数学期中测试卷</a>
  <a href="/sannianji/4.html">2024年春三年级语文期末试卷（附参考答案）</a>
</body></html>
"""


class SearchPipelineTests(unittest.TestCase):
    def setUp(self):
        self.scraper = core.PaperScraper()
        self.messages = []
        self.scraper._safe_get = lambda url, timeout=15, declared_encoding="": (SZ_LIST_HTML, None)

    def _search(self, **kwargs):
        kwargs.setdefault("grade", "3")
        kwargs.setdefault("subject", "语文")
        return self.scraper.search(
            "szxuexiao", progress_callback=self.messages.append, **kwargs)

    def test_noise_title_dropped_after_clean(self):
        """清洗后变空的标题不许入列（原先是清洗前判长度）。"""
        results = self._search()
        for item in results:
            self.assertTrue(item["title"].strip(), "出现了空标题结果")

    def test_title_noise_suffix_removed(self):
        results = self._search()
        self.assertTrue(results)
        self.assertEqual(results[0]["title"], "2024年春三年级语文期末试卷")

    def test_answer_flag_and_year(self):
        item = self._search()[0]
        self.assertTrue(item["has_answer"])
        self.assertEqual(item["year"], "2024")

    def test_other_subject_dropped(self):
        """数学卷不该被语文路径收进来。"""
        titles = [item["title"] for item in self._search()]
        self.assertFalse(any("数学" in t for t in titles), titles)

    def test_same_title_different_url_both_kept(self):
        """同名不同 url 是管线自身产物（清洗后归一同名），两条都该保留。"""
        results = self._search()
        self.assertEqual(len(results), 2)
        self.assertEqual(len({item["url"] for item in results}), 2)

    def test_grade_in_value_domain(self):
        for item in self._search():
            self.assertIn(item["grade"], constants.GRADES)

    def test_keyword_filter(self):
        self.assertEqual(self._search(keyword="期末"), self._search())
        self.assertEqual(self._search(keyword="月考"), [])

    def test_year_filter_is_equality(self):
        self.assertTrue(self._search(year="2024"))
        self.assertEqual(self._search(year="24"), [])

    def test_unsupported_grade_reports_progress(self):
        """不支持的年级必须给反馈，不能静默返回 0 条。"""
        results = self.scraper.search(
            "szxuexiao", grade="9", progress_callback=self.messages.append)
        self.assertEqual(results, [])
        self.assertTrue(any("没有该年级" in m for m in self.messages), self.messages)

    def test_empty_grade_requires_explicit_flag(self):
        self.assertEqual(self.scraper.search("szxuexiao", progress_callback=self.messages.append), [])
        self.assertTrue(any("未指定年级" in m for m in self.messages), self.messages)

    def test_unsupported_subject_reports_progress(self):
        results = self.scraper.search(
            "szxuexiao", subject="物理", grade="3", progress_callback=self.messages.append)
        self.assertEqual(results, [])
        self.assertTrue(any("物理" in m for m in self.messages), self.messages)


# ══════════════════════════════════════════════════════════
#  平台能力声明
# ══════════════════════════════════════════════════════════

class PlatformTests(unittest.TestCase):
    def test_resolve_platform_key(self):
        self.assertEqual(core.resolve_platform_key("shijuan1"), "shijuan1")
        self.assertEqual(core.resolve_platform_key("第一试卷网"), "shijuan1")
        self.assertEqual(core.resolve_platform_key("https://www.shijuan.net"), "shijuan_net")
        self.assertEqual(core.resolve_platform_key("不存在的站"), "")

    def test_grade_support(self):
        self.assertTrue(core.platform_supports_grade("shijuan1", "高三"))
        self.assertFalse(core.platform_supports_grade("szxuexiao", "高一"))
        self.assertFalse(core.platform_supports_grade("xbjy", "七年级"))

    def test_subjects_subset_of_ui_list(self):
        """平台声明学科必须是 UI 学科表的子集，否则下拉框会出现幽灵学科。"""
        ui_subjects = {s for subjects in ui.SUBJECTS_BY_GRADE.values() for s in subjects}
        for key in core.PLATFORM_CONFIGS:
            for subject in core.platform_subjects(key):
                self.assertIn(subject, ui_subjects, f"{key}:{subject}")

    def test_ui_platforms_single_source(self):
        self.assertEqual(set(ui.PLATFORMS.values()), set(core.PLATFORM_CONFIGS))

    def test_download_kind(self):
        self.assertEqual(core.platform_download_kind("shijuan1"), "direct")
        self.assertEqual(core.platform_download_kind("shijuan_net"), "page")
        self.assertEqual(core.platform_download_kind("szxuexiao"), "none")
        self.assertEqual(core.platform_download_kind("unknown"), "none")


# ══════════════════════════════════════════════════════════
#  学科按年级递进（2026-10-28 需求：学科要跟年级走）
# ══════════════════════════════════════════════════════════

class SubjectProgressionTests(unittest.TestCase):
    """口径来自第一试卷网逐栏目实测，不是课程表推演。

    实测矩阵：语数英 1~12 年级全有；物理 8/9/高中；化学 9/高中；
    生物、地理 7/8/高中（九年级结课）；历史、政治 7/9/高中；该站无科学栏目。
    """

    def test_quick_search_is_gone(self):
        """快捷搜索已按需求删除，别让按钮和 handler 偷偷回来。"""
        self.assertFalse(hasattr(ui.ZhentiTabWidget, "_quick_search"))
        self.assertFalse(hasattr(ui.ZhentiTabWidget, "_build_quick_search"))
        self.assertFalse(hasattr(ui, "_grade_colors"))

    def test_year_choices_include_2027(self):
        self.assertIn("2027", ui.YEAR_CHOICES)
        self.assertEqual(ui.YEAR_CHOICES[0], "不限")
        self.assertEqual(ui.YEAR_CHOICES[1], "2027", "年份应倒序，最新的排在最前")

    def test_primary_school_subjects(self):
        self.assertEqual(ui.SUBJECTS_BY_GRADE["一年级"], ["全部", "语文", "数学", "英语"])
        self.assertNotIn("物理", ui.SUBJECTS_BY_GRADE["六年级"])
        self.assertIn("科学", ui.SUBJECTS_BY_GRADE["三年级"])

    def test_junior_subjects_step_up(self):
        seven = set(ui.SUBJECTS_BY_GRADE["七年级"])
        eight = set(ui.SUBJECTS_BY_GRADE["八年级"])
        nine = set(ui.SUBJECTS_BY_GRADE["九年级"])
        self.assertNotIn("物理", seven)
        self.assertNotIn("化学", seven)
        self.assertIn("物理", eight)
        self.assertNotIn("化学", eight)
        self.assertIn("化学", nine)
        # 生物地理在九年级已结课
        self.assertNotIn("生物", nine)
        self.assertNotIn("地理", nine)

    def test_senior_has_all_nine(self):
        for grade in ("高一", "高二", "高三"):
            subjects = set(ui.SUBJECTS_BY_GRADE[grade])
            for subject in ("语文", "数学", "英语", "物理", "化学",
                            "生物", "历史", "地理", "政治"):
                self.assertIn(subject, subjects, f"{grade}缺{subject}")

    def test_subject_count_grows_in_primary_school(self):
        """小学段只增不减：一二年级 4 项 → 三到六年级 6 项。"""
        counts = [len(ui.SUBJECTS_BY_GRADE[g]) for g in core.GRADES[:6]]
        for earlier, later in zip(counts, counts[1:]):
            self.assertGreaterEqual(later, earlier, f"小学段科目数回落: {counts}")

    def test_ninth_grade_is_smaller_than_eighth(self):
        """九年级生物地理结课，科目数比八年级少是正确事实，不是回退 bug。

        这条断言同时挡住"为了满足只增不减而把生地塞回九年级"的改法。
        """
        self.assertLess(len(ui.SUBJECTS_BY_GRADE["九年级"]),
                        len(ui.SUBJECTS_BY_GRADE["八年级"]))

    def test_platform_subjects_filtered_by_grade(self):
        """只问平台会得到"一年级能学物理"这种假选项，必须带年级问。"""
        self.assertNotIn("物理", core.platform_subjects("shijuan1", "一年级"))
        self.assertEqual(
            core.platform_subjects("shijuan1", "一年级"), ("语文", "数学", "英语"))
        self.assertIn("物理", core.platform_subjects("shijuan1", "八年级"))
        self.assertNotIn("化学", core.platform_subjects("shijuan1", "八年级"))
        self.assertIn("化学", core.platform_subjects("shijuan1", "九年级"))
        self.assertNotIn("生物", core.platform_subjects("shijuan1", "九年级"))
        self.assertIn("地理", core.platform_subjects("shijuan1", "高一"))

    def test_platform_subjects_without_grade_is_full_list(self):
        """不传年级时保持原语义（平台全集），工具脚本还在用这个口径。"""
        self.assertEqual(core.platform_subjects("shijuan1"), core.PLATFORM_CONFIGS["shijuan1"].subject_names)

    def test_every_platform_grade_has_subjects(self):
        """每个平台支持的每个年级，至少要有语文数学，不能出现空下拉。"""
        for key in core.PLATFORM_CONFIGS:
            for grade in core.platform_grade_names(key):
                self.assertTrue(core.platform_subjects(key, grade), f"{key}/{grade} 学科为空")

    def test_deyufazhi_normalized_to_zhengzhi(self):
        """初中教材叫「道德与法治」，站内只有 sjzz 一个栏目，必须归一。"""
        self.assertEqual(constants.SUBJECT_KEYWORDS["道德与法治"], "政治")
        self.assertEqual(constants.SUBJECT_KEYWORDS["道法"], "政治")
        self.assertNotIn("道德与法治", core.PLATFORM_CONFIGS["shijuan1"].subject_names)

    def test_zhengzhi_path_matches_sjzz(self):
        self.assertEqual(core.PLATFORM_CONFIGS["shijuan1"].subject_path["政治"], "a/sjzz{g}/")


# ══════════════════════════════════════════════════════════
#  科学：三年级起列进下拉，数据由中小学试卷网提供
# ══════════════════════════════════════════════════════════

class ScienceSubjectTests(unittest.TestCase):
    """第一试卷网 9 个栏目里没有科学，但三年级确实开科学课。

    实测（2026-10-28）：中小学试卷网 /kexue/ 栏目有 25 条，其中三年级 3 条、
    五年级 4 条、六年级 7 条；年级页里一条科学都抓不到（被语数英挤掉）。
    """

    def setUp(self):
        self.scraper = core._get_scraper()
        self.config = core.PLATFORM_CONFIGS["szxuexiao"]

    def test_science_listed_from_third_grade(self):
        for grade in ("三年级", "四年级", "五年级", "六年级"):
            self.assertIn("科学", ui.subject_choices(grade), f"{grade}应列出科学")
        for grade in ("一年级", "二年级"):
            self.assertNotIn("科学", ui.subject_choices(grade), f"{grade}没开科学课")

    def test_dropdown_not_filtered_by_current_platform(self):
        """下拉必须是课程全集：第一试卷网没有科学，三年级也得列出来。

        原先按 platform_subjects 求交，选第一试卷网时三年级只剩语数英，
        用户以为软件没写科学。
        """
        choices = ui.subject_choices("三年级")
        missing = [s for s in choices if s != "全部"
                   and s not in core.platform_subjects("shijuan1", "三年级")]
        self.assertEqual(missing, ["科学"])         # 确实缺，但依然出现在下拉里
        self.assertIn("科学", choices)

    def test_platforms_with_subject_points_to_science_sites(self):
        keys = core.platforms_with_subject("科学")
        self.assertIn("szxuexiao", keys)
        self.assertIn("xbjy", keys)
        self.assertNotIn("shijuan1", keys)
        # 三年级也成立（中小学试卷网支持 1-6 年级）
        self.assertIn("szxuexiao", core.platforms_with_subject("科学", "三年级"))

    def test_science_has_its_own_column(self):
        self.assertEqual(self.config.subject_path["科学"], "kexue/")
        self.assertEqual(self.config.grade_page_url, "{g}/")

    def test_grade_page_and_column_both_crawled(self):
        """年级页与学科栏目页互不覆盖，指定学科时两个都要抓。"""
        urls = [u for u, _ in self.scraper._resolve_targets(self.config, "sannianji", "科学")]
        self.assertTrue(any(u.endswith("/sannianji/") for u in urls), urls)
        self.assertTrue(any(u.endswith("/kexue/") for u in urls), urls)
        self.assertEqual(len(urls), 2)

    def test_all_subjects_covers_mixed_page_and_columns(self):
        urls = [u for u, _ in self.scraper._resolve_targets(self.config, "sannianji", "")]
        self.assertEqual(len(urls), 5, urls)        # 1 个年级页 + 4 个学科栏目
        self.assertTrue(any(u.endswith("/sannianji/") for u in urls))

    def test_single_column_platform_unchanged(self):
        """第一试卷网没有年级混合页，指定学科时仍只抓一个栏目页（回归）。"""
        urls = self.scraper._resolve_targets(core.PLATFORM_CONFIGS["shijuan1"], "4", "语文")
        self.assertEqual(len(urls), 1)
        self.assertTrue(urls[0][0].endswith("/a/sjyw4/"))

    def test_strict_subject_detection_on_mixed_page(self):
        """年级混合页里标题没写学科的，不能硬归成用户要的那科。"""
        title = "2026-2027三年级数学《测量》重点内容及基础知识练习"
        self.assertIsNone(self.scraper._detect_subject(title, "科学", self.config, strict=True))
        self.assertEqual(self.scraper._detect_subject("三年级科学期末卷", "科学", self.config, strict=True), "科学")
        self.assertIsNone(self.scraper._detect_subject(
            "2026统编版三年级期中达标测试卷", "科学", self.config, strict=True))
        # 栏目页不 strict：整页都是该学科，标题没写学科也算
        self.assertEqual(self.scraper._detect_subject(
            "2026统编版三年级期中达标测试卷", "科学", self.config), "科学")

    def test_edition_prefix_is_not_a_noise_word(self):
        """「人教/部编/统编」是教材版本前缀，实测挡掉了 47 条真实试卷。"""
        for word in ("人教", "部编", "统编"):
            self.assertNotIn(word, self.config.exclude_keywords)


# ══════════════════════════════════════════════════════════
#  下载安全
# ══════════════════════════════════════════════════════════

class DownloadSafetyTests(unittest.TestCase):
    def test_extension_whitelist(self):
        self.assertTrue(core.is_allowed_file("试卷.rar"))
        self.assertTrue(core.is_allowed_file("a.PDF"))
        self.assertFalse(core.is_allowed_file("constants.py"))
        self.assertFalse(core.is_allowed_file("setup.exe"))
        self.assertFalse(core.is_allowed_file("noext"))

    def test_sanitize_strips_directories(self):
        for raw in ["../../etc/passwd.rar", "C:\\Windows\\evil.rar", "..\\..\\x.pdf"]:
            name = core.PaperScraper._sanitize_filename(raw)
            self.assertNotIn("/", name)
            self.assertNotIn("\\", name)
            self.assertNotIn("..", name)

    def test_sanitize_trailing_dot_and_space(self):
        """尾部点/空格会被 Win32 静默吃掉，导致落盘名与返回名不一致。"""
        self.assertEqual(core.PaperScraper._sanitize_filename("widgets.py. "), "widgets.py")
        self.assertFalse(core.is_allowed_file(core.PaperScraper._sanitize_filename("widgets.py. ")))

    def test_sanitize_rejects_device_names(self):
        for raw in ["CON", "con.rar", "NUL.doc", "COM1.zip", "LPT9.rar"]:
            self.assertEqual(core.PaperScraper._sanitize_filename(raw), "", raw)

    def test_sanitize_rejects_empty(self):
        for raw in ["", ".", "..", "   "]:
            self.assertEqual(core.PaperScraper._sanitize_filename(raw), "", repr(raw))

    def test_unique_path_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = core.PaperScraper._unique_path(tmp, "a.rar")
            self.assertEqual(os.path.basename(first), "a.rar")
            open(first, "wb").close()
            second = core.PaperScraper._unique_path(tmp, "a.rar")
            self.assertEqual(os.path.basename(second), "a(1).rar")
            self.assertNotEqual(first, second)

    def test_within_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.abspath(tmp)
            self.assertTrue(core._within_dir(os.path.join(base, "a.rar"), base))
            self.assertFalse(core._within_dir(os.path.join(base, "..", "a.rar"), base))

    def test_download_refuses_disallowed_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = core.PaperScraper().download_file("https://x.com/evil.py", tmp)
            self.assertFalse(result["success"])
            self.assertEqual(os.listdir(tmp), [])

    def test_unknown_platform_download_info(self):
        info = core.PaperScraper().get_download_info("https://example.com/a/1.html")
        self.assertEqual(info["type"], "none")

    def test_no_link_platform_download_info(self):
        """szxuexiao 的下载正则实测空跑，现在明确声明为 none，不发请求。"""
        info = core.PaperScraper().get_download_info("https://appsj.szxuexiao.com/x/1.html")
        self.assertEqual(info["type"], "none")
        self.assertIn("不提供直链", info["message"])


class FakeHeaders(dict):
    pass


class FakeResponse:
    """假 HTTP 响应：只实现 download_file 用到的部分。"""

    def __init__(self, headers=None, chunks=(), status_code=200):
        self.headers = FakeHeaders(headers or {})
        self._chunks = list(chunks)
        self.status_code = status_code

    def iter_content(self, chunk_size=8192):
        for chunk in self._chunks:
            yield chunk


class FakeSession:
    def __init__(self, response):
        self.response = response

    def get(self, *args, **kwargs):
        return self.response


class DownloadFlowTests(unittest.TestCase):
    def _run(self, response, stop_event=None):
        scraper = core.PaperScraper()
        with mock.patch.object(core, "_get_session", lambda: FakeSession(response)):
            return scraper.download_file("https://www.shijuan1.com/uploads/a.rar", self.tmp,
                                         stop_event=stop_event)

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = self._tmpdir.name

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_rfc5987_filename(self):
        resp = FakeResponse({"Content-Disposition": "attachment; filename*=UTF-8''%E8%AF%95%E5%8D%B7.pdf"})
        self.assertEqual(core.PaperScraper._extract_filename(resp, "https://x/a.rar"), "试卷.pdf")

    def test_plain_filename_header(self):
        resp = FakeResponse({"Content-Disposition": 'attachment; filename="卷子.rar"'})
        self.assertEqual(core.PaperScraper._extract_filename(resp, "https://x/a.rar"), "卷子.rar")

    def test_filename_falls_back_to_url(self):
        self.assertEqual(
            core.PaperScraper._extract_filename(FakeResponse(), "https://x/soft/abc.zip"), "abc.zip")

    def test_success_writes_file(self):
        resp = FakeResponse({"Content-Length": "6"}, [b"abc", b"def"])
        result = self._run(resp)
        self.assertTrue(result["success"], result)
        with open(result["filepath"], "rb") as f:
            self.assertEqual(f.read(), b"abcdef")

    def test_incomplete_download_rejected(self):
        resp = FakeResponse({"Content-Length": "10"}, [b"12345"])
        result = self._run(resp)
        self.assertFalse(result["success"])
        self.assertIn("不完整", result["message"])
        self.assertEqual(os.listdir(self.tmp), [], "半截文件必须清理掉")

    def test_size_limit_rejected(self):
        resp = FakeResponse({"Content-Length": str(core.MAX_DOWNLOAD_BYTES + 1)}, [b"x"])
        result = self._run(resp)
        self.assertFalse(result["success"])
        self.assertIn("上限", result["message"])

    def test_cancel_leaves_no_file(self):
        import threading
        stop_event = threading.Event()
        stop_event.set()
        resp = FakeResponse({"Content-Length": "6"}, [b"abc", b"def"])
        result = self._run(resp, stop_event=stop_event)
        self.assertFalse(result["success"])
        self.assertIn("取消", result["message"])
        self.assertEqual(os.listdir(self.tmp), [])

    def test_image_disguised_as_archive_rejected(self):
        """第一试卷网防盗链实测：不带 Referer 回的是 JPEG 占位图，
        Content-Type 和 Content-Length 都正常，只有文件头能看出不是压缩包。"""
        jpeg = b"\xff\xd8\xff\xe1\x00\x18Exif\x00\x00II*\x00"
        resp = FakeResponse({"Content-Type": "image/jpeg", "Content-Length": str(len(jpeg))}, [jpeg])
        result = self._run(resp)
        self.assertFalse(result["success"])
        self.assertIn("图片", result["message"])
        self.assertEqual(os.listdir(self.tmp), [], "占位图不能留下 .rar")

    def test_html_page_rejected(self):
        body = b"<!DOCTYPE html><html><body>404</body></html>"
        resp = FakeResponse({"Content-Type": "text/html; charset=gbk"}, [body])
        result = self._run(resp)
        self.assertFalse(result["success"])
        self.assertIn("网页", result["message"])
        self.assertEqual(os.listdir(self.tmp), [])

    def test_referer_is_forwarded(self):
        """下载请求必须带上详情页 Referer，否则站点回占位图。"""
        captured = {}

        class Recorder(FakeSession):
            def get(self, *args, **kwargs):
                captured.update(kwargs.get("headers") or {})
                return self.response

        page = "https://www.shijuan1.com/a/sjyw4/332739.html"
        resp = FakeResponse({"Content-Length": "6"}, [b"abc", b"def"])
        scraper = core.PaperScraper()
        with mock.patch.object(core, "_get_session", lambda: Recorder(resp)):
            result = scraper.download_file(
                "https://www.shijuan1.com/uploads/a.rar", self.tmp, referer=page)
        self.assertTrue(result["success"], result)
        self.assertEqual(captured.get("Referer"), page)

    def test_rfc5987_and_content_sniff_helpers(self):
        self.assertEqual(core._reject_reason(b"\xff\xd8\xff", ""), "服务器返回的是JPEG 图片，不是试卷文件")
        self.assertIn("图片", core._reject_reason(b"", "image/png"))
        self.assertIn("网页", core._reject_reason(b"", "text/html"))
        self.assertEqual(core._reject_reason(b"Rar!\x1a\x07\x01\x00", "application/x-rar-compressed"), "")
        self.assertEqual(core._reject_reason(b"PK\x03\x04", "application/octet-stream"), "")


# ══════════════════════════════════════════════════════════
#  UI 逻辑（假对象，不起窗口）
# ══════════════════════════════════════════════════════════

class FakeTree:
    def __init__(self):
        self.rows = {}
        self.selected = ()

    def insert(self, parent, index, iid=None, values=()):
        self.rows[iid] = values

    def get_children(self):
        return tuple(self.rows)

    def delete(self, *items):
        for item in items:
            self.rows.pop(item, None)

    def selection(self):
        return self.selected


def _make_widget():
    widget = ui.ZhentiTabWidget.__new__(ui.ZhentiTabWidget)
    widget.result_tree = FakeTree()
    widget.search_results = []
    widget._by_iid = {}
    widget._next_iid = 0
    widget.result_count = 0
    widget._view_mode = "search"
    widget._deferred_warnings = []
    return widget


class UiSelectionTests(unittest.TestCase):
    def setUp(self):
        self.widget = _make_widget()
        self.items = [{"title": "同一个标题", "url": f"https://x.com/{i}.html"} for i in range(3)]
        for item in self.items:
            self.widget._add_result(item)

    def test_second_row_maps_to_second_item(self):
        """同名结果很常见，点第 2 行必须拿到第 2 条的 url。"""
        self.widget.result_tree.selected = ("1",)
        self.assertEqual(self.widget._require_selected()["url"], "https://x.com/1.html")

    def test_no_selection_returns_none(self):
        self.widget.result_tree.selected = ()
        with mock.patch.object(ui.messagebox, "showinfo"):
            self.assertIsNone(self.widget._require_selected())

    def test_iid_unique_and_monotonic(self):
        self.assertEqual(list(self.widget.result_tree.rows), ["0", "1", "2"])

    def test_reset_clears_mapping_and_counter(self):
        self.widget._reset_results()
        self.assertEqual(self.widget._by_iid, {})
        self.assertEqual(self.widget._next_iid, 0)
        self.assertEqual(self.widget.search_results, [])
        self.assertEqual(self.widget.result_tree.get_children(), ())

    def test_duplicate_url_still_gets_unique_iid(self):
        """收藏夹里两条同一 url（手工编辑过）也不能让 Tk 报 already exists。"""
        widget = _make_widget()
        same = {"title": "t", "url": "https://x.com/1.html"}
        widget._add_result(dict(same))
        widget._add_result(dict(same))
        self.assertEqual(len(widget.result_tree.rows), 2)


class UiPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.widget = _make_widget()

    def test_save_json_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "fav.json")
            self.assertTrue(self.widget._save_json(path, [{"a": 1}]))
            self.assertTrue(os.path.exists(path))

    def test_save_json_reports_failure(self):
        """写盘失败必须返回 False —— 否则界面会无条件报"收藏成功"。"""
        with tempfile.TemporaryDirectory() as tmp:
            target_dir = os.path.join(tmp, "dir")
            os.makedirs(target_dir)
            self.assertFalse(self.widget._save_json(target_dir, []))

    def test_load_json_missing_file_returns_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.widget._load_json(os.path.join(tmp, "none.json"), []), [])
            self.assertEqual(self.widget._deferred_warnings, [])

    def test_load_json_corrupt_file_backed_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fav.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{不是 json")
            self.assertEqual(self.widget._load_json(path, []), [])
            self.assertTrue(os.path.exists(path + ".corrupt"))
            self.assertTrue(self.widget._deferred_warnings)

    def test_load_json_wrong_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fav.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"a": 1}')
            self.assertEqual(self.widget._load_json(path, []), [])
            self.assertTrue(self.widget._deferred_warnings)


class UiKeywordTests(unittest.TestCase):
    def setUp(self):
        self.widget = _make_widget()

    def test_parse_prefix_grade_and_subject(self):
        self.assertEqual(self.widget._parse_keyword("三年级语文试卷"), ("3", "语文", "试卷"))
        self.assertEqual(self.widget._parse_keyword("数学"), (None, "数学", ""))
        self.assertEqual(self.widget._parse_keyword("高一物理"), ("10", "物理", ""))

    def test_unmatched_keyword_kept_whole(self):
        self.assertEqual(self.widget._parse_keyword(" 期末 "), (None, None, " 期末 "))


class PageTurnTests(unittest.TestCase):
    """列表页翻页：只拿第一页会漏掉绝大部分存量（2026-10-28 实测：25→125）。"""

    def setUp(self):
        self.scraper = core.PaperScraper()

    def test_首页HTML里抽后续页(self):
        """第一试卷网形态：list_116_2.html，栏目号不该写死。"""
        html = ('<a href="list_116_1.html">1</a>'
                '<a href="list_116_2.html">2</a>'
                '<a href="list_116_3.html">3</a>')
        cfg = core.PLATFORM_CONFIGS["shijuan1"]
        got = self.scraper._page_urls(html, "https://www.shijuan1.com/a/sjsx5/", cfg, 3)
        self.assertEqual(got, ["https://www.shijuan1.com/a/sjsx5/list_116_2.html",
                               "https://www.shijuan1.com/a/sjsx5/list_116_3.html"])

    def test_绝对路径形态拼成完整URL(self):
        """试卷网的分页是 /wunianji/shuxue/index_2.html 这种绝对路径。"""
        html = '<a href="/wunianji/shuxue/index_2.html">2</a>'
        cfg = core.PLATFORM_CONFIGS["shijuan_net"]
        got = self.scraper._page_urls(html, "https://www.shijuan.net/wunianji/shuxue/",
                                      cfg, 2)
        self.assertEqual(got, ["https://www.shijuan.net/wunianji/shuxue/index_2.html"])

    def test_页面里没有分页链接时不猜(self):
        """站点改版后宁可只给一页，也不该凭空编一个链接出来。"""
        cfg = core.PLATFORM_CONFIGS["shijuan1"]
        self.assertEqual(self.scraper._page_urls("<html></html>",
                                                 "https://x.com/a/", cfg, 5), [])

    def test_没配模板的站不翻页(self):
        """新一试卷之外没有 page_url_template；心标教育列表页里也找不到分页链接。"""
        self.assertEqual(core.PLATFORM_CONFIGS["xbjy"].page_url_template, "")
        self.assertEqual(core.PLATFORM_CONFIGS["xbjy"].page_href_pattern, "")
        cfg = core.PLATFORM_CONFIGS["xbjy"]
        self.assertEqual(self.scraper._page_urls("<a href='2.html'>2</a>",
                                                 "https://www.xbjy.com/s/xxsx/", cfg, 5), [])

    def test_没有分页链接的站按模板拼(self):
        cfg = core.PLATFORM_CONFIGS["yishijuan"]
        got = self.scraper._page_urls("", "https://www.yishijuan.com/xiaoxueshijuan/",
                                      cfg, cfg.max_pages)
        # 模板站按页码直接拼出第 2..max_pages 页
        self.assertEqual(got[0], "https://www.yishijuan.com/xiaoxueshijuan/2.html")
        self.assertEqual(len(got), cfg.max_pages - 1)

    def test_max_pages为1时不翻页(self):
        cfg = core.PLATFORM_CONFIGS["shijuan1"]
        html = '<a href="list_116_2.html">2</a>'
        self.assertEqual(self.scraper._page_urls(
            html, "https://www.shijuan1.com/a/sjsx5/", cfg, 1), [])

    def test_各平台的默认页数(self):
        """第一试卷网 3 页，其余平台 20 页（2026-10-29 用户指定）。"""
        for key, cfg in core.PLATFORM_CONFIGS.items():
            expect = 3 if key == "shijuan1" else 20
            self.assertEqual(cfg.max_pages, expect, f"{key} 的默认翻页数不对")

    def test_每页链接去重且不与列表页自身重复(self):
        html = ('<a href="list_116_2.html">2</a>'
                '<a href="list_116_2.html">2</a>')
        cfg = core.PLATFORM_CONFIGS["shijuan1"]
        got = self.scraper._page_urls(html, "https://www.shijuan1.com/a/sjsx5/", cfg, 5)
        self.assertEqual(got, ["https://www.shijuan1.com/a/sjsx5/list_116_2.html"])

    def test_多页里重复的卷子只保留一条(self):
        """翻页后同一份卷子会在多页的推荐位重复出现：走真实 search 验证 URL 去重。"""
        link = ('<a href="/a/sjsx5/332826.html">'
                '人教版2025学年五年级数学下册期末学业水平测试卷（含答案）</a>')
        with mock.patch.object(core.PaperScraper, "_safe_get", return_value=(link, "")):
            results = self.scraper.search("shijuan1", subject="数学", grade="5")
        urls = [r["url"] for r in results]
        self.assertTrue(urls, "桩 HTML 里这条链接应该被解析出来")
        self.assertEqual(len(urls), len(set(urls)), urls)


if __name__ == "__main__":
    unittest.main(verbosity=2)
