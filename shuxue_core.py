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
    _cache = None
    _dirty = False

    @classmethod
    def _load(cls):
        if cls._cache is not None:
            return cls._cache
        if os.path.exists(cls._path):
            try:
                with open(cls._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    cls._cache = data[-cls._MAX:]
                    return cls._cache
            except Exception:
                pass
        cls._cache = []
        return cls._cache

    @classmethod
    def _save(cls, items=None):
        if items is None:
            items = cls._cache or []
        try:
            with open(cls._path, "w", encoding="utf-8") as f:
                json.dump(items[-cls._MAX:], f, ensure_ascii=False)
            cls._dirty = False
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
            cls._dirty = True

    @classmethod
    def flush(cls):
        """将缓存写入文件"""
        if cls._dirty:
            cls._save()

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

def _safe_eval(expr: str):
    """安全计算数学表达式，替代 eval()"""
    import ast

    # 只允许数字、运算符、括号、小数点、空格
    allowed_chars = set('0123456789+-*/(). ')
    if not all(c in allowed_chars for c in expr):
        raise ValueError(f"表达式包含非法字符: {expr}")

    # 使用 ast.literal_eval 无法处理表达式，使用 compile + exec
    # 但限制只能使用数学运算
    try:
        # 编译表达式
        code = compile(expr, '<string>', 'eval')
        # 检查是否只包含数字和运算符
        for node in ast.walk(code):
            if isinstance(node, ast.Expression):
                continue
            elif isinstance(node, ast.BinOp):
                if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                    raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
            elif isinstance(node, ast.UnaryOp):
                if not isinstance(node.op, (ast.UAdd, ast.USub)):
                    raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
            elif isinstance(node, ast.Constant):
                if not isinstance(node.value, (int, float)):
                    raise ValueError(f"不支持的常量类型: {type(node.value).__name__}")
            elif isinstance(node, ast.Num):  # Python 3.7 兼容
                pass
            else:
                raise ValueError(f"不支持的语法: {type(node).__name__}")

        # 安全执行
        result = eval(code, {"__builtins__": {}}, {})
        return result
    except Exception as e:
        raise ValueError(f"表达式计算失败: {expr}, 错误: {e}")

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
    "cb_frac_skill": "分数运用", "cb_new_op": "比例应用",
    "cb_sum_diff": "和差倍", "cb_age": "年龄问题", "cb_tree": "植树问题",
    "cb_chicken_rabbit": "鸡兔同笼", "cb_duck": "盈亏问题",
    "cb_project": "工程问题", "cb_form": "行程问题", "cb_concentration": "浓度问题",
    "cb_graph_count": "图形计数", "cb_graph_split": "图形分割",
    "cb_perimeter": "周长面积", "cb_3d_graph": "立体图形", "cb_equal_area": "等积变形",
    "cb_odd_even": "奇偶分析", "cb_whole_div": "整除问题", "cb_remainder": "余数问题",
    "cb_prime": "质/合问题", "cb_gcd_lcm": "公约数/倍数",
    "cb_logic": "推理问题", "cb_arrange": "统筹问题", "cb_best": "最优化",
    "cb_draw": "抽屉问题", "cb_container": "容斥问题",
    "cb_assign": "分配问题", "cb_measure": "测量计算",
}

ADVANCE_TYPES = {
    "cb_find_rule", "cb_arithmetic", "cb_frac_skill", "cb_new_op",
    "cb_sum_diff", "cb_age", "cb_tree", "cb_chicken_rabbit", "cb_duck",
    "cb_project", "cb_form", "cb_concentration",
    "cb_graph_count", "cb_graph_split", "cb_perimeter", "cb_3d_graph", "cb_equal_area",
    "cb_odd_even", "cb_whole_div", "cb_remainder", "cb_prime", "cb_gcd_lcm",
    "cb_logic", "cb_arrange", "cb_best", "cb_draw", "cb_container",
    "cb_assign", "cb_measure",
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

                # 使用安全的数学表达式计算（标准运算优先级）
                eval_str = expr.rstrip(' =').replace('×', '*').replace('÷', '/')
                ans = _safe_eval(eval_str)

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
            except Exception:
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
            except Exception:
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

    def gen_sum_diff(self):
        if random.random() < 0.35:
            return self._gen_sum_diff_diff_multiple()
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

    def _gen_sum_diff_diff_multiple(self):
        """差倍问题变种：确保差值能被(倍数-1)整除"""
        v = random.randint(1, 5)
        if v == 1:
            ratio = random.randint(2, 6)
            small = random.randint(5, 80)
            big = small * ratio
            diff = big - small
            return f"两个数的差是{diff}，大数是小数的{ratio}倍，求这两个数。", f"{big}和{small}"
        elif v == 2:
            ratio = random.randint(2, 5)
            small = random.randint(10, 100)
            big = small * ratio
            diff = big - small
            return f"高年级比低年级多植{diff}棵树，且高年级植树数是低年级的{ratio}倍，求高低年级各植多少棵？", f"高年级{big}棵，低年级{small}棵"
        elif v == 3:
            ratio = random.randint(2, 4)
            small = random.randint(5, 50)
            big = small * ratio
            diff = big - small
            return f"哥哥比弟弟多{diff}元，哥哥的钱是弟弟的{ratio}倍，兄弟各有多少钱？", f"哥哥{big}元，弟弟{small}元"
        elif v == 4:
            ratio = random.randint(2, 5)
            small = random.randint(10, 60)
            big = small * ratio
            diff = big - small
            return f"甲仓比乙仓多存{diff}吨粮食，甲仓存粮是乙仓的{ratio}倍，两仓各存粮多少吨？", f"甲仓{big}吨，乙仓{small}吨"
        else:
            ratio = random.randint(2, 4)
            small = random.randint(3, 30)
            big = small * ratio
            diff = big - small
            return f"长方形的长比宽多{diff}厘米，长是宽的{ratio}倍，长和宽各是多少厘米？", f"长{big}厘米，宽{small}厘米"

    def gen_age(self):
        if random.random() < 0.4:
            return self._gen_age_future_multiple()
        v = random.randint(1, 4)
        if v == 1:
            for _ in range(50):
                child = random.randint(8, 14)
                years = random.randint(2, child - 2)
                father_now = child + random.randint(22, 35)
                child_then = child - years
                father_then = father_now - years
                if child_then > 0 and father_then > 0 and father_then % child_then == 0:
                    ratio = father_then // child_then
                    return f"小明今年{child}岁，爸爸今年{father_now}岁，{years}年前爸爸的年龄是小明的几倍？", ratio
            return "小明今年10岁，爸爸今年34岁，8年前爸爸的年龄是小明的几倍？", 13
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

    def _gen_age_future_multiple(self):
        """几年后倍数问题"""
        v = random.randint(1, 5)
        if v == 1:
            for _ in range(100):
                child = random.randint(5, 12)
                father = child + random.randint(22, 30)
                target = random.randint(2, 4)
                num = father - target * child
                den = target - 1
                if den > 0 and num > 0 and num % den == 0:
                    years = num // den
                    if 0 < years <= 20:
                        return f"小明今年{child}岁，爸爸今年{father}岁，几年后爸爸的年龄是小明的{target}倍？", years
            return "小明今年8岁，爸爸今年36岁，几年后爸爸的年龄是小明的3倍？", 5
        elif v == 2:
            for _ in range(100):
                a = random.randint(6, 14)
                b = a + random.randint(2, 8)
                target = random.randint(2, 3)
                num = b - target * a
                den = target - 1
                if den > 0 and num > 0 and num % den == 0:
                    years = num // den
                    if 0 < years <= 15:
                        return f"姐姐今年{b}岁，妹妹今年{a}岁，几年后姐姐的年龄是妹妹的{target}倍？", years
            return "姐姐今年15岁，妹妹今年10岁，几年后姐姐的年龄是妹妹的2倍？", 5
        elif v == 3:
            for _ in range(100):
                child = random.randint(6, 12)
                father = child + random.randint(24, 32)
                target = random.randint(2, 4)
                num = target * child - father
                den = target - 1
                if den > 0 and num > 0 and num % den == 0:
                    years = num // den
                    if 0 < years < child:
                        return f"小明今年{child}岁，爸爸今年{father}岁，几年前爸爸的年龄是小明的{target}倍？", years
            return "小明今年10岁，爸爸今年34岁，几年前爸爸的年龄是小明的3倍？", 2
        elif v == 4:
            a = random.randint(3, 8)
            b = a + random.randint(20, 30)
            for t in random.sample(range(3, 7), 4):
                y = (b - t * a) // (t - 1)
                if y > 0 and y <= 20 and (b - t * a) % (t - 1) == 0:
                    return f"儿子今年{a}岁，妈妈今年{b}岁，{y}年后妈妈的年龄是儿子的几倍？", t
            return f"儿子今年5岁，妈妈今年25岁，5年后妈妈的年龄是儿子的几倍？", 3
        else:
            a = random.randint(8, 15)
            b = a + random.randint(1, 5)
            years = random.randint(3, 10)
            target = (a + years) + (b + years)
            return f"哥哥今年{a}岁，弟弟今年{b}岁，几年后两人年龄之和是{target}岁？", years

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
        r = random.random()
        if r < 0.3:
            return self._gen_profit_variant()
        elif r < 0.55:
            return self._gen_shopping_variant()
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

    # ==================== 分数运用（水桶加水类） ====================
    def _find_frac_pair(self, a, b):
        """为分数运用题找到合适的 n, m 对（n > m，结果为正且在合理范围内）"""
        pairs = []
        for n in range(2, 8):
            for m in range(1, n):
                num = b * m - a * n
                den = n - m
                if den > 0 and num > 0 and num % den == 0:
                    ans = num // den
                    if 1 <= ans <= 50:
                        pairs.append((n, m))
        if pairs:
            return random.choice(pairs)
        return None

    def gen_frac_apply(self):
        v = random.randint(1, 6)
        if v == 1:
            for _ in range(100):
                a = random.randint(4, 20)
                b = a + random.randint(4, 20)
                pair = self._find_frac_pair(a, b)
                if pair:
                    n, m = pair
                    ans = (b * m - a * n) // (n - m)
                    return f"小桶装了{a}升水，大桶装了{b}升水，往两桶各增加同样多的水后，小桶的水是大桶的{n}分之{m}，各加了多少升水？", ans
        elif v == 2:
            for _ in range(100):
                a = random.randint(5, 20)
                b = a + random.randint(5, 25)
                pair = self._find_frac_pair(a, b)
                if pair:
                    n, m = pair
                    ans = (b * m - a * n) // (n - m)
                    return f"甲瓶有果汁{a}毫升，乙瓶有果汁{b}毫升，两瓶各倒入同样多的果汁后，乙瓶是甲瓶的{n}分之{m}，各倒入了多少毫升？", ans
        elif v == 3:
            for _ in range(100):
                a = random.randint(10, 30)
                b = a + random.randint(10, 40)
                pair = self._find_frac_pair(a, b)
                if pair:
                    n, m = pair
                    ans = (b * m - a * n) // (n - m)
                    return f"甲箱有苹果{a}个，乙箱有苹果{b}个，两箱各放入同样多的苹果后，乙箱是甲箱的{n}分之{m}，各放了多少个？", ans
        elif v == 4:
            for _ in range(100):
                a = random.randint(8, 25)
                b = a + random.randint(5, 20)
                pair = self._find_frac_pair(a, b)
                if pair:
                    n, m = pair
                    ans = (b * m - a * n) // (n - m)
                    return f"书架上层有书{a}本，下层有书{b}本，从下层拿同样多的书到上层后，上层是下层的{n}分之{m}，拿了多少本？", ans
        elif v == 5:
            for _ in range(100):
                a = random.randint(50, 150)
                b = a + random.randint(20, 80)
                pair = self._find_frac_pair(a, b)
                if pair:
                    n, m = pair
                    ans = (b * m - a * n) // (n - m)
                    return f"甲停车场有车{a}辆，乙停车场有车{b}辆，两停车场各增加同样多的车后，乙是甲的{n}分之{m}，各增加了多少辆？", ans
        else:
            for _ in range(100):
                a = random.randint(20, 50)
                b = a + random.randint(10, 30)
                pair = self._find_frac_pair(a, b)
                if pair:
                    n, m = pair
                    ans = (b * m - a * n) // (n - m)
                    return f"一班有学生{a}人，二班有学生{b}人，两班各转来同样多的学生后，二班人数是一班的{n}分之{m}，各转来多少人？", ans
        # 保底
        return "小桶装了8升水，大桶装了14升水，往两桶各增加同样多的水后，小桶的水是大桶的7分之5，各加了多少升水？", 6

    # ==================== 比例应用（图书馆比例类） ====================
    def _find_ratio_add(self, init_m, init_f):
        """找到合适的 fa:fb 和 ans，使得加入 ans 名女生后男女比变为 fa:fb"""
        from math import gcd as _gcd
        clean_ratios = [(1,2),(1,3),(1,4),(1,5),(2,3),(2,5),(3,4),(3,5),(3,7),(4,5),(4,7)]
        random.shuffle(clean_ratios)
        for fa, fb in clean_ratios:
            # init_m / (init_f + ans) = fa / fb
            # ans = (init_m * fb - init_f * fa) / fa
            num = init_m * fb - init_f * fa
            if num > 0 and num % fa == 0:
                ans = num // fa
                if 2 <= ans <= 30:
                    return fa, fb, ans
        return None

    def gen_ratio_apply(self):
        from math import gcd as _gcd
        v = random.randint(1, 6)
        if v == 1:
            for _ in range(100):
                total = random.randint(27, 54)
                a, b = 4, 5
                while total % (a + b) != 0:
                    total += 1
                init_m = total * a // (a + b)
                init_f = total - init_m
                result = self._find_ratio_add(init_m, init_f)
                if result:
                    fa, fb, ans = result
                    return f"图书馆有{total}人看书，男女之比是{a}:{b}，后来又来了一些女生，男女之比变为{fa}:{fb}，来了多少女生？", ans
        elif v == 2:
            for _ in range(100):
                total = random.randint(20, 50)
                a, b = 3, 5
                while total % (a + b) != 0:
                    total += 1
                init_m = total * a // (a + b)
                init_f = total - init_m
                result = self._find_ratio_add(init_m, init_f)
                if result:
                    fa, fb, ans = result
                    return f"阅览室有{total}人，男女之比是{a}:{b}，又来了一些女生后男女之比变为{fa}:{fb}，来了多少女生？", ans
        elif v == 3:
            for _ in range(100):
                total = random.randint(24, 60)
                a, b = 2, 4
                while total % (a + b) != 0:
                    total += 1
                init_m = total * a // (a + b)
                init_f = total - init_m
                result = self._find_ratio_add(init_m, init_f)
                if result:
                    fa, fb, ans = result
                    return f"兴趣小组有{total}人，男女之比是{a}:{b}，又加入一些女生后男女之比变为{fa}:{fb}，加入多少女生？", ans
        elif v == 4:
            for _ in range(100):
                init_m = random.randint(10, 25)
                init_f = random.randint(10, 25)
                result = self._find_ratio_add(init_m, init_f)
                if result:
                    fa, fb, ans = result
                    return f"阅览室有男{init_m}人女{init_f}人，又来了一些女生后男女之比变为{fa}:{fb}，来了多少女生？", ans
        elif v == 5:
            for _ in range(100):
                init_m = random.randint(12, 30)
                init_f = random.randint(12, 30)
                leave_m = random.randint(1, max(1, init_m // 3))
                final_m = init_m - leave_m
                final_f = init_f
                if final_m > 0 and final_f > 0:
                    g = _gcd(final_m, final_f)
                    fa, fb = final_m // g, final_f // g
                    return f"教室里有男{init_m}人女{init_f}人，走了几名男生后男女之比变为{fa}:{fb}，走了多少男生？", leave_m
        else:
            for _ in range(100):
                init_m = random.randint(10, 25)
                init_f = random.randint(10, 25)
                result = self._find_ratio_add(init_m, init_f)
                if result:
                    fa, fb, ans = result
                    return f"班里有男生{init_m}人，女生{init_f}人，又来了一些女生后男女之比变为{fa}:{fb}，来了多少女生？", ans
        # 保底
        return "图书馆有36人看书，男女之比是5:4，后来又来了一些女生，男女之比变为1:3，来了多少女生？", 9

    # ==================== 分配问题 ====================
    def gen_assign(self):
        v = random.randint(1, 5)
        if v == 1:
            total = random.randint(30, 99)
            give = random.randint(5, total - 6)
            n = random.randint(2, 6)
            remain = total - give
            while remain % n != 0:
                give = random.randint(5, total - 6)
                remain = total - give
            ans = remain // n
            names = [("小明", "小红"), ("小华", "小丽"), ("哥哥", "弟弟"), ("姐姐", "妹妹")]
            a, b = random.choice(names)
            items = ["故事书", "漫画书", "笔记本", "彩笔", "贴纸"]
            item = random.choice(items)
            return f"{a}有{total}本{item}，借给{b}{give}本后，剩下的平均分给{n}个小朋友，每个小朋友得到多少本？", ans
        elif v == 2:
            total = random.randint(50, 200)
            give = random.randint(10, total - 10)
            n = random.randint(2, 5)
            remain = total - give
            while remain % n != 0:
                give = random.randint(10, total - 10)
                remain = total - give
            ans = remain // n
            items = [("苹果", "个"), ("糖果", "颗"), ("饼干", "块"), ("橘子", "个")]
            item, unit = random.choice(items)
            return f"妈妈买了{total}{unit}{item}，送给邻居{give}{unit}后，剩下的平均分给{n}个孩子，每人分到多少{unit}？", ans
        elif v == 3:
            a = random.randint(20, 80)
            b = random.randint(20, 80)
            n = random.randint(2, 5)
            total = a + b
            while total % n != 0:
                b = random.randint(20, 80)
                total = a + b
            ans = total // n
            return f"两个书架共有{total}本书，第一个书架有{a}本，第二个书架有{b}本。平均分给{n}个班级，每班分到多少本？", ans
        elif v == 4:
            per = random.randint(5, 15)
            n = random.randint(3, 8)
            total = per * n + random.randint(1, n - 1)
            q, r = divmod(total, n)
            return f"把{total}个苹果平均分给{n}个小朋友，每人分几个？还剩几个？", f"{q}个剩{r}个"
        else:
            total = random.randint(100, 500)
            n = random.randint(4, 8)
            while total % n != 0:
                total += 1
            ans = total // n
            return f"学校买了{total}本作业本，平均分给{n}个班，每班分到多少本？", ans

    # ==================== 测量计算 ====================
    def gen_measure(self):
        v = random.randint(1, 5)
        if v == 1:
            total = round(random.uniform(3, 15), 2)
            mud = round(random.uniform(0.1, 2), 2)
            air = round(random.uniform(0.5, 3), 2)
            water = round(total - mud - air, 2)
            while water <= 0:
                mud = round(random.uniform(0.1, 1), 2)
                air = round(random.uniform(0.3, 2), 2)
                water = round(total - mud - air, 2)
            return f"把{total}米长的竹竿插入水池中，竹竿入泥部分是{mud}米，露出水面部分是{air}米，水池中水深多少米？", water
        elif v == 2:
            total = round(random.uniform(1, 5), 2)
            a = round(random.uniform(0.1, total / 2), 2)
            b = round(total - a - round(random.uniform(0.1, total / 3), 2), 2)
            c = round(total - a - b, 2)
            while c <= 0:
                a = round(random.uniform(0.1, total / 3), 2)
                b = round(random.uniform(0.1, total / 3), 2)
                c = round(total - a - b, 2)
            return f"一根绳子长{total}米，第一次用去{a}米，第二次用去{b}米，还剩多少米？", c
        elif v == 3:
            a = round(random.uniform(10, 50), 2)
            b = round(random.uniform(10, 50), 2)
            return f"一桶油重{a}千克，用去{b}千克后，桶和油共重多少千克？（桶重2.5千克）", round(a - b + 2.5, 2)
        elif v == 4:
            length = round(random.uniform(50, 200), 1)
            width = round(random.uniform(20, 80), 1)
            return f"一块长方形菜地长{length}米，宽{width}米，周长是多少米？", round(2 * (length + width), 1)
        else:
            a = round(random.uniform(1, 10), 2)
            b = round(random.uniform(1, 10), 2)
            c = round(random.uniform(0.5, 5), 2)
            ans = round(a + b + c, 2)
            return f"三根铁丝分别长{a}米、{b}米、{c}米，接在一起共长多少米？", ans

    # ==================== 盈亏计算（内部变种） ====================
    def _gen_profit_variant(self):
        v = random.randint(1, 5)
        if v == 1:
            total = random.randint(30, 100)
            cost = random.randint(50, 150)
            sell = cost + random.randint(10, 50)
            sold1 = random.randint(total // 3, total * 2 // 3)
            sell2 = cost - random.randint(5, 30)
            sold2 = total - sold1
            income = sold1 * sell + sold2 * sell2
            expense = total * cost
            profit = income - expense
            result = "盈利" if profit > 0 else "亏损" if profit < 0 else "不亏不赚"
            return f"某商店购进{total}件衣服，每件进价{cost}元。实际销售时每件售价{sell}元，卖出{sold1}件后降到{sell2}元销售，结果全部售出。该商店是盈利了还是亏损了？盈亏多少元？", f"{result}{abs(profit)}元"
        elif v == 2:
            cost = random.randint(5, 30)
            sell = cost + random.randint(2, 10)
            n = random.randint(10, 50)
            profit = (sell - cost) * n
            return f"某商店每支笔进价{cost}元，售价{sell}元，卖出{n}支后盈利多少元？", f"{profit}元"
        elif v == 3:
            cost = random.randint(20, 100)
            sell = cost - random.randint(2, 15)
            n = random.randint(10, 30)
            loss = (cost - sell) * n
            return f"某商店每件商品进价{cost}元，清仓价{sell}元，卖出{n}件后亏损多少元？", f"{loss}元"
        elif v == 4:
            cost1 = random.randint(30, 80)
            sell1 = cost1 + random.randint(5, 20)
            n1 = random.randint(10, 30)
            cost2 = random.randint(30, 80)
            sell2 = cost2 - random.randint(5, 15)
            n2 = random.randint(10, 30)
            profit1 = (sell1 - cost1) * n1
            profit2 = (sell2 - cost2) * n2
            total_profit = profit1 + profit2
            result = "盈利" if total_profit > 0 else "亏损" if total_profit < 0 else "不亏不赚"
            return f"商店卖出A商品{n1}件，每件进价{cost1}元售价{sell1}元；卖出B商品{n2}件，每件进价{cost2}元售价{sell2}元。总的是盈利还是亏损？", f"{result}{abs(total_profit)}元"
        else:
            cost = random.randint(50, 200)
            profit_total = random.randint(100, 500)
            sell = random.randint(cost + 5, cost + 30)
            n = profit_total // (sell - cost)
            while n <= 0 or (sell - cost) * n != profit_total:
                sell = cost + random.randint(5, 20)
                n = profit_total // (sell - cost) if sell > cost else 0
            return f"某商品进价{cost}元，售价{sell}元，要盈利{profit_total}元需卖出多少件？", n

    # ==================== 购物计算（内部变种） ====================
    def _gen_shopping_variant(self):
        v = random.randint(1, 5)
        if v == 1:
            n = random.randint(50, 200)
            p1 = random.randint(5, 15)
            p2 = random.randint(5, 15)
            while p2 == p1:
                p2 = random.randint(5, 15)
            total = n * p1 + n * p2
            names = [("《儿童文学》", "《当代小学生》"), ("《数学报》", "《语文报》"),
                     ("铅笔", "橡皮"), ("笔记本", "文具盒"), ("苹果", "香蕉")]
            a, b = random.choice(names)
            return f"学校要购进{a}和{b}各{n}本，{a}每本{p1}元，{b}每本{p2}元。一共需要花多少元？", total
        elif v == 2:
            n1 = random.randint(10, 50)
            p1 = random.randint(5, 30)
            n2 = random.randint(10, 50)
            p2 = random.randint(5, 30)
            total = n1 * p1 + n2 * p2
            return f"商店卖出苹果{n1}千克，每千克{p1}元；卖出香蕉{n2}千克，每千克{p2}元。共收入多少元？", total
        elif v == 3:
            n = random.randint(5, 20)
            p = random.randint(10, 100)
            pay = random.randint(p * n, p * n + 200)
            total = n * p
            change = pay - total
            return f"买{n}个单价{p}元的商品，付{pay}元应找回多少元？", change
        elif v == 4:
            n = random.randint(2, 8)
            p = random.randint(10, 50)
            total = n * p
            discount = random.choice([8, 9])
            actual = total * discount // 10
            return f"买{n}个单价{p}元的商品，打{discount}折后需付多少元？", actual
        else:
            p1 = random.randint(5, 20)
            p2 = random.randint(5, 20)
            n1 = random.randint(5, 20)
            n2 = random.randint(5, 20)
            total1 = n1 * p1
            total2 = n2 * p2
            diff = abs(total1 - total2)
            return f"甲买了{n1}本单价{p1}元的书，乙买了{n2}本单价{p2}元的书，甲比乙多花多少元？", diff


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
    "cb_simple_calc": "gen_simple_calc", "cb_frac_skill": "gen_frac_apply", "cb_new_op": "gen_ratio_apply",
    "cb_sum_diff": "gen_sum_diff", "cb_age": "gen_age", "cb_tree": "gen_tree",
    "cb_chicken_rabbit": "gen_chicken_rabbit", "cb_duck": "gen_duck",
    "cb_project": "gen_project", "cb_form": "gen_form", "cb_concentration": "gen_concentration",
    "cb_perimeter": "gen_perimeter", "cb_3d_graph": "gen_3d_graph", "cb_equal_area": "gen_equal_area",
    "cb_graph_count": "gen_graph_count", "cb_graph_split": "gen_graph_split",
    "cb_odd_even": "gen_odd_even", "cb_whole_div": "gen_whole_div", "cb_remainder": "gen_remainder",
    "cb_prime": "gen_prime", "cb_gcd_lcm": "gen_gcd_lcm",
    "cb_logic": "gen_logic", "cb_arrange": "gen_arrange", "cb_best": "gen_best",
    "cb_draw": "gen_draw", "cb_container": "gen_container",
    "cb_assign": "gen_assign", "cb_measure": "gen_measure",
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
            from zhenti_core import get_spider_questions
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
    # 保存去重缓存
    _DedupCache.flush()
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
        ("cb_100in", 4), ("cb_mul_2x1", 4), ("cb_div_1digit", 3), ("cb_mix_addmulsub", 4),
        # 提升40%：和差倍(含差倍变种)
        ("cb_sum_diff", 4), ("cb_find_rule", 2), ("cb_tree", 2),
        ("cb_arithmetic", 2), ("cb_odd_even", 1), ("cb_age", 2),
    ],
    "四年级": [
        # 基础60%
        ("cb_10000in", 4), ("cb_mul_2x2", 4), ("cb_div_2digit", 3),
        ("cb_mix_addmulsub", 3), ("cb_simple_calc", 3),
        # 提升40%：年龄问题(含几年后倍数) + 盈亏(含购物) + 应用题
        ("cb_age", 3), ("cb_sum_diff", 2), ("cb_chicken_rabbit", 2),
        ("cb_duck", 3), ("cb_assign", 2), ("cb_measure", 2),
    ],
    "五年级": [
        # 基础60%
        ("cb_dec_addsub", 4), ("cb_mul_dec", 4), ("cb_div_dec", 3),
        ("cb_frac_addsub", 3), ("cb_mix_dec", 4),
        # 提升40%
        ("cb_project", 3), ("cb_form", 3), ("cb_frac_skill", 2), ("cb_3d_graph", 3),
    ],
    "六年级": [
        # 基础60%
        ("cb_frac_addsub", 4), ("cb_mix_frac", 3), ("cb_simple_calc", 4),
        ("cb_mul_frac", 4), ("cb_div_frac", 3),
        # 提升40%
        ("cb_new_op", 3), ("cb_gcd_lcm", 3), ("cb_best", 3), ("cb_container", 3),
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


# ══════════════════════════════════════════════════════════
#  几何题图形绘制模块 (原 shuxue_drawings.py)
# ══════════════════════════════════════════════════════════

from dataclasses import dataclass
from typing import Optional

@dataclass
class DrawingSpec:
    shape_type: str
    params: dict
    figure_height_mm: float

GEOMETRY_QUESTION_TYPES = {
    "cb_perimeter", "cb_3d_graph", "cb_equal_area",
    "cb_graph_count", "cb_graph_split",
}

FIGURE_HEIGHTS = {
    "rectangle": 16, "square": 16, "triangle": 16, "circle": 16,
    "cube": 18, "prism": 18,
    "eq_tri_para": 17, "eq_tri_trap": 17, "eq_para_rect": 17,
    "points_circle": 18, "line_grid": 16, "rect_grid": 16,
    "line_segment": 12, "circle_lines": 17, "cell_grid": 16,
}

def _extract_perimeter(text: str) -> Optional[DrawingSpec]:
    m = re.search(r'长方形长(\d+)厘米宽(\d+)厘米', text)
    if m:
        return DrawingSpec("rectangle", {"l": int(m.group(1)), "w": int(m.group(2))}, 25)
    m = re.search(r'正方形边长(\d+)厘米', text)
    if m:
        return DrawingSpec("square", {"s": int(m.group(1))}, 25)
    m = re.search(r'三角形底(\d+)厘米[，,]高(\d+)厘米', text)
    if m:
        return DrawingSpec("triangle", {"b": int(m.group(1)), "h": int(m.group(2))}, 25)
    m = re.search(r'圆的半径是(\d+)厘米', text)
    if m:
        return DrawingSpec("circle", {"r": int(m.group(1))}, 25)
    return None

def _extract_3d(text: str) -> Optional[DrawingSpec]:
    m = re.search(r'棱长(\d+)厘米的正方体', text)
    if m:
        return DrawingSpec("cube", {"a": int(m.group(1))}, 30)
    m = re.search(r'长方体长(\d+)厘米[、,]宽(\d+)厘米[、,]高(\d+)厘米', text)
    if m:
        return DrawingSpec("prism", {"l": int(m.group(1)), "w": int(m.group(2)), "h": int(m.group(3))}, 30)
    return None

def _extract_equal_area(text: str) -> Optional[DrawingSpec]:
    if '三角形' in text and '平行四边形' in text:
        return DrawingSpec("eq_tri_para", {"text": text}, 28)
    if '三角形' in text and '梯形' in text:
        return DrawingSpec("eq_tri_trap", {"text": text}, 28)
    if '平行四边形' in text and '长方形' in text:
        return DrawingSpec("eq_para_rect", {"text": text}, 28)
    return None

def _extract_graph_count(text: str) -> Optional[DrawingSpec]:
    m = re.search(r'(\d+)个点两两连线', text)
    if m:
        return DrawingSpec("points_circle", {"n": int(m.group(1))}, 30)
    m = re.search(r'(\d+)条横线和(\d+)条竖线', text)
    if m:
        return DrawingSpec("line_grid", {"h": int(m.group(1)), "v": int(m.group(2))}, 25)
    m = re.search(r'(\d+)行(\d+)列的方格网', text)
    if m:
        return DrawingSpec("rect_grid", {"rows": int(m.group(1)), "cols": int(m.group(2))}, 25)
    return None

def _extract_graph_split(text: str) -> Optional[DrawingSpec]:
    m = re.search(r'一条线段[，,](\d+)个点', text)
    if m:
        return DrawingSpec("line_segment", {"n": int(m.group(1))}, 18)
    m = re.search(r'圆内画(\d+)条直线', text)
    if m:
        return DrawingSpec("circle_lines", {"n": int(m.group(1))}, 28)
    m = re.search(r'(\d+)行(\d+)列的方格图', text)
    if m:
        return DrawingSpec("cell_grid", {"rows": int(m.group(1)), "cols": int(m.group(2))}, 25)
    return None

_EXTRACTORS = {
    "cb_perimeter": _extract_perimeter,
    "cb_3d_graph": _extract_3d,
    "cb_equal_area": _extract_equal_area,
    "cb_graph_count": _extract_graph_count,
    "cb_graph_split": _extract_graph_split,
}

def extract_drawing_spec(q_type: str, question_text: str) -> Optional[DrawingSpec]:
    extractor = _EXTRACTORS.get(q_type)
    if extractor:
        return extractor(question_text)
    return None

def _dim_label(c, x, y, text, font, size=8):
    c.setFont(font, size)
    c.drawCentredString(x, y, text)

def _dashed_line(c, x1, y1, x2, y2):
    c.saveState()
    c.setDash([2, 2])
    c.setLineWidth(0.3)
    c.line(x1, y1, x2, y2)
    c.restoreState()

def draw_rectangle(c, x, y, w, h, params):
    l, wd = params["l"], params["w"]
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    avail_w = w - 4
    avail_h = h - 14
    scale = min(avail_w / l, avail_h / wd)
    rw, rh = l * scale, wd * scale
    rx = x + (w - rw) / 2
    ry = y + 8
    c.setLineWidth(0.6)
    c.rect(rx, ry, rw, rh)
    _dim_label(c, rx + rw / 2, ry - 10, f"{l}cm", fn, 8)
    c.saveState()
    c.translate(rx - 4, ry + rh / 2)
    c.rotate(90)
    _dim_label(c, 0, 0, f"{wd}cm", fn, 8)
    c.restoreState()

def draw_square(c, x, y, w, h, params):
    s = params["s"]
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    avail = min(w - 4, h - 14)
    ss = min(avail, s * (avail / max(s, 1)))
    rx = x + (w - ss) / 2
    ry = y + 8
    c.setLineWidth(0.6)
    c.rect(rx, ry, ss, ss)
    _dim_label(c, rx + ss / 2, ry - 10, f"{s}cm", fn, 8)

def draw_triangle(c, x, y, w, h, params):
    b, ht = params["b"], params["h"]
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    avail_w = w - 4
    avail_h = h - 14
    scale = min(avail_w / b, avail_h / ht)
    sb, sh = b * scale, ht * scale
    cx = x + w / 2
    by = y + 8
    pts = [(cx - sb / 2, by), (cx + sb / 2, by), (cx, by + sh)]
    p = c.beginPath()
    p.moveTo(*pts[0])
    p.lineTo(*pts[1])
    p.lineTo(*pts[2])
    p.close()
    c.drawPath(p, stroke=1, fill=0)
    _dashed_line(c, cx, by + sh, cx, by)
    _dim_label(c, cx, by - 10, f"{b}cm", fn, 8)
    c.saveState()
    c.translate(cx + 3, by + sh / 2)
    c.rotate(90)
    _dim_label(c, 0, 0, f"{ht}cm", fn, 8)
    c.restoreState()

def draw_circle(c, x, y, w, h, params):
    r = params["r"]
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    avail = min(w - 4, h - 16) / 2
    sr = min(avail, r * (avail / max(r, 1)))
    cx = x + w / 2
    cy = y + 8 + sr
    c.setLineWidth(0.6)
    c.circle(cx, cy, sr)
    c.line(cx, cy, cx + sr, cy)
    _dim_label(c, cx + sr / 2, cy + 4, f"r={r}cm", fn, 8)

def draw_cube(c, x, y, w, h, params):
    a = params["a"]
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    avail_w = w - 6
    avail_h = h - 14
    max_a = min(avail_w / 1.35, avail_h)
    sa = min(max_a, a * (max_a / max(a, 1)))
    ox = sa * 0.35
    oy = sa * 0.35
    bx = x + (w - sa - ox) / 2
    by = y + 8
    c.setLineWidth(0.6)
    c.rect(bx, by, sa, sa)
    c.rect(bx + ox, by + oy, sa, sa)
    c.line(bx, by, bx + ox, by + oy)
    c.line(bx + sa, by, bx + sa + ox, by + oy)
    c.line(bx, by + sa, bx + ox, by + sa + oy)
    c.line(bx + sa, by + sa, bx + sa + ox, by + sa + oy)
    _dim_label(c, bx + sa / 2, by - 10, f"{a}cm", fn, 8)

def draw_prism(c, x, y, w, h, params):
    l, wd, ht = params["l"], params["w"], params["h"]
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    avail_w = w - 6
    avail_h = h - 14
    max_dim = min(avail_w / 1.4, avail_h)
    scale = max_dim / max(l, wd, ht, 1)
    sl, sw, sh = l * scale, wd * scale, ht * scale
    ox, oy = sw * 0.4, sw * 0.3
    bx = x + (w - sl - ox) / 2
    by = y + 8
    c.setLineWidth(0.6)
    c.rect(bx, by, sl, sh)
    c.rect(bx + ox, by + oy, sl, sh)
    c.line(bx, by, bx + ox, by + oy)
    c.line(bx + sl, by, bx + sl + ox, by + oy)
    c.line(bx, by + sh, bx + ox, by + sh + oy)
    c.line(bx + sl, by + sh, bx + sl + ox, by + sh + oy)
    _dim_label(c, bx + sl / 2, by - 10, f"{l}cm", fn, 8)

def draw_eq_tri_para(c, x, y, w, h, params):
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    c.setLineWidth(0.6)
    half_w = w / 2 - 2
    tx = x + 1
    ty = y + 6
    tw, th = half_w - 2, h - 14
    p = c.beginPath()
    p.moveTo(tx, ty)
    p.lineTo(tx + tw, ty)
    p.lineTo(tx + tw / 2, ty + th)
    p.close()
    c.drawPath(p, stroke=1, fill=0)
    _dim_label(c, tx + tw / 2, ty + th + 4, "S", fn, 9)
    px = x + half_w + 4
    pw, ph = half_w - 2, th * 0.65
    skew = tw * 0.2
    p2 = c.beginPath()
    p2.moveTo(px + skew, ty + ph)
    p2.lineTo(px + skew + pw, ty + ph)
    p2.lineTo(px + pw, ty)
    p2.lineTo(px, ty)
    p2.close()
    c.drawPath(p2, stroke=1, fill=0)
    _dim_label(c, px + pw / 2 + skew / 2, ty + ph + 4, "S", fn, 9)
    c.saveState()
    c.setDash([2, 2])
    c.line(x + w / 2 - 2, ty + th + 10, x + w / 2 - 2, ty - 2)
    c.restoreState()

def draw_eq_tri_trap(c, x, y, w, h, params):
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    c.setLineWidth(0.6)
    half_w = w / 2 - 2
    tx, ty = x + 1, y + 6
    tw, th = half_w - 2, h - 14
    p = c.beginPath()
    p.moveTo(tx, ty)
    p.lineTo(tx + tw, ty)
    p.lineTo(tx + tw / 2, ty + th)
    p.close()
    c.drawPath(p, stroke=1, fill=0)
    _dim_label(c, tx + tw / 2, ty + th + 4, "S", fn, 9)
    px = x + half_w + 4
    pw, ph = half_w - 2, th * 0.7
    p2 = c.beginPath()
    p2.moveTo(px, ty)
    p2.lineTo(px + pw, ty)
    p2.lineTo(px + pw * 0.7, ty + ph)
    p2.lineTo(px + pw * 0.3, ty + ph)
    p2.close()
    c.drawPath(p2, stroke=1, fill=0)
    _dim_label(c, px + pw / 2, ty + ph + 4, "S", fn, 9)

def draw_eq_para_rect(c, x, y, w, h, params):
    fn = c._fontname if hasattr(c, '_fontname') else 'SimSun'
    c.setLineWidth(0.6)
    half_w = w / 2 - 2
    tx, ty = x + 1, y + 6
    tw, th = half_w - 2, h - 14
    skew = tw * 0.2
    p = c.beginPath()
    p.moveTo(tx + skew, ty + th)
    p.lineTo(tx + skew + tw, ty + th)
    p.lineTo(tx + tw, ty)
    p.lineTo(tx, ty)
    p.close()
    c.drawPath(p, stroke=1, fill=0)
    _dim_label(c, tx + tw / 2 + skew / 2, ty + th + 4, "S", fn, 9)
    px = x + half_w + 4
    pw, ph = half_w - 2, th
    c.rect(px, ty, pw, ph)
    _dim_label(c, px + pw / 2, ty + ph + 4, "S", fn, 9)

def draw_points_circle(c, x, y, w, h, params):
    n = min(params["n"], 8)
    cx = x + w / 2
    cy = y + h / 2
    r = min(w - 8, h - 16) / 2
    c.setLineWidth(0.3)
    for i in range(n):
        a1 = 2 * math.pi * i / n
        for j in range(i + 1, n):
            a2 = 2 * math.pi * j / n
            c.line(cx + r * math.cos(a1), cy + r * math.sin(a1),
                   cx + r * math.cos(a2), cy + r * math.sin(a2))
    c.setLineWidth(0.6)
    for i in range(n):
        a = 2 * math.pi * i / n
        c.circle(cx + r * math.cos(a), cy + r * math.sin(a), 2, stroke=1, fill=1)

def draw_line_grid(c, x, y, w, h, params):
    hv, vv = params["h"], params["v"]
    pad = 4
    gw, gh = w - 2 * pad, h - 2 * pad - 6
    c.setLineWidth(0.5)
    for i in range(hv):
        yy = y + pad + gh * i / max(hv - 1, 1)
        c.line(x + pad, yy, x + pad + gw, yy)
    for j in range(vv):
        xx = x + pad + gw * j / max(vv - 1, 1)
        c.line(xx, y + pad, xx, y + pad + gh)

def draw_rect_grid(c, x, y, w, h, params):
    rows, cols = params["rows"], params["cols"]
    pad = 4
    gw, gh = w - 2 * pad, h - 2 * pad - 6
    cw, ch = gw / cols, gh / rows
    c.setLineWidth(0.5)
    for i in range(rows + 1):
        c.line(x + pad, y + pad + ch * i, x + pad + gw, y + pad + ch * i)
    for j in range(cols + 1):
        c.line(x + pad + cw * j, y + pad, x + pad + cw * j, y + pad + gh)

def draw_line_segment(c, x, y, w, h, params):
    n = params["n"]
    pad = 6
    sx, ex = x + pad, x + w - pad
    sy = y + h / 2
    c.setLineWidth(0.6)
    c.line(sx, sy, ex, sy)
    c.circle(sx, sy, 2.5, stroke=1, fill=1)
    c.circle(ex, sy, 2.5, stroke=1, fill=1)
    c.setLineWidth(0.5)
    for i in range(1, n + 1):
        px = sx + (ex - sx) * i / (n + 1)
        c.circle(px, sy, 2, stroke=1, fill=1)

def draw_circle_lines(c, x, y, w, h, params):
    n = min(params["n"], 6)
    cx = x + w / 2
    cy = y + h / 2
    r = min(w - 8, h - 16) / 2
    c.setLineWidth(0.5)
    c.circle(cx, cy, r)
    for i in range(n):
        angle = math.pi * i / n + 0.1
        dx = r * math.cos(angle)
        dy = r * math.sin(angle)
        c.line(cx - dx, cy - dy, cx + dx, cy + dy)

def draw_cell_grid(c, x, y, w, h, params):
    draw_rect_grid(c, x, y, w, h, params)

_DRAW_FUNCS = {
    "rectangle": draw_rectangle,
    "square": draw_square,
    "triangle": draw_triangle,
    "circle": draw_circle,
    "cube": draw_cube,
    "prism": draw_prism,
    "eq_tri_para": draw_eq_tri_para,
    "eq_tri_trap": draw_eq_tri_trap,
    "eq_para_rect": draw_eq_para_rect,
    "points_circle": draw_points_circle,
    "line_grid": draw_line_grid,
    "rect_grid": draw_rect_grid,
    "line_segment": draw_line_segment,
    "circle_lines": draw_circle_lines,
    "cell_grid": draw_cell_grid,
}

def draw_figure(c, x, y, width, height, spec: DrawingSpec):
    c.saveState()
    c._fontname = 'SimSun'
    func = _DRAW_FUNCS.get(spec.shape_type)
    if func:
        func(c, x, y, width, height, spec.params)
    c.restoreState()


# ══════════════════════════════════════════════════════════
#  数学题目PDF导出模块 (原 shuxue_export.py)
# ══════════════════════════════════════════════════════════

from datetime import datetime

def _get_export_dir():
    return os.path.dirname(os.path.abspath(__file__))

def _build_filename(questions_data, mode="export", grade="", use_bracket=False, use_vertical=False, use_answer=True):
    total_count = len(questions_data.get("basic", [])) + len(questions_data.get("advance", []))

    if mode == "onekey":
        # 一键出题模式：年级+出题数量
        parts = [grade, f"{total_count}题"]
    else:
        # 导出模式：知识点+数量
        cat_names = []
        seen = set()
        for item in questions_data.get("basic", []):
            if len(item) >= 1:
                cat = item[0]
                name = CATEGORY_NAMES.get(cat, cat)
                if name not in seen:
                    seen.add(name)
                    cat_names.append(name)
        for item in questions_data.get("advance", []):
            if len(item) >= 1:
                cat = item[0]
                name = CATEGORY_NAMES.get(cat, cat)
                if name not in seen:
                    seen.add(name)
                    cat_names.append(name)
        # 如果知识点名称超过10个字符，使用每个知识点前2个字
        if cat_names:
            combined = "".join(cat_names)
            if len(combined) > 10:
                short_names = [name[:2] for name in cat_names]
                names_part = "".join(short_names)
            else:
                names_part = "_".join(cat_names)
        else:
            names_part = "练习"
        parts = [names_part, f"{total_count}题"]

    # 附加功能
    extras = []
    if use_bracket:
        extras.append("带括号")
    if use_vertical:
        extras.append("竖式")
    if not use_answer:
        extras.append("无答案")
    if extras:
        parts.extend(extras)

    return "_".join(parts) + ".pdf"

def _frac_to_text_export(s):
    return FRAC_RE.sub(lambda m: f"{m.group(1)}/{m.group(2)}", s)

def _split_frac_parts(s):
    parts = []
    last = 0
    for m in FRAC_RE.finditer(s):
        if m.start() > last:
            parts.append(('text', s[last:m.start()]))
        parts.append(('frac', m.group(1), m.group(2)))
        last = m.end()
    if last < len(s):
        parts.append(('text', s[last:]))
    return parts

def _draw_mixed(c, x, y, parts, font_name, font_size, frac_font_size=None):
    if frac_font_size is None:
        frac_font_size = font_size
    cur_x = x
    line_y_offset = frac_font_size * 0.28
    for p in parts:
        if p[0] == 'text':
            c.setFont(font_name, font_size)
            c.drawString(cur_x, y, p[1])
            cur_x += c.stringWidth(p[1], font_name, font_size)
        else:
            num_str, den_str = p[1], p[2]
            nw = c.stringWidth(num_str, font_name, frac_font_size)
            dw = c.stringWidth(den_str, font_name, frac_font_size)
            box_w = max(nw, dw) + 4
            c.setFont(font_name, frac_font_size)
            c.drawCentredString(cur_x + box_w / 2,
                                y + line_y_offset + frac_font_size * 0.15,
                                num_str)
            c.setLineWidth(0.6)
            c.line(cur_x, y + line_y_offset, cur_x + box_w, y + line_y_offset)
            c.drawCentredString(cur_x + box_w / 2,
                                y + line_y_offset - frac_font_size * 1.0,
                                den_str)
            cur_x += box_w + 2
    c.setFont(font_name, font_size)
    return cur_x

def _safe_fmt_answer(ans):
    if ans is None:
        return "略"
    if isinstance(ans, tuple):
        if len(ans) == 2:
            return f"{ans[0]}余{ans[1]}"
        else:
            return str(ans)
    elif isinstance(ans, Fraction):
        if ans.denominator == 1:
            return str(ans.numerator)
        return f"{ans.numerator}/{ans.denominator}"
    elif isinstance(ans, float):
        ans = round(ans, 4)
        if ans.is_integer():
            return str(int(ans))
        return f"{ans:g}"
    else:
        return str(ans)

def _register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for fp in ['simsun.ttc', r'C:\Windows\Fonts\simsun.ttc']:
        try:
            pdfmetrics.registerFont(TTFont('SimSun', fp))
            return
        except Exception:
            pass
    for fp in ['msyh.ttf', r'C:\Windows\Fonts\msyh.ttf']:
        try:
            pdfmetrics.registerFont(TTFont('SimSun', fp))
            return
        except Exception:
            pass

_font_cache_export = None
def _get_font():
    global _font_cache_export
    if _font_cache_export:
        return _font_cache_export
    try:
        from reportlab.pdfbase import pdfmetrics
        pdfmetrics.getFont('SimSun')
        _font_cache_export = 'SimSun'
    except Exception:
        _font_cache_export = 'Helvetica'
    return _font_cache_export

def _draw_bold(c, x, y, text, font_name, font_size):
    c.drawString(x, y, text)
    c.drawString(x + 0.3, y, text)

def export_pdf(questions_data, use_vertical=False, use_answer=False, show_titles=False, mode="export", grade="", use_bracket=False):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors

    _register_fonts()
    fn_sun = _get_font()

    basic_qs = questions_data.get("basic", [])
    advance_qs = questions_data.get("advance", [])
    total_count = len(basic_qs) + len(advance_qs)

    basic_answers = []
    for item in basic_qs:
        if len(item) >= 3:
            basic_answers.append(item[2])
        else:
            basic_answers.append("略")
    advance_answers = []
    for item in advance_qs:
        if len(item) >= 3:
            advance_answers.append(item[2])
        else:
            advance_answers.append("略")
    all_answers = basic_answers + advance_answers

    export_dir = _get_export_dir()
    filename = _build_filename(questions_data, mode=mode, grade=grade, use_bracket=use_bracket, use_vertical=use_vertical, use_answer=use_answer)
    filepath = os.path.join(export_dir, filename)

    pw, ph = A4
    lm = 15 * mm
    rm = 15 * mm
    tm = 28 * mm
    bm = 18 * mm
    uw = pw - lm - rm

    reg_row_h = 8 * mm if not use_vertical else 32 * mm
    adv_row_h = 35 * mm

    MIXED_TYPES = {"cb_mix_addsub", "cb_mix_addmul", "cb_mix_addmulsub", "cb_mix_dec", "cb_mix_frac"}

    regular = []
    for i, item in enumerate(basic_qs):
        if len(item) >= 2:
            regular.append((i, item[0], item[1]))
    advanced = []
    for i, item in enumerate(advance_qs):
        if len(item) >= 2:
            advanced.append((i + len(basic_qs), item[1], item[0]))

    total_pages = [1]
    c = canvas.Canvas(filepath, pagesize=A4)
    c.setTitle("数学练习题")

    header_y = ph - tm + 12 * mm
    header_line_y = header_y - 2 * mm
    first_page_start_y = header_line_y - 6 * mm
    other_page_start_y = header_line_y - 6 * mm

    current_page = [1]
    cur_y = first_page_start_y

    def draw_header():
        c.setFont(fn_sun, 10)
        c.drawString(lm, header_y, "日期:_____年_____月_____日")
        c.drawRightString(pw - rm, header_y, f"共{total_count}题")
        c.setLineWidth(0.3)
        c.line(lm, header_line_y, pw - rm, header_line_y)
        c.setFont(fn_sun, 9)
        c.drawRightString(pw - rm, bm * 0.5, f"{current_page[0]}/{total_pages[0]}")
        c.setFont(fn_sun, 10)

    def new_page():
        c.showPage()
        current_page[0] += 1
        draw_header()
        return other_page_start_y

    draw_header()
    page_started = True

    if regular:
        renumbered = [(seq, q, t) for seq, (i, t, q) in enumerate(regular, 1)]
        regular_normal = [(seq, q, t) for seq, q, t in renumbered if t not in MIXED_TYPES]
        regular_mixed = [(seq, q, t) for seq, q, t in renumbered if t in MIXED_TYPES]

        if show_titles:
            c.setFont(fn_sun, 12)
            _draw_bold(c, lm, cur_y, f"基础计算（{len(regular)}题）", fn_sun, 12)
            cur_y -= reg_row_h

        col_w = uw / 4
        for idx, (seq, question, _qtype) in enumerate(regular_normal):
            col = idx % 4
            if col == 0 and idx > 0:
                cur_y -= reg_row_h
                if cur_y < bm + reg_row_h:
                    cur_y = new_page()
            x = lm + col * col_w
            label = f"{seq:>3}. "
            question = question.replace(" + ", "+").replace(" - ", "-").replace(" × ", "×").replace(" ÷ ", "÷")
            parts = _split_frac_parts(question)
            c.setFont(fn_sun, 11.5)
            lw = c.stringWidth(label, fn_sun, 11)
            c.drawString(x, cur_y, label)
            _draw_mixed(c, x + lw, cur_y, parts, fn_sun, 11)

        if regular_normal:
            last_col = len(regular_normal) % 4
            if last_col != 0:
                cur_y -= reg_row_h

        if regular_mixed:
            col_w_m = uw / 3
            for idx, (seq, question, _qtype) in enumerate(regular_mixed):
                col = idx % 3
                if col == 0 and idx > 0:
                    cur_y -= reg_row_h
                    if cur_y < bm + reg_row_h:
                        cur_y = new_page()
                x = lm + col * col_w_m
                label = f"{seq:>3}. "
                parts = _split_frac_parts(question)
                c.setFont(fn_sun, 11.5)
                lw = c.stringWidth(label, fn_sun, 11)
                c.drawString(x, cur_y, label)
                _draw_mixed(c, x + lw, cur_y, parts, fn_sun, 11)

    if advanced:
        adv_font_size = 10.5
        adv_line_gap = 5.5 * mm
        adv_work_gap = 20 * mm

        def wrap_text_adv(text, max_w, fn, fs):
            lines_out = []
            cur_line = ""
            plain = _frac_to_text_export(text)
            for ch in list(plain):
                test = cur_line + ch
                if c.stringWidth(test, fn, fs) <= max_w:
                    cur_line = test
                else:
                    if cur_line:
                        lines_out.append(cur_line)
                    cur_line = ch
            if cur_line:
                lines_out.append(cur_line)
            return lines_out if lines_out else [""]

        if regular:
            cur_y -= reg_row_h + 4 * mm
            if cur_y < bm + adv_line_gap + adv_work_gap:
                cur_y = new_page()
        else:
            cur_y = first_page_start_y

        if show_titles:
            c.setFont(fn_sun, 12)
            _draw_bold(c, lm, cur_y, f"运用题（{len(advanced)}题）", fn_sun, 12)
            cur_y -= reg_row_h

        FIGURE_SIZE_MM = 30

        def is_geometry(item):
            if not item or len(item) < 3:
                return False
            return item[2] in GEOMETRY_QUESTION_TYPES

        def draw_fig_right(item, col_x, col_w, top_y):
            if not is_geometry(item):
                return 0
            spec = extract_drawing_spec(item[2], item[1])
            if not spec:
                return 0
            fig_size_pt = FIGURE_SIZE_MM * mm
            fig_x = col_x + col_w - fig_size_pt
            fig_y = top_y - fig_size_pt
            draw_figure(c, fig_x, fig_y, fig_size_pt, fig_size_pt, spec)
            return fig_size_pt

        col_gap = 6 * mm
        col_w_adv = (uw - col_gap) / 2
        left_x = lm
        right_x = lm + col_w_adv + col_gap
        text_w_adv = col_w_adv - FIGURE_SIZE_MM * mm - 2 * mm

        pairs = []
        for i in range(0, len(advanced), 2):
            left_item = advanced[i]
            right_item = advanced[i + 1] if i + 1 < len(advanced) else None
            pairs.append((left_item, right_item))

        for left_item, right_item in pairs:
            left_label = f"{left_item[0] + 1}. "
            left_qtext = _frac_to_text_export(left_item[1])
            left_geo = is_geometry(left_item)
            left_w = text_w_adv if left_geo else col_w_adv

            right_label = f"{right_item[0] + 1}. " if right_item else ""
            right_qtext = _frac_to_text_export(right_item[1]) if right_item else ""
            right_geo = is_geometry(right_item) if right_item else False
            right_w = text_w_adv if right_geo else col_w_adv

            c.setFont(fn_sun, adv_font_size)
            left_lines = wrap_text_adv(left_label + left_qtext, left_w, fn_sun, adv_font_size) if left_qtext else []
            right_lines = wrap_text_adv(right_label + right_qtext, right_w, fn_sun, adv_font_size) if right_qtext else []
            max_lines = max(len(left_lines), len(right_lines))
            pair_height = max_lines * adv_line_gap + adv_work_gap

            if cur_y - pair_height < bm:
                cur_y = new_page()

            c.setFont(fn_sun, adv_font_size)
            for li, line_txt in enumerate(left_lines):
                c.drawString(left_x, cur_y - li * adv_line_gap, line_txt)
            draw_fig_right(left_item, left_x, col_w_adv, cur_y)

            if right_item:
                c.setFont(fn_sun, adv_font_size)
                for li, line_txt in enumerate(right_lines):
                    c.drawString(right_x, cur_y - li * adv_line_gap, line_txt)
                draw_fig_right(right_item, right_x, col_w_adv, cur_y)

            cur_y -= pair_height

    if use_answer and all_answers:
        c.showPage()
        current_page[0] += 1
        draw_header()
        cur_y = other_page_start_y

        c.setFont(fn_sun, 14)
        c.drawCentredString(pw / 2, cur_y - 3 * mm, "参 考 答 案")
        cur_y -= 10 * mm + 3 * mm

        c.setFont(fn_sun, 9)
        ans_line_h = 6 * mm
        ans_sep = "    "
        ans_texts = []
        for i, ans in enumerate(all_answers):
            ans_str = _safe_fmt_answer(ans)
            ans_texts.append(f"{i + 1}. {ans_str}")

        cur_line = ""
        for txt in ans_texts:
            test = cur_line + (ans_sep + txt if cur_line else txt)
            if c.stringWidth(test, fn_sun, 9) <= uw:
                cur_line = test
            else:
                if cur_line:
                    if cur_y < bm + ans_line_h:
                        cur_y = new_page()
                        c.setFont(fn_sun, 9)
                    c.drawString(lm, cur_y, cur_line)
                    cur_y -= ans_line_h
                cur_line = txt
        if cur_line:
            if cur_y < bm + ans_line_h:
                cur_y = new_page()
                c.setFont(fn_sun, 9)
            c.drawString(lm, cur_y, cur_line)
            cur_y -= ans_line_h

    c.save()

    if current_page[0] != total_pages[0]:
        total_pages[0] = current_page[0]
        current_page[0] = 1
        c = canvas.Canvas(filepath, pagesize=A4)
        c.setTitle("数学练习题")
        cur_y = first_page_start_y
        page_started = True
        draw_header()

        if regular:
            renumbered2 = [(seq, q, t) for seq, (i, t, q) in enumerate(regular, 1)]
            regular_normal = [(seq, q, t) for seq, q, t in renumbered2 if t not in MIXED_TYPES]
            regular_mixed = [(seq, q, t) for seq, q, t in renumbered2 if t in MIXED_TYPES]

            if show_titles:
                c.setFont(fn_sun, 12)
                _draw_bold(c, lm, cur_y, f"基础计算（{len(regular)}题）", fn_sun, 12)
                cur_y -= reg_row_h

            col_w = uw / 4
            for idx, (seq, question, _qtype) in enumerate(regular_normal):
                col = idx % 4
                if col == 0 and idx > 0:
                    cur_y -= reg_row_h
                    if cur_y < bm + reg_row_h:
                        c.showPage()
                        current_page[0] += 1
                        draw_header()
                        cur_y = other_page_start_y
                x = lm + col * col_w
                label = f"{seq:>3}. "
                question = question.replace(" + ", "+").replace(" - ", "-").replace(" × ", "×").replace(" ÷ ", "÷")
                parts = _split_frac_parts(question)
                c.setFont(fn_sun, 11.5)
                lw = c.stringWidth(label, fn_sun, 11)
                c.drawString(x, cur_y, label)
                _draw_mixed(c, x + lw, cur_y, parts, fn_sun, 11)

            if regular_normal:
                last_col = len(regular_normal) % 4
                if last_col != 0:
                    cur_y -= reg_row_h

            if regular_mixed:
                col_w_m = uw / 3
                for idx, (seq, question, _qtype) in enumerate(regular_mixed):
                    col = idx % 3
                    if col == 0 and idx > 0:
                        cur_y -= reg_row_h
                        if cur_y < bm + reg_row_h:
                            c.showPage()
                            current_page[0] += 1
                            draw_header()
                            cur_y = other_page_start_y
                    x = lm + col * col_w_m
                    label = f"{seq:>3}. "
                    parts = _split_frac_parts(question)
                    c.setFont(fn_sun, 11.5)
                    lw = c.stringWidth(label, fn_sun, 11)
                    c.drawString(x, cur_y, label)
                    _draw_mixed(c, x + lw, cur_y, parts, fn_sun, 11)

        if advanced:
            adv_font_size = 10.5
            adv_line_gap = 5.5 * mm
            adv_work_gap = 20 * mm

            if regular:
                cur_y -= reg_row_h + 4 * mm
                if cur_y < bm + adv_line_gap + adv_work_gap:
                    c.showPage()
                    current_page[0] += 1
                    draw_header()
                    cur_y = other_page_start_y
            else:
                cur_y = first_page_start_y

            if show_titles:
                c.setFont(fn_sun, 12)
                _draw_bold(c, lm, cur_y, f"运用题（{len(advanced)}题）", fn_sun, 12)
                cur_y -= reg_row_h

            col_gap = 6 * mm
            col_w_adv = (uw - col_gap) / 2
            left_x = lm
            right_x = lm + col_w_adv + col_gap
            text_w_adv = col_w_adv - FIGURE_SIZE_MM * mm - 2 * mm

            pairs = []
            for i in range(0, len(advanced), 2):
                left_item = advanced[i]
                right_item = advanced[i + 1] if i + 1 < len(advanced) else None
                pairs.append((left_item, right_item))

            for left_item, right_item in pairs:
                left_label = f"{left_item[0] + 1}. "
                left_qtext = _frac_to_text_export(left_item[1])
                left_geo = is_geometry(left_item)
                left_w = text_w_adv if left_geo else col_w_adv

                right_label = f"{right_item[0] + 1}. " if right_item else ""
                right_qtext = _frac_to_text_export(right_item[1]) if right_item else ""
                right_geo = is_geometry(right_item) if right_item else False
                right_w = text_w_adv if right_geo else col_w_adv

                c.setFont(fn_sun, adv_font_size)
                left_lines = wrap_text_adv(left_label + left_qtext, left_w, fn_sun, adv_font_size) if left_qtext else []
                right_lines = wrap_text_adv(right_label + right_qtext, right_w, fn_sun, adv_font_size) if right_qtext else []
                max_lines = max(len(left_lines), len(right_lines))
                pair_height = max_lines * adv_line_gap + adv_work_gap

                if cur_y - pair_height < bm:
                    c.showPage()
                    current_page[0] += 1
                    draw_header()
                    cur_y = other_page_start_y

                c.setFont(fn_sun, adv_font_size)
                for li, line_txt in enumerate(left_lines):
                    c.drawString(left_x, cur_y - li * adv_line_gap, line_txt)
                draw_fig_right(left_item, left_x, col_w_adv, cur_y)

                if right_item:
                    c.setFont(fn_sun, adv_font_size)
                    for li, line_txt in enumerate(right_lines):
                        c.drawString(right_x, cur_y - li * adv_line_gap, line_txt)
                    draw_fig_right(right_item, right_x, col_w_adv, cur_y)

                cur_y -= pair_height

        if use_answer and all_answers:
            c.showPage()
            current_page[0] += 1
            draw_header()
            cur_y = other_page_start_y
            c.setFont(fn_sun, 14)
            c.drawCentredString(pw / 2, cur_y - 3 * mm, "参 考 答 案")
            cur_y -= 10 * mm + 3 * mm
            c.setFont(fn_sun, 9)
            ans_line_h = 6 * mm
            ans_sep = "    "
            ans_texts = []
            for i, ans in enumerate(all_answers):
                ans_str = _safe_fmt_answer(ans)
                ans_texts.append(f"{i + 1}. {ans_str}")
            cur_line = ""
            for txt in ans_texts:
                test = cur_line + (ans_sep + txt if cur_line else txt)
                if c.stringWidth(test, fn_sun, 9) <= uw:
                    cur_line = test
                else:
                    if cur_line:
                        if cur_y < bm + ans_line_h:
                            c.showPage()
                            current_page[0] += 1
                            draw_header()
                            c.setFont(fn_sun, 9)
                        c.drawString(lm, cur_y, cur_line)
                        cur_y -= ans_line_h
                    cur_line = txt
            if cur_line:
                if cur_y < bm + ans_line_h:
                    c.showPage()
                    current_page[0] += 1
                    draw_header()
                    c.setFont(fn_sun, 9)
                c.drawString(lm, cur_y, cur_line)
                cur_y -= ans_line_h

        c.save()

    return filepath