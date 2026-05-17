# shuxue_core.py — 小学数学题目生成核心（最终稳定版）
# 所有变量均有明确赋值，无递归，内置安全上限

import random
import math
import re
import os
import json
from fractions import Fraction


# ══════════════════════════════════════════════════════════
#  去重缓存（文件级，跨会话持久化）
# ══════════════════════════════════════════════════════════
class _DedupCache:
    """文件级题目去重缓存，最多保留最近500条"""
    _MAX = 500
    _path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".question_cache.json")

    @classmethod
    def _load(cls):
        if os.path.exists(cls._path):
            try:
                with open(cls._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data[-cls._MAX:]
            except Exception:
                pass
        return []

    @classmethod
    def _save(cls, items):
        try:
            with open(cls._path, "w", encoding="utf-8") as f:
                json.dump(items[-cls._MAX:], f, ensure_ascii=False)
        except Exception:
            pass

    @classmethod
    def normalize(cls, question_text):
        """标准化题目文本用于去重比较"""
        t = question_text
        t = re.sub(r'FRAC\[\d+,\d+\]', lambda m: '', t)
        t = t.replace(" ", "").replace("×", "*").replace("÷", "/")
        t = t.replace("（", "(").replace("）", ")")
        t = t.lower()
        return t

    @classmethod
    def is_duplicate(cls, question_text):
        norm = cls.normalize(question_text)
        cache = cls._load()
        return norm in cache

    @classmethod
    def add(cls, question_text):
        norm = cls.normalize(question_text)
        cache = cls._load()
        if norm not in cache:
            cache.append(norm)
            cls._save(cache)

    @classmethod
    def clear(cls):
        cls._save([])

# ══════════════════════════════════════════════════════════
#  分数辅助标记
# ══════════════════════════════════════════════════════════
def _frac(f: Fraction) -> str:
    if f.denominator == 1:
        return str(f.numerator)
    return f"FRAC[{f.numerator},{f.denominator}]"

def _make_frac(den_min=2, den_max=12):
    den = random.randint(den_min, den_max)
    num = random.randint(1, den - 1)
    return Fraction(num, den)

FRAC_RE = re.compile(r'FRAC\[(\d+),(\d+)\]')

# ══════════════════════════════════════════════════════════
#  题型名称映射（保持UI兼容）
# ══════════════════════════════════════════════════════════
CATEGORY_NAMES = {
    "cb_10in": "10以内加减", "cb_20in": "20以内加减", "cb_100in": "100以内加减",
    "cb_10000in": "万以内加减", "cb_dec_addsub": "小数加减", "cb_frac_addsub": "分数加减",
    "cb_mul_table": "表内乘法", "cb_mul_2x1": "两位×一位", "cb_mul_3x1": "三位×一位",
    "cb_mul_2x2": "两位×两位", "cb_mul_3x2": "三位×两位",
    "cb_mul_dec": "小数乘法", "cb_mul_frac": "分数乘法", "cb_mul_simple": "乘法简便运算",
    "cb_div_table": "表内除法", "cb_div_remain": "带余数除法", "cb_div_int": "整除",
    "cb_div_1digit": "除数是一位数", "cb_div_2digit": "除数是两位数",
    "cb_div_dec": "小数除法", "cb_div_frac": "分数除法",
    "cb_mix_addsub": "连加连减", "cb_mix_addmul": "加减乘", "cb_mix_addmulsub": "加减乘除",
    "cb_mix_dec": "小数混合", "cb_mix_frac": "分数混合",
    "cb_find_rule": "找规律填数", "cb_arithmetic": "等差数列", "cb_simple_calc": "简便运算",
    "cb_frac_skill": "分数巧算", "cb_new_op": "定义新运算",
    "cb_sum_diff": "和差倍", "cb_age": "年龄问题", "cb_tree": "植树问题",
    "cb_chicken_rabbit": "鸡兔同笼", "cb_duck": "盈亏问题",
    "cb_project": "工程问题", "cb_form": "行程问题", "cb_concentration": "浓度问题",
    "cb_graph_count": "图形计数", "cb_graph_split": "图形分割",
    "cb_perimeter": "周长面积", "cb_3d_graph": "立体图形", "cb_equal_area": "等积变形",
    "cb_odd_even": "奇偶分析", "cb_whole_div": "整除问题", "cb_remainder": "余数问题",
    "cb_prime": "质/合问题", "cb_gcd_lcm": "公约数/倍数",
    "cb_logic": "推理问题", "cb_arrange": "统筹问题", "cb_best": "最优化",
    "cb_draw": "抽屉问题", "cb_container": "容斥问题",
}

ADVANCE_TYPES = {
    "cb_find_rule", "cb_arithmetic", "cb_frac_skill", "cb_new_op",
    "cb_sum_diff", "cb_age", "cb_tree", "cb_chicken_rabbit", "cb_duck",
    "cb_project", "cb_form", "cb_concentration",
    "cb_graph_count", "cb_graph_split", "cb_perimeter", "cb_3d_graph", "cb_equal_area",
    "cb_odd_even", "cb_whole_div", "cb_remainder", "cb_prime", "cb_gcd_lcm",
    "cb_logic", "cb_arrange", "cb_best", "cb_draw", "cb_container",
}

# ══════════════════════════════════════════════════════════
#  MathProblemGenerator — 题目生成器核心类
# ══════════════════════════════════════════════════════════
class MathProblemGenerator:
    _recent_hashes = []   # 记录最近生成的题目哈希，用于简单去重
    _max_recent = 50

    # ---------- 辅助：安全循环生成 ----------
    def _safe_gen(self, gen_func, max_tries=500, default=None):
        for _ in range(max_tries):
            try:
                result = gen_func()
                if result is not None and isinstance(result, tuple) and len(result) == 2:
                    return result
            except Exception:
                continue
        return default if default is not None else ("1 + 1 =", 2)

    # ==================== 加减法 ====================
    # ==================== 加减法（仅两数运算，填空用括号） ====================
    def gen_10in(self):
        def _once():
            v = random.randint(1, 3)  # 去掉原 v==4 的连加
            if v == 1:  # 直接运算
                op = random.choice(['+', '-'])
                if op == '+':
                    a_val = random.randint(1, 9)
                    b_val = random.randint(1, 10 - a_val)
                    return f"{a_val} + {b_val} =", a_val + b_val
                else:
                    a_val = random.randint(2, 10)
                    b_val = random.randint(1, a_val - 1)
                    return f"{a_val} - {b_val} =", a_val - b_val
            elif v == 2:  # 填空： ( ) + b = c
                b_val = random.randint(1, 5)
                c_val = random.randint(b_val + 1, 10)
                return f"( ) + {b_val} = {c_val}", c_val - b_val
            else:  # 填空： a - ( ) = c
                c_val = random.randint(1, 6)
                a_val = random.randint(c_val + 1, 10)
                return f"{a_val} - ( ) = {c_val}", a_val - c_val

        return self._safe_gen(_once)

    def gen_20in(self):
        def _once():
            v = random.randint(1, 3)
            if v == 1:  # 直接运算
                op = random.choice(['+', '-'])
                if op == '+':
                    a_val = random.randint(10, 19)
                    b_val = random.randint(1, 20 - a_val)
                    return f"{a_val} + {b_val} =", a_val + b_val
                else:
                    a_val = random.randint(11, 20)
                    b_val = random.randint(1, a_val - 1)
                    return f"{a_val} - {b_val} =", a_val - b_val
            elif v == 2:  # 填空： ( ) - b = c
                ans = random.randint(5, 13)
                sub = random.randint(1, 9)
                total = ans + sub
                if total > 20:
                    ans, sub, total = 5, 7, 12
                return f"( ) - {sub} = {ans}", total
            else:  # 填空： a - ( ) = c 或直接运算（可调整）
                a_val = random.randint(11, 20)
                b_val = random.randint(a_val - 10 + 1, min(a_val - 1, 9))
                return f"{a_val} - {b_val} =", a_val - b_val

        return self._safe_gen(_once)

    def gen_100in(self):
        def _once():
            v = random.randint(1, 3)  # 去掉连加和三个数运算
            if v == 1:  # 直接运算
                op = random.choice(['+', '-'])
                a_val = random.randint(10, 90)
                if op == '+':
                    b_val = random.randint(1, 99 - a_val)
                    return f"{a_val} + {b_val} =", a_val + b_val
                else:
                    b_val = random.randint(1, a_val - 1)
                    return f"{a_val} - {b_val} =", a_val - b_val
            elif v == 2:  # 填空： ( ) + b = c
                b_val = random.randint(10, 50)
                c_val = random.randint(b_val + 10, min(b_val + 50, 99))
                return f"( ) + {b_val} = {c_val}", c_val - b_val
            else:  # 填空： a - ( ) = c 或 整十数运算
                if random.random() < 0.5:
                    a_val = random.choice(range(10, 100, 10))
                    b_val = random.choice(range(10, 100 - a_val + 10, 10))
                    op = random.choice(['+', '-'])
                    if op == '-' and b_val > a_val:
                        a_val, b_val = b_val, a_val
                    if op == '+':
                        return f"{a_val} + {b_val} =", a_val + b_val
                    else:
                        return f"{a_val} - {b_val} =", a_val - b_val
                else:
                    ans = random.randint(10, 60)
                    sub = random.randint(10, 98 - ans)
                    total = ans + sub
                    return f"{total} - ( ) = {ans}", sub

        return self._safe_gen(_once)

    def gen_10000in(self):
        def _once():
            v = random.randint(1, 2)  # 只保留两数运算
            if v == 1:  # 直接运算
                op = random.choice(['+', '-'])
                if op == '+':
                    a_val = random.randint(1000, 9999 - 100)
                    b_val = random.randint(100, 9999 - a_val - 100)
                    return f"{a_val} + {b_val} =", a_val + b_val
                else:
                    a_val = random.randint(1000, 9999)
                    b_val = random.randint(100, a_val - 1)
                    return f"{a_val} - {b_val} =", a_val - b_val
            else:  # 整千/整百数运算
                a_val = random.choice(range(100, 9001, 100))
                b_val = random.choice(range(100, 10000 - a_val, 100))
                op = random.choice(['+', '-'])
                if op == '-' and b_val > a_val:
                    a_val, b_val = b_val, a_val
                if op == '+':
                    return f"{a_val} + {b_val} =", a_val + b_val
                else:
                    return f"{a_val} - {b_val} =", a_val - b_val

        return self._safe_gen(_once)

    def gen_decimal_addsub(self):
        def _once():
            v = random.randint(1, 2)  # 去掉三数混合
            if v == 1:  # 直接运算
                decimals = random.choice([1, 2])
                a_val = round(random.uniform(0.1, 10), decimals)
                b_val = round(random.uniform(0.1, 10), decimals)
                op = random.choice(['+', '-'])
                if op == '-':
                    a_val, b_val = sorted([a_val, b_val], reverse=True)
                ans = round(a_val + b_val if op == '+' else a_val - b_val, decimals)
                return f"{a_val} {op} {b_val} =", ans
            else:  # 整数加减小数
                a_val = random.randint(1, 20)
                b_val = round(random.uniform(0.1, 9.9), 1)
                return f"{a_val} + {b_val} =", round(a_val + b_val, 1)

        return self._safe_gen(_once)

    def gen_fraction_addsub(self):
        def _once():
            v = random.randint(1, 2)
            if v == 1:  # 同分母
                den = random.randint(2, 12)
                a_num = random.randint(1, den - 1)
                b_num = random.randint(1, den - 1)
                op = random.choice(['+', '-'])
                fa = Fraction(a_num, den)
                fb = Fraction(b_num, den)
                if op == '-' and fa < fb:
                    fa, fb = fb, fa
                ans = fa + fb if op == '+' else fa - fb
                return f"{_frac(fa)} {op} {_frac(fb)} =", ans  # 运算符两侧已有空格
            else:  # 异分母
                d1, d2 = random.choice([(2, 4), (3, 6), (2, 6), (4, 8), (3, 9)])
                a_num = random.randint(1, d1 - 1)
                b_num = random.randint(1, d2 - 1)
                fa = Fraction(a_num, d1)
                fb = Fraction(b_num, d2)
                op = random.choice(['+', '-'])
                if op == '-' and fa < fb:
                    fa, fb = fb, fa
                ans = fa + fb if op == '+' else fa - fb
                return f"{_frac(fa)} {op} {_frac(fb)} =", ans

        return self._safe_gen(_once)
    # ==================== 乘法 ====================
    def gen_mul_table(self):
        a_val = random.randint(2, 9)
        b_val = random.randint(2, 9)
        return f"{a_val} × {b_val} =", a_val * b_val

    def gen_mul_2x1(self):
        a_val = random.randint(12, 99)
        b_val = random.randint(2, 9)
        return f"{a_val} × {b_val} =", a_val * b_val

    def gen_mul_3x1(self):
        a_val = random.randint(100, 999)
        b_val = random.randint(2, 9)
        return f"{a_val} × {b_val} =", a_val * b_val

    def gen_mul_2x2(self):
        a_val = random.randint(12, 50)
        b_val = random.randint(11, 50)
        return f"{a_val} × {b_val} =", a_val * b_val

    def gen_mul_3x2(self):
        a_val = random.randint(100, 999)
        b_val = random.randint(10, 99)
        return f"{a_val} × {b_val} =", a_val * b_val

    def gen_mul_decimal(self):
        def _once():
            v = random.randint(1, 3)
            if v == 1:
                a_val = round(random.uniform(0.1, 9.9), 1)
                b_val = round(random.uniform(0.1, 9.9), 1)
                return f"{a_val} × {b_val} =", round(a_val * b_val, 2)
            elif v == 2:
                a_val = random.randint(2, 20)
                b_val = round(random.uniform(0.1, 9.9), 1)
                return f"{a_val} × {b_val} =", round(a_val * b_val, 2)
            else:
                a_val = round(random.uniform(1.00, 9.99), 2)
                b_val = random.randint(2, 9)
                return f"{a_val} × {b_val} =", round(a_val * b_val, 2)
        return self._safe_gen(_once)

    def gen_mul_fraction(self):
        a_frac = _make_frac()
        b_frac = _make_frac()
        return f"{_frac(a_frac)} × {_frac(b_frac)} =", a_frac * b_frac

    def gen_mul_simple(self):
        """
        乘法简便运算：仅分配律、结合律（凑整），无三位数乘两位数
        """
        if not hasattr(self, '_batch_hashes'):
            self._batch_hashes = set()

        max_attempts = 300
        for _ in range(max_attempts):
            v = random.choices(
                [1, 2, 3, 4, 5],
                weights=[0.30, 0.25, 0.25, 0.10, 0.10]
            )[0]

            expr = ""
            ans = 0

            # 类型1：提取公因数 a×b + a×c (b+c尽量整百)
            if v == 1:
                a = random.randint(2, 9)
                if random.random() < 0.6:
                    b = random.randint(11, 89)
                    c = 100 - b
                else:
                    total = random.choice([20, 30, 40, 50, 60, 70, 80, 90])
                    b = random.randint(10, total - 10)
                    c = total - b
                expr = f"{a} × {b} + {a} × {c} ="
                ans = a * (b + c)

            # 类型2：a×b + a 或 a×b - a
            elif v == 2:
                a = random.randint(11, 99)
                b = random.randint(2, 9)
                if random.random() < 0.5:
                    expr = f"{b} × {a} + {a} ="
                    ans = a * (b + 1)
                else:
                    expr = f"{a} × {b} - {a} ="
                    ans = a * (b - 1)

            # 类型3：a×101 - a 或 a×99 + a （显式分配律，不出现三位数乘两位数）
            elif v == 3:
                a = random.randint(11, 99)
                if random.random() < 0.5:
                    expr = f"{a} × 101 - {a} ="
                else:
                    expr = f"{a} × 99 + {a} ="
                ans = a * 100

            # 类型4：补项 a×c + b×c 且 a+b=100
            elif v == 4:
                a = random.randint(20, 80)
                b = 100 - a
                c = random.randint(11, 99)
                expr = f"{a} × {c} + {b} × {c} ="
                ans = (a + b) * c

            # 类型5：结合律 25×a×4 或 125×a×8（严格控制）
            else:  # v == 5
                if random.random() < 0.3:  # 30%概率实际生成
                    if random.random() < 0.5:
                        a = random.randint(2, 40)
                        expr = f"25 × {a} × 4 ="
                        ans = 25 * a * 4
                    else:
                        a = random.randint(2, 12)
                        expr = f"125 × {a} × 8 ="
                        ans = 125 * a * 8
                else:
                    continue

            if expr in self._batch_hashes:
                continue
            self._batch_hashes.add(expr)

            return expr, ans

        return "25 × 4 × 8 =", 800
    # ==================== 除法 ====================
    def gen_div_table(self):
        a_val = random.randint(2, 9)
        b_val = random.randint(2, 9)
        return f"{a_val * b_val} ÷ {a_val} =", b_val

    def gen_div_remainder(self):
        b_val = random.randint(2, 9)
        q_val = random.randint(2, 9)
        r_val = random.randint(1, b_val - 1)
        a_val = b_val * q_val + r_val
        return f"{a_val} ÷ {b_val} =", (q_val, r_val)

    def gen_div_exact(self):
        b_val = random.randint(2, 9)
        q_val = random.randint(10, 100)
        return f"{b_val * q_val} ÷ {b_val} =", q_val

    def gen_div_1digit(self):
        b_val = random.randint(2, 9)
        q_val = random.randint(10, 50)
        r_val = random.randint(1, b_val - 1)
        a_val = b_val * q_val + r_val
        return f"{a_val} ÷ {b_val} =", f"{q_val}……{r_val}"

    def gen_div_2digit(self):
        b_val = random.randint(11, 50)
        q_val = random.randint(10, 50)
        a_val = b_val * q_val
        return f"{a_val} ÷ {b_val} =", q_val

    def gen_div_decimal(self):
        def _once():
            a_val = random.randint(1, 9) * 10
            b_val = round(random.uniform(0.5, 9.9), 1)
            return f"{a_val} ÷ {b_val} =", round(a_val / b_val, 2)
        return self._safe_gen(_once)

    def gen_div_fraction(self):
        a_frac = _make_frac()
        b_frac = _make_frac()
        return f"{_frac(a_frac)} ÷ {_frac(b_frac)} =", a_frac / b_frac

    # ==================== 四则混合 ====================
    def _calc(self, a_val, op, b_val):
        if op == '+': return a_val + b_val
        if op == '-': return a_val - b_val
        if op == '×': return a_val * b_val
        if op == '÷':
            if b_val == 0:
                raise ValueError
            return a_val / b_val

    def gen_mix_addsub(self, use_bracket=False):
        for _ in range(500):
            nums = [random.randint(1, 9999) for _ in range(3)]
            ops = [random.choice(["+", "-"]), random.choice(["+", "-"])]
            # 确保中间结果非负且最终结果在万以内
            step1 = nums[0] + nums[1] if ops[0] == '+' else nums[0] - nums[1]
            if step1 < 0 or step1 > 9999:
                continue
            ans = step1 + nums[2] if ops[1] == '+' else step1 - nums[2]
            if ans < 0 or ans > 9999:
                continue
            if use_bracket:
                expr = f"({nums[0]} {ops[0]} {nums[1]}) {ops[1]} {nums[2]} ="
            else:
                expr = f"{nums[0]} {ops[0]} {nums[1]} {ops[1]} {nums[2]} ="
            return expr, ans
        return "100+200+300=", 600

    def gen_mix_addmul(self, use_bracket=False):
        """加减乘混合：随机安排乘法和加减法的位置，结果在万以内"""
        for _ in range(500):
            # 生成三个数，乘法因子适当控制以免过大
            a = random.randint(2, 99)
            b = random.randint(2, 99)
            c = random.randint(1, 999)

            # 乘积不能太大
            if a * b > 9999:
                continue

            # 随机选择组合形式
            form = random.randint(1, 4)

            if form == 1:  # a × b + c
                ans = a * b + c
                if ans > 9999: continue
                expr = f"{a} × {b} + {c} ="
            elif form == 2:  # a × b - c
                if a * b < c: continue
                ans = a * b - c
                expr = f"{a} × {b} - {c} ="
            elif form == 3:  # a + b × c
                ans = a + b * c
                if ans > 9999: continue
                expr = f"{a} + {b} × {c} ="
            else:  # a - b × c
                if a < b * c: continue
                ans = a - b * c
                expr = f"{a} - {b} × {c} ="

            # 如果启用括号，生成带括号的形式
            if use_bracket:
                bracket_form = random.randint(1, 2)
                if bracket_form == 1:
                    # (a + b) × c
                    a, b, c = random.randint(1, 99), random.randint(1, 99), random.randint(2, 99)
                    ans = (a + b) * c
                    if ans > 9999: continue
                    expr = f"({a} + {b}) × {c} ="
                else:
                    # (a - b) × c
                    a, b, c = random.randint(2, 99), random.randint(1, a - 1), random.randint(2, 99)
                    ans = (a - b) * c
                    if ans > 9999: continue
                    expr = f"({a} - {b}) × {c} ="

            return expr, ans

        # 保底
        return "12 + 34 × 5 =", 182

    def gen_mix_addmulsub(self, use_bracket=False):
        """
        加减乘除混合运算：
        - 四个数值，范围 1~999
        - 运算符随机（+、-、×、÷），位置随机
        - 不勾选括号时无括号；勾选括号时随机加一对括号
        - 结果非负且在 9999 以内
        - 使用标准运算优先级（先乘除后加减）
        """
        for _ in range(500):
            try:
                # 四个数值
                nums = [random.randint(1, 999) for _ in range(4)]
                # 三个运算符
                ops = [random.choice(['+', '-', '×', '÷']) for _ in range(3)]

                # 构建表达式字符串
                if use_bracket:
                    bracket_pos = random.randint(0, 2)
                    if bracket_pos == 0:
                        expr = f"({nums[0]} {ops[0]} {nums[1]}) {ops[1]} {nums[2]} {ops[2]} {nums[3]} ="
                    elif bracket_pos == 1:
                        expr = f"{nums[0]} {ops[0]} ({nums[1]} {ops[1]} {nums[2]}) {ops[2]} {nums[3]} ="
                    else:
                        expr = f"{nums[0]} {ops[0]} {nums[1]} {ops[1]} ({nums[2]} {ops[2]} {nums[3]}) ="
                else:
                    expr = f"{nums[0]} {ops[0]} {nums[1]} {ops[1]} {nums[2]} {ops[2]} {nums[3]} ="

                # 使用 Python eval 计算答案（标准运算优先级）
                eval_str = expr.rstrip(' =').replace('×', '*').replace('÷', '/')
                ans = eval(eval_str)

                # 结果检查
                if ans is None or ans < 0 or ans > 9999:
                    continue
                if isinstance(ans, float):
                    if abs(ans - round(ans, 2)) > 0.001:
                        continue
                    ans = round(ans, 2)
                if isinstance(ans, Fraction):
                    ans = float(ans)
                    if ans > 9999 or ans < 0:
                        continue
                    ans = round(ans, 2)

                return expr, ans
            except (ZeroDivisionError, ValueError, TypeError):
                continue

        # 保底题目
        return "123+456+789+101=", 1469

    def _calc(self, a, op, b):
        if op == '+': return a + b
        if op == '-': return a - b
        if op == '×': return a * b
        if op == '÷':
            if b == 0:
                raise ValueError
            # 尽量返回能整除的结果，否则返回小数
            result = a / b
            # 如果是整数，返回int；否则返回float
            if result.is_integer():
                return int(result)
            return result

    def gen_mix_decimal(self, use_bracket=False):
        for _ in range(500):
            try:
                a_val = round(random.uniform(0.1, 10), 1)
                b_val = round(random.uniform(0.1, 10), 1)
                c_val = round(random.uniform(0.1, 10), 1)
                op1 = random.choice(['+', '-', '×', '÷'])
                op2 = random.choice(['+', '-'])
                if op1 == '÷' and b_val == 0:
                    continue
                if use_bracket:
                    expr = f"({a_val} {op1} {b_val}) {op2} {c_val} ="
                else:
                    expr = f"{a_val} {op1} {b_val} {op2} {c_val} ="
                temp = self._calc(a_val, op1, b_val)
                ans = self._calc(temp, op2, c_val)
                return expr, round(ans, 2)
            except:
                continue
        return "1.2+2.3=", 3.5

    def gen_mix_fraction(self, use_bracket=False):
        for _ in range(500):
            try:
                a_frac = _make_frac()
                b_frac = _make_frac()
                c_frac = _make_frac()
                op1 = random.choice(['+', '-'])
                if use_bracket:
                    expr = f"({_frac(a_frac)} {op1} {_frac(b_frac)}) × {_frac(c_frac)} ="
                else:
                    expr = f"{_frac(a_frac)} {op1} {_frac(b_frac)} × {_frac(c_frac)} ="
                temp = (a_frac + b_frac) if op1 == '+' else (a_frac - b_frac)
                ans = temp * c_frac
                return expr, ans
            except:
                continue
        return f"{_frac(Fraction(1, 2))} + {_frac(Fraction(1, 2))} =", Fraction(1, 1)

    # ==================== 提升题 ====================
    def gen_find_rule(self):
        v = random.randint(1, 5)
        if v == 1:
            start = random.randint(1, 20)
            diff = random.randint(2, 10)
            nums = [start + diff * i for i in range(4)]
            ans = start + diff * 4
            return f"找规律：{nums[0]}，{nums[1]}，{nums[2]}，{nums[3]}，____", ans
        elif v == 2:
            start = random.randint(1, 5)
            ratio = random.randint(2, 3)
            nums = [start * ratio ** i for i in range(4)]
            ans = start * ratio ** 4
            return f"找规律：{nums[0]}，{nums[1]}，{nums[2]}，{nums[3]}，____", ans
        elif v == 3:
            start = random.randint(1, 10)
            nums = [start]
            for i in range(1, 5):
                nums.append(nums[-1] + (i if i % 2 == 1 else -i))
            ans = nums[-1] + (5 if len(nums) % 2 == 0 else -5)
            return f"找规律：{nums[0]}，{nums[1]}，{nums[2]}，{nums[3]}，____", ans
        elif v == 4:
            start = random.randint(1, 5)
            nums = [(start + i) ** 2 for i in range(4)]
            ans = (start + 4) ** 2
            return f"找规律：{nums[0]}，{nums[1]}，{nums[2]}，{nums[3]}，____", ans
        else:
            a, b = random.randint(1, 10), random.randint(1, 10)
            nums = [a, b]
            for i in range(3):
                nums.append(nums[-1] + nums[-2])
            ans = nums[-1] + nums[-2]
            return f"找规律：{nums[0]}，{nums[1]}，{nums[2]}，{nums[3]}，____", ans

    def gen_arithmetic(self):
        v = random.randint(1, 5)
        start = random.randint(1, 20)
        diff = random.randint(2, 5)
        n = random.randint(5, 10)
        if v == 1:
            ans = start + (n - 1) * diff
            return f"等差数列：首项{start}，公差{diff}，第{n}项是____", ans
        elif v == 2:
            last = start + (n - 1) * diff
            total = n * (start + last) // 2
            return f"等差数列：首项{start}，公差{diff}，共{n}项，前{n}项之和是____", total
        elif v == 3:
            last = start + (n - 1) * diff
            return f"等差数列：首项{start}，末项{last}，公差{diff}，共有几项？", n
        elif v == 4:
            last = start + (n - 1) * diff
            total = n * (start + last) // 2
            return f"等差数列：首项{start}，末项{last}，共{n}项，公差是多少？", diff
        else:
            total = n * (2 * start + (n - 1) * diff) // 2
            last = start + (n - 1) * diff
            return f"等差数列：首项{start}，公差{diff}，前{n}项之和为{total}，末项是____", last

    def gen_simple_calc(self):
        v = random.randint(1, 5)
        if v == 1:
            a = random.randint(2, 9)
            b = random.randint(11, 89)
            return f"{a} × {b} + {a} × {100 - b} =", a * 100
        elif v == 2:
            a = random.randint(2, 20)
            return f"99 × {a} =", 100 * a - a
        elif v == 3:
            a = random.randint(5, 15)
            b = random.randint(1, a - 1)
            return f"({a}+{b})×({a}-{b}) =", (a + b) * (a - b)
        elif v == 4:
            a = random.randint(2, 9)
            b = random.randint(2, 9)
            return f"{a}×{a}×{b}×{b} =", (a * b) ** 2
        else:
            a = random.randint(2, 20)
            return f"{a}×50 =", a * 50

    def gen_frac_skill(self):
        v = random.randint(1, 4)
        if v == 1:
            n = random.randint(2, 8)
            return f"1/{n} + 1/{n + 1} =", Fraction(1, n) + Fraction(1, n + 1)
        elif v == 2:
            den = random.randint(2, 6)
            a = random.randint(1, den - 1)
            b = den - a
            return f"{_frac(Fraction(a, den))} + {_frac(Fraction(b, den))} = ____（用最简分数表示）", Fraction(1, 1)
        elif v == 3:
            a = random.randint(2, 8)
            b = random.choice([4, 8, 12, 25])
            return f"{a} × {Fraction(1, b)} + {a} × {Fraction(1, b)} =", a * Fraction(1, b) + a * Fraction(1, b)
        else:
            n = random.randint(2, 6)
            total = Fraction(0)
            parts = []
            for i in range(1, n + 1):
                total += Fraction(1, i)
                parts.append(f"1/{i}")
            return f"{' + '.join(parts)} = ____（用最简分数表示）", total

    def gen_new_op(self):
        v = random.randint(1, 6)
        if v == 1:
            a, b = random.randint(2, 9), random.randint(2, 9)
            return f"定义 a △ b = a×b + a，求 {a} △ {b}", a * b + a
        elif v == 2:
            a, b = random.randint(2, 15), random.randint(2, 15)
            if a > b:
                return f"定义 a △ b = a+b（当a>b时），a×b（当a≤b时），求 {a} △ {b}", a + b
            else:
                return f"定义 a △ b = a+b（当a>b时），a×b（当a≤b时），求 {a} △ {b}", a * b
        elif v == 3:
            a = random.randint(1, 10)
            b = random.randint(2, 6)
            ans = b * a + b * (b - 1) // 2
            return f"定义 a ★ b = a+(a+1)+…+(a+b-1)，求 {a} ★ {b}", ans
        elif v == 4:
            a = random.randint(2, 5)
            b = random.randint(2, 3)
            return f"定义 a ◆ b = a的b次方，求 {a} ◆ {b}", a ** b
        elif v == 5:
            a = random.randint(10, 999)
            b = random.randint(1, 9)
            digit_sum = sum(int(d) for d in str(a))
            return f"定义 a ☆ b = a的各位数字之和 + b，求 {a} ☆ {b}", digit_sum + b
        else:
            a, b = random.randint(2, 9), random.randint(2, 9)
            return f"定义 a ▲ b = a×b - a，求 {a} ▲ {b}", a * b - a

    def gen_sum_diff(self):
        v = random.randint(1, 3)
        if v == 1:
            total = random.randint(20, 200)
            diff = random.randint(2, 30)
            big = (total + diff) // 2
            small = total - big
            return f"甲乙两数之和是{total}，差是{diff}，求这两个数。", f"{big}和{small}"
        elif v == 2:
            total = random.randint(20, 100)
            ratio = random.randint(2, 5)
            small = total // (ratio + 1)
            big = total - small
            return f"甲乙两数之和是{total}，甲是乙的{ratio}倍，求甲乙各是多少？", f"甲{big}，乙{small}"
        else:
            diff = random.randint(2, 20)
            ratio = random.randint(2, 4)
            small = diff // (ratio - 1) if diff % (ratio - 1) == 0 else diff
            big = small * ratio
            return f"甲乙两数之差是{diff}，甲是乙的{ratio}倍，求甲乙各是多少？", f"甲{big}，乙{small}"

    def gen_age(self):
        v = random.randint(1, 4)
        if v == 1:
            child = random.randint(5, 12)
            years = random.randint(5, 15)
            father_now = random.randint(28, 45)
            child_then = child
            father_then = father_now - years
            ratio = father_then // child_then if child_then > 0 else 2
            target_child = child_then
            target_father = target_child * ratio
            actual_father = father_now
            real_ratio = (actual_father - years) / (child) if child > 0 else 2
            return f"小明今年{child}岁，爸爸今年{father_now}岁，{years}年前爸爸的年龄是小明的几倍？", (father_now - years) // child
        elif v == 2:
            child = random.randint(5, 12)
            father = child + random.randint(22, 35)
            years = random.randint(3, 10)
            return f"小明今年{child}岁，爸爸今年{father}岁，{years}年后父子年龄之和是多少？", child + father + years * 2
        elif v == 3:
            a = random.randint(5, 15)
            b = a + random.randint(1, 5)
            c = b + random.randint(1, 5)
            return f"三个小朋友，小明{a}岁，小红{b}岁，小刚{c}岁，最大的比最小的大几岁？", c - a
        else:
            child = random.randint(4, 10)
            diff = random.randint(22, 35)
            father = child + diff
            return f"爸爸比小明大{diff}岁，爸爸今年{father}岁，小明今年几岁？", child

    def gen_tree(self):
        v = random.randint(1, 4)
        length = random.randint(50, 500)
        space = random.choice([3, 4, 5, 6, 8, 10])
        if v == 1:
            return f"一条路长{length}米，每隔{space}米种一棵树，两端都种，共种多少棵？", (length // space) + 1
        elif v == 2:
            return f"一条路长{length}米，每隔{space}米种一棵树，只种一端，共种多少棵？", length // space
        elif v == 3:
            return f"一条路长{length}米，每隔{space}米种一棵树，两端都不种，共种多少棵？", (length // space) - 1
        else:
            side = random.randint(2, 6)
            return f"一个正方形方阵，每边站{side}人，四边共站多少人？（角上的人只算一次）", 4 * side - 4

    def gen_chicken_rabbit(self):
        v = random.randint(1, 7)
        if v == 1:
            chickens = random.randint(5, 30)
            rabbits = random.randint(5, 20)
            heads = chickens + rabbits
            legs = chickens * 2 + rabbits * 4
            return f"鸡兔同笼，共有{heads}个头，{legs}只脚，鸡兔各几只？", f"鸡{chickens}只，兔{rabbits}只"
        elif v == 2:
            a = random.randint(5, 20)
            b = random.randint(3, 10)
            heads = a + b
            legs = a * 3 + b * 8
            return f"笼中有三脚蛛和八爪章鱼共{heads}只，脚共{legs}只，三脚蛛和八爪章鱼各几只？", f"三脚蛛{a}只，八爪章鱼{b}只"
        elif v == 3:
            chickens = random.randint(8, 30)
            rabbits = random.randint(5, 20)
            heads = chickens + rabbits
            legs = chickens * 2 + rabbits * 4
            return f"停车场有自行车和汽车共{heads}辆，轮子共{legs}个，自行车和汽车各几辆？", f"自行车{chickens}辆，汽车{rabbits}辆"
        elif v == 4:
            ducks = random.randint(5, 25)
            cows = random.randint(3, 15)
            heads = ducks + cows
            legs = ducks * 2 + cows * 4
            return f"农场里鸭和牛共{heads}只，数脚共{legs}只，鸭和牛各几只？", f"鸭{ducks}只，牛{cows}只"
        elif v == 5:
            chickens = random.randint(5, 20)
            rabbits = random.randint(5, 15)
            heads = chickens + rabbits
            legs = chickens * 2 + rabbits * 4
            return f"鸡和兔关在同一个笼子里，共有{heads}个头，{legs}只脚，问鸡有多少只？", chickens
        elif v == 6:
            chickens = random.randint(5, 25)
            rabbits = random.randint(5, 15)
            heads = chickens + rabbits
            legs = chickens * 2 + rabbits * 4
            diff = abs(chickens - rabbits)
            return f"鸡兔共{heads}只，脚共{legs}只，鸡比兔多几只？", diff
        else:
            chickens = random.randint(5, 20)
            rabbits = random.randint(5, 15)
            heads = chickens + rabbits
            legs = chickens * 2 + rabbits * 4
            return f"笼中有鸡和兔共{heads}只，脚共{legs}只，兔有多少只？", rabbits

    def gen_duck(self):
        v = random.randint(1, 6)
        if v == 1:
            people = random.randint(3, 15)
            per1 = random.randint(2, 5)
            short = random.randint(1, 5)
            per2 = per1 + 1
            extra = per2 * people - per1 * people - short
            return f"分苹果，每人{per1}个少{short}个，每人{per2}个多{extra}个，有几个人？", people
        elif v == 2:
            people = random.randint(3, 12)
            per1 = random.randint(3, 6)
            short = random.randint(2, 8)
            per2 = per1 + 1
            extra = per2 * people - per1 * people - short
            return f"坐船，每条船坐{per1}人少{short}人，每条船坐{per2}人多{extra}人，有几条船？", people
        elif v == 3:
            people = random.randint(3, 12)
            per1 = random.randint(3, 6)
            per2 = per1 + random.randint(1, 3)
            surplus1 = random.randint(5, 15)
            surplus2 = surplus1 - (per2 - per1) * people
            while surplus2 <= 0:
                people = random.randint(3, 12)
                surplus2 = surplus1 - (per2 - per1) * people
            return f"分苹果，每人{per1}个剩{surplus1}个，每人{per2}个剩{surplus2}个，有几个人？", people
        elif v == 4:
            people = random.randint(3, 12)
            per1 = random.randint(3, 6)
            per2 = per1 + random.randint(1, 3)
            deficit1 = random.randint(2, 8)
            deficit2 = deficit1 + (per1 - per2) * people
            while deficit2 <= 0:
                people = random.randint(3, 12)
                deficit2 = deficit1 + (per1 - per2) * people
            return f"坐船，每条船坐{per1}人少{deficit1}人，每条船坐{per2}人少{deficit2}人，有几条船？", people
        elif v == 5:
            people = random.randint(3, 12)
            per1 = random.randint(2, 5)
            short = random.randint(1, 5)
            per2 = per1 + 1
            extra = per2 * people - per1 * people - short
            return f"分书，每人{per1}本少{short}本，每人{per2}本多{extra}本，有几个人？", people
        else:
            people = random.randint(3, 15)
            per = random.randint(3, 8)
            total = people * per + random.randint(1, per - 1)
            r = total % per
            return f"有{people}人分{total}个苹果，每人分几个还剩几个？", f"{per}个剩{r}个"

    def gen_project(self):
        v = random.randint(1, 5)
        if v == 1:
            a_days = random.randint(5, 20)
            b_days = random.randint(5, 20)
            ans = Fraction(a_days * b_days, a_days + b_days)
            return f"一项工程，甲单独做{a_days}天完成，乙单独做{b_days}天完成，合作几天完成？", ans
        elif v == 2:
            a_days = random.randint(6, 20)
            b_days = random.randint(6, 20)
            work_a = Fraction(1, a_days)
            work_b = Fraction(1, b_days)
            ans = Fraction(1, 2) / (work_a + work_b)
            return f"一项工程，甲单独做{a_days}天完成，乙单独做{b_days}天完成，合作完成一半需要几天？", ans
        elif v == 3:
            a_days = random.randint(6, 20)
            b_days = random.randint(6, 20)
            work_a = Fraction(1, a_days)
            work_b = Fraction(1, b_days)
            ans = Fraction(1) / (work_a + work_b)
            return f"一项工程，甲每天完成全部的{work_a}，乙每天完成全部的{work_b}，合作几天完成？", ans
        elif v == 4:
            a_days = random.randint(8, 25)
            b_days = random.randint(8, 25)
            work_b = Fraction(1, b_days)
            work_a = work_b * random.randint(2, 4)
            ans = Fraction(1) / (work_a + work_b)
            return f"一项工程，乙单独做{b_days}天完成，甲的工作效率是乙的{work_a // work_b}倍，甲乙合作几天完成？", ans
        else:
            a_days = random.randint(5, 15)
            b_days = random.randint(5, 15)
            work_a = Fraction(1, a_days)
            work_b = Fraction(1, b_days)
            ans = Fraction(1, 3) / (work_a + work_b)
            return f"一项工程，甲单独做{a_days}天完成，乙单独做{b_days}天完成，合作完成三分之一需要几天？", ans

    def gen_form(self):
        v = random.randint(1, 5)
        if v == 1:
            distance = random.randint(100, 500)
            va = random.randint(20, 60)
            vb = random.randint(20, 60)
            ans = distance / (va + vb)
            return f"甲乙相距{distance}千米，相向而行，甲速{va}千米/时，乙速{vb}千米/时，几时相遇？", f"{round(ans, 2)}时"
        elif v == 2:
            distance = random.randint(100, 500)
            va = random.randint(30, 80)
            vb = random.randint(20, 60)
            ans = distance / (va - vb)
            return f"甲乙相距{distance}千米，同向而行，甲速{va}千米/时，乙速{vb}千米/时，甲追上乙要几时？", f"{round(ans, 2)}时"
        elif v == 3:
            distance = random.randint(100, 500)
            va = random.randint(20, 50)
            vb = random.randint(20, 50)
            speed = va + vb
            ans = distance / speed * 2
            return f"甲乙相距{distance}千米，相向而行，甲速{va}千米/时，乙速{vb}千米/时，相遇后继续走，几时后再次相遇？", f"{round(ans, 2)}时"
        elif v == 4:
            distance = random.randint(200, 600)
            va = random.randint(30, 60)
            vb = random.randint(20, 50)
            ans = distance / (va + vb)
            return f"甲乙分别从两地同时出发，相距{distance}千米，甲速{va}千米/时，乙速{vb}千米/时，几时后相遇？", f"{round(ans, 2)}时"
        else:
            distance = random.randint(100, 400)
            va = random.randint(40, 80)
            vb = random.randint(20, 40)
            gap = random.randint(20, 60)
            ans = (distance + gap) / (va - vb)
            return f"甲在乙前方{gap}千米处，同向而行，甲速{va}千米/时，乙速{vb}千米/时，乙追上甲要几时？", f"{round(ans, 2)}时"

    def gen_concentration(self):
        v = random.randint(1, 6)
        if v == 1:
            salt = random.randint(10, 50)
            water = random.randint(100, 300)
            pct = round(salt / (salt + water) * 100, 1)
            return f"盐{salt}克溶入水{water}克中，盐水浓度是多少？", f"{pct}%"
        elif v == 2:
            a_salt = random.randint(10, 30)
            a_water = random.randint(80, 200)
            b_salt = random.randint(10, 30)
            b_water = random.randint(80, 200)
            total_salt = a_salt + b_salt
            total_water = a_water + b_water
            pct = round(total_salt / (total_salt + total_water) * 100, 1)
            return f"将浓度不同的两杯盐水混合：第一杯含盐{a_salt}克、水{a_water}克，第二杯含盐{b_salt}克、水{b_water}克。混合后浓度是多少？", f"{pct}%"
        elif v == 3:
            salt = random.randint(10, 50)
            water = random.randint(100, 300)
            add_water = random.randint(50, 200)
            pct = round(salt / (salt + water + add_water) * 100, 1)
            return f"盐{salt}克溶入水{water}克中，再加入{add_water}克水，稀释后浓度是多少？", f"{pct}%"
        elif v == 4:
            salt = random.randint(10, 50)
            water = random.randint(100, 300)
            total = salt + water
            add_salt = random.randint(5, 20)
            pct = round((salt + add_salt) / (total + add_salt) * 100, 1)
            return f"盐{salt}克溶入水{water}克中，再加入{add_salt}克盐，浓度变为多少？", f"{pct}%"
        elif v == 5:
            total = random.randint(100, 300)
            pct = random.choice([5, 10, 15, 20])
            salt = total * pct // 100
            evap = random.randint(20, 80)
            new_pct = round(salt / (total - evap) * 100, 1)
            return f"浓度{pct}%的盐水{total}克，蒸发掉{evap}克水后浓度是多少？", f"{new_pct}%"
        else:
            total = random.randint(100, 300)
            pct = random.choice([5, 10, 15, 20])
            salt = total * pct // 100
            return f"浓度{pct}%的盐水{total}克，含盐多少克？", f"{salt}克"

    def gen_perimeter(self):
        v = random.randint(1, 5)
        if v == 1:
            l_val = random.randint(5, 20)
            w_val = random.randint(3, 15)
            return f"长方形长{l_val}厘米宽{w_val}厘米，求周长。", (l_val + w_val) * 2
        elif v == 2:
            l_val = random.randint(5, 20)
            w_val = random.randint(3, 15)
            return f"长方形长{l_val}厘米宽{w_val}厘米，求面积。", l_val * w_val
        elif v == 3:
            side = random.randint(3, 15)
            return f"正方形边长{side}厘米，求面积。", side * side
        elif v == 4:
            base = random.randint(4, 20)
            height = random.randint(3, 15)
            return f"三角形底{base}厘米，高{height}厘米，求面积。", base * height // 2
        else:
            r = random.randint(2, 10)
            area = round(3.14 * r * r, 2)
            return f"圆的半径是{r}厘米，求面积。（π取3.14）", area

    def gen_3d_graph(self):
        v = random.randint(1, 6)
        if v == 1:
            a = random.randint(3, 10)
            return f"棱长{a}厘米的正方体，求体积。", a ** 3
        elif v == 2:
            l = random.randint(3, 15)
            w = random.randint(3, 10)
            h = random.randint(3, 10)
            return f"长方体长{l}厘米、宽{w}厘米、高{h}厘米，求体积。", l * w * h
        elif v == 3:
            l = random.randint(3, 15)
            w = random.randint(3, 10)
            h = random.randint(3, 10)
            area = 2 * (l * w + l * h + w * h)
            return f"长方体长{l}厘米、宽{w}厘米、高{h}厘米，求表面积。", area
        elif v == 4:
            a = random.randint(3, 10)
            return f"棱长{a}厘米的正方体，求表面积。", 6 * a * a
        elif v == 5:
            r = random.randint(2, 8)
            h = random.randint(3, 12)
            ans = round(3.14 * r * r * h, 2)
            return f"圆柱底面半径{r}厘米，高{h}厘米，求体积。（π取3.14）", ans
        else:
            a = random.randint(3, 10)
            total = a * 12
            return f"棱长{a}厘米的正方体，所有棱长之和是多少厘米？", total

    def gen_equal_area(self):
        v = random.randint(1, 5)
        if v == 1:
            area = random.randint(12, 48)
            return f"三角形和平行四边形等底等高，平行四边形面积{area}平方厘米，三角形面积是多少？", area // 2
        elif v == 2:
            base = random.randint(4, 20)
            height = random.randint(3, 15)
            tri_area = base * height // 2
            return f"三角形底{base}厘米、高{height}厘米，与它等底等高的平行四边形面积是多少？", tri_area * 2
        elif v == 3:
            area = random.randint(10, 50)
            return f"三角形面积{area}平方厘米，与它等底等高的梯形面积是多少？（梯形面积是三角形的1.5倍）", round(area * 1.5, 1)
        elif v == 4:
            base = random.randint(4, 12)
            height = random.randint(3, 10)
            area = base * height
            return f"平行四边形底{base}厘米、高{height}厘米，与它等底等高的长方形面积是多少？", area
        else:
            area = random.randint(12, 48)
            return f"一个梯形面积{area}平方厘米，与它等高的三角形（三角形的底等于梯形上底加下底），三角形面积是多少？", area

    def gen_graph_count(self):
        v = random.randint(1, 5)
        if v == 1:
            n = random.randint(3, 8)
            return f"{n}个点两两连线，共能连多少条线段？", n * (n - 1) // 2
        elif v == 2:
            n = random.randint(2, 5)
            m = random.randint(2, 5)
            angles = n * m * (n - 1) * (m - 1) // 4
            return f"{n}条横线和{m}条竖线相交，共能组成多少个角？（不含平角）", angles
        elif v == 3:
            rows = random.randint(2, 5)
            cols = random.randint(2, 5)
            rect_count = rows * cols * (rows + 1) * (cols + 1) // 4
            return f"一个{rows}行{cols}列的方格网中共有多少个长方形（含正方形）？", rect_count
        elif v == 4:
            n = random.randint(3, 8)
            tri_count = n * (n - 1) * (n - 2) // 6
            return f"{n}个点中任取3个点，共能组成多少个三角形？（无三点共线）", tri_count
        else:
            n = random.randint(3, 6)
            lines = n * (n - 1) // 2
            return f"一个平面上有{n}条直线，最多能把平面分成几部分？", lines + 1

    def gen_graph_split(self):
        v = random.randint(1, 5)
        if v == 1:
            n = random.randint(2, 8)
            return f"一条线段，{n}个点（不含端点），能把线段分成几段？", n + 1
        elif v == 2:
            n = random.randint(1, 5)
            ans = 1 + n * (n + 1) // 2
            return f"一个圆内画{n}条直线（两两相交，无三线共点），最多能把圆分成几部分？", ans
        elif v == 3:
            rows = random.randint(2, 5)
            cols = random.randint(2, 5)
            ans = rows * cols
            return f"一个{rows}行{cols}列的方格图中共有多少个小长方形？", ans
        elif v == 4:
            n = random.randint(2, 6)
            return f"一个三角形，画{n}条平行于底边的线，把三角形分成几部分？", n + 1
        else:
            n = random.randint(2, 6)
            return f"一张纸对折{n}次后，最多能分成几层？", 2 ** n

    def gen_odd_even(self):
        v = random.randint(1, 6)
        if v == 1:
            a = random.randint(1, 50)
            b = random.randint(1, 50)
            return f"{a} + {b} 的和是奇数还是偶数？", "奇数" if (a + b) % 2 else "偶数"
        elif v == 2:
            a = random.randint(1, 20)
            b = random.randint(1, 20)
            return f"{a} × {b} 的积是奇数还是偶数？", "奇数" if (a * b) % 2 else "偶数"
        elif v == 3:
            n = random.randint(3, 10)
            total = 2 * n
            return f"1到{total}中，有多少个奇数？", n
        elif v == 4:
            cases = [
                ("两个奇数的和", "偶数"),
                ("两个偶数的和", "偶数"),
                ("一个奇数和一个偶数的和", "奇数"),
            ]
            desc, ans = random.choice(cases)
            return f"{desc}是什么数？", ans
        elif v == 5:
            cases = [
                ("两个奇数的积", "奇数"),
                ("一个奇数和一个偶数的积", "偶数"),
                ("两个偶数的积", "偶数"),
            ]
            desc, ans = random.choice(cases)
            return f"{desc}是什么数？", ans
        else:
            a = random.randint(5, 30)
            result = random.randint(a + 2, a + 30)
            if result % 2 == a % 2:
                result += 1
            blank_parity = "奇数" if (result - a) % 2 else "偶数"
            return f"{a} + （ ） = {result}，括号中应填奇数还是偶数？", blank_parity

    def gen_whole_div(self):
        v = random.randint(1, 5)
        if v == 1:
            num = random.randint(100, 999)
            div = random.choice([2, 3, 5, 9])
            return f"{num} 能否被 {div} 整除？", "能" if num % div == 0 else "不能"
        elif v == 2:
            d1, d2 = random.sample([2, 3, 5, 7], 2)
            lcm = d1 * d2 // math.gcd(d1, d2)
            return f"一个数既能被{d1}整除又能被{d2}整除，这个数最小是多少？", lcm
        elif v == 3:
            n = random.randint(2, 5)
            divs = random.sample([2, 3, 5, 7, 11], n)
            lcm_val = divs[0]
            for d in divs[1:]:
                lcm_val = lcm_val * d // math.gcd(lcm_val, d)
            return f"一个数能被{'、'.join(str(d) for d in divs)}整除，这个数最小是多少？", lcm_val
        elif v == 4:
            num = random.randint(100, 999)
            div = random.choice([2, 3, 5])
            q, r = divmod(num, div)
            return f"{num} ÷ {div} =", f"{q}……{r}" if r else str(q)
        else:
            n = random.randint(3, 9)
            count = 0
            for i in range(1, n + 1):
                if n % i == 0:
                    count += 1
            return f"{n} 有几个因数？", count

    def gen_remainder(self):
        v = random.randint(1, 5)
        if v == 1:
            a = random.randint(20, 200)
            b = random.randint(3, 9)
            return f"{a} ÷ {b} 的余数是多少？", a % b
        elif v == 2:
            d1 = random.randint(3, 7)
            d2 = random.randint(3, 7)
            r = random.randint(1, min(d1, d2) - 1)
            lcm = d1 * d2 // math.gcd(d1, d2)
            ans = lcm + r
            return f"一个数除以{d1}余{r}，除以{d2}也余{r}，这个数最小是多少？", ans
        elif v == 3:
            n = random.randint(1, 5)
            base = random.randint(2, 5)
            div = random.randint(3, 7)
            ans = pow(base, n, div)
            return f"{base}的{n}次方除以{div}的余数是多少？", ans
        elif v == 4:
            a = random.randint(10, 50)
            b = random.randint(3, 8)
            r = a % b
            return f"{a}除以{b}余{r}，再除以{b}余几？", r
        else:
            d1 = random.randint(3, 7)
            d2 = random.randint(3, 7)
            r1 = random.randint(1, d1 - 1)
            r2 = random.randint(1, d2 - 1)
            while r1 == r2:
                r2 = random.randint(1, d2 - 1)
            lcm = d1 * d2 // math.gcd(d1, d2)
            ans = None
            for i in range(lcm, lcm * d1 * d2 + 1):
                if i % d1 == r1 and i % d2 == r2:
                    ans = i
                    break
            return f"一个数除以{d1}余{r1}，除以{d2}余{r2}，这个数最小是多少？（{d1}和{d2}互质）", ans

    def gen_prime(self):
        v = random.randint(1, 5)
        if v == 1:
            num = random.randint(10, 50)
            is_prime = num >= 2 and all(num % i != 0 for i in range(2, int(math.sqrt(num)) + 1))
            return f"{num} 是质数还是合数？", "质数" if is_prime else "合数"
        elif v == 2:
            num = random.randint(12, 100)
            factors = []
            n = num
            for p in range(2, int(math.sqrt(n)) + 1):
                while n % p == 0:
                    factors.append(p)
                    n //= p
            if n > 1:
                factors.append(n)
            return f"将{num}分解质因数。", "×".join(str(f) for f in factors)
        elif v == 3:
            even_num = random.choice([10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30])
            primes = [p for p in range(2, even_num) if all(p % i != 0 for i in range(2, int(p**0.5)+1))]
            ans = None
            for p in primes:
                q = even_num - p
                if q >= 2 and all(q % i != 0 for i in range(2, int(q**0.5)+1)):
                    ans = f"{p}和{q}"
                    break
            return f"两个质数之和是{even_num}，这两个质数分别是？", ans
        elif v == 4:
            num = random.randint(2, 20)
            is_sq = int(math.isqrt(num)) ** 2 == num
            return f"{num} 是不是完全平方数？", "是" if is_sq else "不是"
        else:
            n = random.randint(20, 50)
            count = sum(1 for i in range(2, n+1) if all(i % j != 0 for j in range(2, int(i**0.5)+1)))
            return f"2到{n}中，有多少个质数？", count

    def gen_gcd_lcm(self):
        v = random.randint(1, 5)
        a_val = random.randint(10, 60)
        b_val = random.randint(10, 60)
        if v == 1:
            return f"求{a_val}和{b_val}的最大公约数。", math.gcd(a_val, b_val)
        elif v == 2:
            return f"求{a_val}和{b_val}的最小公倍数。", a_val * b_val // math.gcd(a_val, b_val)
        elif v == 3:
            g = math.gcd(a_val, b_val)
            l = a_val * b_val // g
            return f"已知{a_val}和{b_val}的最大公约数是{g}，它们的最小公倍数是多少？", l
        elif v == 4:
            g = math.gcd(a_val, b_val)
            l = a_val * b_val // g
            return f"已知{a_val}和{b_val}的最小公倍数是{l}，它们的最大公约数是多少？", g
        else:
            c = random.randint(10, 40)
            g = math.gcd(a_val, b_val)
            return f"求{a_val}、{b_val}和{c}三个数的最大公约数。", math.gcd(g, c)

    def gen_logic(self):
        v = random.randint(1, 5)
        if v == 1:
            days = ["星期一", "星期二", "星期三", "星期四", "星期五"]
            a, b = random.sample(days, 2)
            third = [d for d in days if d != a and d != b][random.randint(0, 2)]
            return f"小明说：'今天不是{a}也不是{b}。'小红说：'今天是{third}。'如果只有一人说对了，今天是星期几？", third
        elif v == 2:
            jobs = ["医生", "教师", "工程师", "律师"]
            a, b, c = random.sample(jobs, 3)
            answer = random.choice(jobs)
            return f"A说：'我是{a}。'B说：'我是{b}。'C说：'我是{c}。'已知只有一人说了真话，谁是{answer}？如果回答职业，{a}说的是假话，那么说真话的人的职业是什么？", a
        elif v == 3:
            names = random.sample(["小明", "小红", "小刚", "小丽", "小华"], 4)
            order = list(range(4))
            random.shuffle(order)
            chain = "，".join(f"{names[order[i]]}比{names[order[i+1]]}重" for i in range(3))
            return f"比体重：{chain}，谁最轻？", names[order[3]]
        elif v == 4:
            a = random.randint(1, 9)
            b = random.randint(1, 9)
            while b == a:
                b = random.randint(1, 9)
            product = a * b
            sum_val = a + b
            return f"两个一位数，它们的积是{product}，和是{sum_val}，这两个数分别是？", f"{min(a,b)}和{max(a,b)}"
        else:
            ages = [random.randint(5, 12) for _ in range(3)]
            ages_sorted = sorted(ages)
            total = sum(ages)
            oldest = ages_sorted[2]
            youngest = ages_sorted[0]
            return f"三个小朋友，最大{oldest}岁，最小{youngest}岁，三人年龄之和是{total}岁，中间的小朋友几岁？", ages_sorted[1]

    def gen_arrange(self):
        v = random.randint(1, 4)
        if v == 1:
            n = random.randint(3, 8)
            time_per_side = random.choice([1, 2, 3])
            if n == 1:
                ans = time_per_side * 2
            elif n == 2:
                ans = time_per_side * 2
            else:
                ans = n * time_per_side
            return f"煎{n}张饼，每面要{time_per_side}分钟，锅里每次最多放2张，最少要几分钟？", ans
        elif v == 2:
            wash = random.randint(2, 5)
            boil = random.randint(5, 15)
            steep = random.randint(3, 8)
            ans = boil + steep
            return f"烧水泡茶：洗水壶{wash}分钟，烧水{boil}分钟，沏茶{steep}分钟。合理安排最少要几分钟？（洗水壶后才能烧水，水开后才能沏茶）", ans
        elif v == 3:
            n = random.randint(3, 6)
            fill_time = random.randint(2, 5)
            carry_time = random.randint(1, 3)
            ans = fill_time + (n - 1) * carry_time + fill_time
            return f"给{n}个桶接水，每桶接满要{fill_time}分钟，从水龙头提到目的地要{carry_time}分钟，只有1个水龙头，最少要几分钟？（假设提起后可以继续接下一桶）", ans
        else:
            cap = random.randint(2, 5)
            total = random.randint(cap + 1, cap * 4)
            ans = math.ceil(total / cap)
            return f"一条船每次最多坐{cap}人，有{total}人要过河，至少需要几次？", ans

    def gen_best(self):
        v = random.randint(1, 5)
        if v == 1:
            total = random.randint(6, 20)
            half = total // 2
            ans = half * (total - half)
            return f"a+b={total}，a和b都是正整数，a×b的最大值是多少？", ans
        elif v == 2:
            product = random.randint(4, 36)
            best_sum = None
            for i in range(1, product + 1):
                if product % i == 0:
                    s = i + product // i
                    if best_sum is None or s < best_sum:
                        best_sum = s
            return f"a×b={product}，a和b都是正整数，a+b的最小值是多少？", best_sum
        elif v == 3:
            perimeter = random.randint(8, 40)
            if perimeter % 2 == 0:
                half_p = perimeter // 2
                best_area = (half_p // 2) * (half_p - half_p // 2)
            else:
                best_area = (perimeter // 4) * (perimeter // 4)
            return f"用{perimeter}厘米长的铁丝围一个长方形（边长为整数厘米），面积最大是多少平方厘米？", best_area
        elif v == 4:
            total = random.randint(9, 27)
            q, r = total // 3, total % 3
            if r == 0:
                ans = q * q * q
            elif r == 1:
                ans = (q - 1) * q * (q + 1)
            else:
                ans = q * q * (q + 2)
            return f"三个正整数之和为{total}，它们的乘积最大是多少？", ans
        else:
            area = random.randint(6, 60)
            best_peri = None
            for w in range(1, area + 1):
                if area % w == 0:
                    l = area // w
                    peri = 2 * (l + w)
                    if best_peri is None or peri < best_peri:
                        best_peri = peri
            return f"面积为{area}平方厘米的长方形（边长为整数厘米），周长最短是多少厘米？", best_peri

    def gen_draw(self):
        v = random.randint(1, 6)
        if v == 1:
            n = random.randint(4, 20)
            k = random.randint(2, 5)
            ans = math.ceil(n / k)
            return f"{n}个苹果放入{k}个抽屉，至少有一个抽屉至少有几个苹果？", ans
        elif v == 2:
            colors = random.randint(2, 4)
            ans = colors + 1
            return f"一个袋子里有黑、白{'、蓝' if colors >= 3 else ''}{'、红' if colors >= 4 else ''}共{colors}种颜色的袜子，至少摸出几只才能保证有2只同色的？", ans
        elif v == 3:
            n = random.randint(13, 40)
            ans = math.ceil(n / 12)
            return f"一个班有{n}个同学，至少有几个同学在同一个月出生？（一年12个月）", ans
        elif v == 4:
            colors = random.randint(2, 4)
            k = 3
            ans = colors * (k - 1) + 1
            return f"有{colors}种颜色的球，至少摸出几个才能保证有{k}个同色的？", ans
        elif v == 5:
            n = random.randint(8, 30)
            ans = math.ceil(n / 7)
            return f"一个班有{n}个同学，至少有几个同学在同一个星期几出生？", ans
        else:
            people = random.randint(20, 50)
            ans = 2
            return f"一个班有{people}个同学，至少有几个同学的生日在同一天？（一年按365天算）", ans

    def gen_container(self):
        v = random.randint(1, 5)
        if v == 1:
            a = random.randint(10, 30)
            b = random.randint(10, 30)
            both = random.randint(3, min(a, b))
            return f"一个班{a}人会画画，{b}人会唱歌，两项都会的有{both}人，至少会一项的有多少人？", a + b - both
        elif v == 2:
            a = random.randint(15, 40)
            b = random.randint(15, 40)
            c = random.randint(10, 30)
            ab = random.randint(2, min(a, b))
            ac = random.randint(2, min(a, c))
            bc = random.randint(2, min(b, c))
            abc = random.randint(1, min(ab, ac, bc))
            total = a + b + c - ab - ac - bc + abc
            return f"一个班{a}人喜欢数学，{b}人喜欢语文，{c}人喜欢英语。数学和语文都喜欢的{ab}人，数学和英语都喜欢的{ac}人，语文和英语都喜欢的{bc}人，三科都喜欢的{abc}人。至少喜欢一科的有多少人？", total
        elif v == 3:
            total = random.randint(30, 50)
            a = random.randint(15, total - 5)
            b = random.randint(15, total - 5)
            both = a + b - total
            if both < 1:
                both = 1
                a = total - b + both
            return f"全班共{total}人，{a}人参加了足球队，{b}人参加了篮球队，两队都参加的至少有多少人？", both
        elif v == 4:
            total = random.randint(40, 80)
            a = random.randint(20, total - 10)
            b = random.randint(20, total - 10)
            c = random.randint(15, total - 10)
            min_overlap = max(0, a + b + c - 2 * total)
            return f"全班共{total}人，{a}人喜欢足球，{b}人喜欢篮球，{c}人喜欢排球，三项都不喜欢的有多少人最少？", min_overlap
        else:
            a = random.randint(10, 30)
            b = random.randint(10, 30)
            total = random.randint(max(a, b) + 5, a + b - 2)
            both = a + b - total
            return f"一个班有{total}人，{a}人参加了美术组，{b}人参加了音乐组，两组都参加的至少有多少人？", both


# ══════════════════════════════════════════════════════════
#  题型 → 生成方法映射
# ══════════════════════════════════════════════════════════
_GENERATOR_MAP = {
    "cb_10in": "gen_10in", "cb_20in": "gen_20in", "cb_100in": "gen_100in",
    "cb_10000in": "gen_10000in", "cb_dec_addsub": "gen_decimal_addsub", "cb_frac_addsub": "gen_fraction_addsub",
    "cb_mul_table": "gen_mul_table", "cb_mul_2x1": "gen_mul_2x1", "cb_mul_3x1": "gen_mul_3x1",
    "cb_mul_2x2": "gen_mul_2x2", "cb_mul_3x2": "gen_mul_3x2",
    "cb_mul_dec": "gen_mul_decimal", "cb_mul_frac": "gen_mul_fraction", "cb_mul_simple": "gen_mul_simple",
    "cb_div_table": "gen_div_table", "cb_div_remain": "gen_div_remainder", "cb_div_int": "gen_div_exact",
    "cb_div_1digit": "gen_div_1digit", "cb_div_2digit": "gen_div_2digit",
    "cb_div_dec": "gen_div_decimal", "cb_div_frac": "gen_div_fraction",
    "cb_mix_addsub": "gen_mix_addsub", "cb_mix_addmul": "gen_mix_addmul",
    "cb_mix_addmulsub": "gen_mix_addmulsub", "cb_mix_dec": "gen_mix_decimal",
    "cb_mix_frac": "gen_mix_fraction",
    "cb_find_rule": "gen_find_rule", "cb_arithmetic": "gen_arithmetic",
    "cb_simple_calc": "gen_simple_calc", "cb_frac_skill": "gen_frac_skill", "cb_new_op": "gen_new_op",
    "cb_sum_diff": "gen_sum_diff", "cb_age": "gen_age", "cb_tree": "gen_tree",
    "cb_chicken_rabbit": "gen_chicken_rabbit", "cb_duck": "gen_duck",
    "cb_project": "gen_project", "cb_form": "gen_form", "cb_concentration": "gen_concentration",
    "cb_perimeter": "gen_perimeter", "cb_3d_graph": "gen_3d_graph", "cb_equal_area": "gen_equal_area",
    "cb_graph_count": "gen_graph_count", "cb_graph_split": "gen_graph_split",
    "cb_odd_even": "gen_odd_even", "cb_whole_div": "gen_whole_div", "cb_remainder": "gen_remainder",
    "cb_prime": "gen_prime", "cb_gcd_lcm": "gen_gcd_lcm",
    "cb_logic": "gen_logic", "cb_arrange": "gen_arrange", "cb_best": "gen_best",
    "cb_draw": "gen_draw", "cb_container": "gen_container",
}

_BRACKET_TYPES = {"cb_mix_addsub", "cb_mix_addmul", "cb_mix_addmulsub", "cb_mix_dec", "cb_mix_frac"}

_gen = MathProblemGenerator()


def generate_questions(selections, use_bracket=False, grade=None, use_spider=True, spider_ratio=0.5):
    """
    生成题目
    
    Args:
        selections: 题型选择
        use_bracket: 是否使用括号
        grade: 年级 (1-6)，用于从爬虫题库获取真题
        use_spider: 是否使用爬虫题库
        spider_ratio: 爬虫题占比 (0-1)
    """
    basic, advance = [], []
    
    # 尝试从爬虫题库获取提升题
    spider_questions = []
    if use_spider and grade and grade in range(1, 7):
        try:
            from spider.integration import get_spider_questions
            advance_types = [t for t in selections.keys() if t in ADVANCE_TYPES]
            spider_count = int(sum(selections.get(t, 0) for t in advance_types) * spider_ratio)
            if spider_count > 0:
                spider_questions = get_spider_questions(
                    grade=grade,
                    q_types=advance_types if advance_types else None,
                    count=spider_count
                )
                print(f"[Spider] 从题库获取 {len(spider_questions)} 道真题")
        except Exception as e:
            print(f"[Spider] 获取真题失败: {e}")
    
    # 添加爬虫题目到提升题列表
    advance.extend(spider_questions)
    
    for q_type, count in selections.items():
        method_name = _GENERATOR_MAP.get(q_type)
        if not method_name:
            continue
        method = getattr(_gen, method_name, None)
        if not method:
            continue

        generated = 0
        attempts = 0
        max_attempts = min(count * 50, 5000)  # 去重需要更多尝试

        # 如果是提升题且已使用爬虫题，减少生成数量
        target_count = count
        if q_type in ADVANCE_TYPES and spider_questions:
            spider_count_for_type = sum(1 for q in spider_questions if q[0] == q_type)
            target_count = max(0, count - spider_count_for_type)

        while generated < target_count and attempts < max_attempts:
            attempts += 1
            try:
                if q_type in _BRACKET_TYPES:
                    result = method(use_bracket)
                else:
                    result = method()
                if result and isinstance(result, tuple) and len(result) == 2:
                    question, answer = result
                    # 全局去重：跳过已出过的题目
                    if _DedupCache.is_duplicate(question):
                        continue
                    _DedupCache.add(question)
                    if q_type in ADVANCE_TYPES:
                        advance.append((q_type, question, answer))
                    else:
                        basic.append((q_type, question, answer))
                    generated += 1
            except Exception:
                continue

    # 混合四则运算固定排在最后，其他基础题随机打乱
    _MIX = {"cb_mix_addsub", "cb_mix_addmul", "cb_mix_addmulsub", "cb_mix_dec", "cb_mix_frac"}
    basic_normal = [q for q in basic if q[0] not in _MIX]
    basic_mixed = [q for q in basic if q[0] in _MIX]
    random.shuffle(basic_normal)
    basic = basic_normal + basic_mixed
    random.shuffle(advance)
    return {"basic": basic, "advance": advance}


# ══════════════════════════════════════════════════════════
#  一键出题：年级配置
# ══════════════════════════════════════════════════════════
GRADE_CONFIG = {
    "一年级": [
        ("cb_10in", 15), ("cb_20in", 15)
    ],
    "二年级": [
        ("cb_20in", 8), ("cb_mul_table", 8), ("cb_div_table", 8), ("cb_mix_addmul", 6)
    ],
    "三年级": [
        # 基础60%
        ("cb_100in", 5), ("cb_mul_2x1", 5), ("cb_div_1digit", 4), ("cb_mix_addmulsub", 4),
        # 提升40%
        ("cb_find_rule", 4), ("cb_tree", 3), ("cb_arithmetic", 3), ("cb_odd_even", 2),
    ],
    "四年级": [
        # 基础60%
        ("cb_10000in", 4), ("cb_mul_2x2", 4), ("cb_div_2digit", 4),
        ("cb_mix_addmulsub", 3), ("cb_simple_calc", 3),
        # 提升40%
        ("cb_sum_diff", 4), ("cb_perimeter", 3), ("cb_chicken_rabbit", 3), ("cb_age", 2),
    ],
    "五年级": [
        # 基础60%
        ("cb_dec_addsub", 4), ("cb_mul_dec", 4), ("cb_div_dec", 3),
        ("cb_frac_addsub", 3), ("cb_mix_dec", 4),
        # 提升40%
        ("cb_project", 3), ("cb_form", 3), ("cb_concentration", 3), ("cb_3d_graph", 3),
    ],
    "六年级": [
        # 基础60%
        ("cb_frac_addsub", 4), ("cb_mix_frac", 3), ("cb_simple_calc", 4),
        ("cb_mul_frac", 4), ("cb_div_frac", 3),
        # 提升40%
        ("cb_frac_skill", 3), ("cb_new_op", 3), ("cb_gcd_lcm", 3), ("cb_best", 3),
    ],
}
def generate_quick_questions(grade, count):
    config = GRADE_CONFIG.get(grade, GRADE_CONFIG["三年级"])
    total_ratio = sum(c for _, c in config)
    selections = {}
    remaining = count
    for i, (cat, ratio) in enumerate(config):
        if i == len(config) - 1:
            selections[cat] = remaining
        else:
            n = max(1, round(count * ratio / total_ratio))
            selections[cat] = n
            remaining -= n
    return generate_questions(selections, use_bracket=False)


def compute_answers(questions_data):
    results = []
    for q_type, question, answer in questions_data.get("basic", []):
        results.append((q_type, question, _fmt_answer(answer)))
    for q_type, question, answer in questions_data.get("advance", []):
        results.append((q_type, question, _fmt_answer(answer)))
    return results


def _fmt_answer(ans) -> str:
    if isinstance(ans, tuple):
        return f"{ans[0]}余{ans[1]}"
    elif isinstance(ans, Fraction):
        return _frac(ans)
    elif isinstance(ans, float):
        ans = round(ans, 4)
        if ans.is_integer():
            return str(int(ans))
        s = f"{ans:g}"
        if '.' in s and len(s) < 8:
            return s
        frac = Fraction(ans).limit_denominator(1000)
        if frac.denominator == 1:
            return str(frac.numerator)
        return _frac(frac)
    else:
        return str(ans)