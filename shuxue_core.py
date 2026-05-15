# shuxue_core.py — 小学数学题目生成核心（最终稳定版）
# 所有变量均有明确赋值，无递归，内置安全上限

import random
import math
import re
from fractions import Fraction

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
    "cb_find_rule", "cb_arithmetic", "cb_simple_calc", "cb_frac_skill", "cb_new_op",
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
        q_val = random.randint(10, 200)
        return f"{b_val * q_val} ÷ {b_val} =", q_val

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
            if use_bracket and random.choice([True, False]):
                expr = f"({nums[0]} {ops[0]} {nums[1]}) {ops[1]} {nums[2]} ="
            else:
                expr = f"{nums[0]} {ops[0]} {nums[1]} {ops[1]} {nums[2]} ="
            return expr, ans
        return "100 + 200 + 300 =", 600

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

            # 如果启用括号，有概率生成带括号的形式
            if use_bracket and random.random() < 0.4:
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
                if use_bracket and random.random() < 0.4:
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
                    ans = round(ans, 2)

                return expr, ans
            except (ZeroDivisionError, ValueError, TypeError):
                continue

        # 保底题目
        return "123 + 456 + 789 + 101 =", 1469

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
        return "1.2 + 2.3 =", 3.5

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
        start = random.randint(1, 20)
        diff = random.randint(2, 10)
        nums = [start + diff * i for i in range(4)]
        ans = start + diff * 4
        return f"找规律：{nums[0]}，{nums[1]}，{nums[2]}，{nums[3]}，____", ans

    def gen_arithmetic(self):
        start = random.randint(1, 20)
        diff = random.randint(2, 5)
        n = random.randint(5, 10)
        ans = start + (n - 1) * diff
        return f"等差数列：首项{start}，公差{diff}，第{n}项是____", ans

    def gen_simple_calc(self):
        a_val = random.randint(2, 9)
        b_val = random.randint(11, 99)
        return f"{a_val} × {b_val} + {a_val} × {100 - b_val} =", a_val * 100

    def gen_frac_skill(self):
        a_frac = _make_frac()
        b_frac = _make_frac()
        return f"{_frac(a_frac)} + {_frac(b_frac)} =", a_frac + b_frac

    def gen_new_op(self):
        return "定义 a △ b = a×b + a，求 3 △ 4", 15

    def gen_sum_diff(self):
        total = random.randint(20, 200)
        diff = random.randint(2, 30)
        big = (total + diff) // 2
        small = total - big
        return f"甲乙两数之和是{total}，差是{diff}，求这两个数。", f"{big}和{small}"

    def gen_age(self):
        child = random.randint(5, 15)
        father = random.randint(25, 45)
        return f"小明{child}岁，爸爸{father}岁，爸爸比小明大几岁？", father - child

    def gen_tree(self):
        length = random.randint(50, 500)
        space = random.choice([3,4,5,6,8,10])
        return f"一条路长{length}米，每隔{space}米种一棵树，两端都种，共种多少棵？", (length // space) + 1

    def gen_chicken_rabbit(self):
        chickens = random.randint(5, 30)
        rabbits = random.randint(5, 20)
        heads = chickens + rabbits
        legs = chickens * 2 + rabbits * 4
        return f"鸡兔同笼，共有{heads}个头，{legs}只脚，鸡兔各几只？", f"鸡{chickens}只，兔{rabbits}只"

    def gen_duck(self):
        return "分苹果，每人3个少2个，每人4个多1个，有几个人？", 3

    def gen_project(self):
        a_days = random.randint(5, 20)
        b_days = random.randint(5, 20)
        ans = Fraction(a_days * b_days, a_days + b_days)
        return f"一项工程，甲单独做{a_days}天完成，乙单独做{b_days}天完成，合作几天完成？", _frac(ans)

    def gen_form(self):
        distance = random.randint(100, 500)
        va = random.randint(20, 60)
        vb = random.randint(20, 60)
        ans = distance // (va + vb)
        return f"甲乙相距{distance}千米，相向而行，甲速{va}千米/时，乙速{vb}千米/时，几时相遇？", f"{ans}时"

    def gen_concentration(self):
        salt = random.randint(10, 50)
        water = random.randint(100, 300)
        pct = round(salt / (salt + water) * 100, 1)
        return f"盐{salt}克溶入水{water}克中，盐水浓度是多少？", f"{pct}%"

    def gen_perimeter(self):
        l_val = random.randint(5, 20)
        w_val = random.randint(3, 15)
        return f"长方形长{l_val}厘米宽{w_val}厘米，求周长。", (l_val + w_val) * 2

    def gen_3d_graph(self):
        a_val = random.randint(3, 10)
        return f"棱长{a_val}厘米的正方体，求体积。", a_val ** 3

    def gen_equal_area(self):
        area = random.randint(12, 48)
        return f"三角形和平行四边形等底等高，平行四边形面积{area}平方厘米，三角形面积是多少？", area // 2

    def gen_graph_count(self):
        n_val = random.randint(3, 6)
        return f"{n_val}个点两两连线，共能连多少条线段？", n_val * (n_val - 1) // 2

    def gen_graph_split(self):
        n_val = random.randint(2, 5)
        return f"一条线段，{n_val}个点（不含端点），能把线段分成几段？", n_val + 1

    def gen_odd_even(self):
        a_val = random.randint(1, 50)
        b_val = random.randint(1, 50)
        return f"{a_val} + {b_val} 的和是奇数还是偶数？", "奇数" if (a_val + b_val) % 2 else "偶数"

    def gen_whole_div(self):
        num = random.randint(100, 999)
        div = random.choice([2, 3, 5, 9])
        return f"{num} 能否被 {div} 整除？", "能" if num % div == 0 else "不能"

    def gen_remainder(self):
        a_val = random.randint(20, 200)
        b_val = random.randint(3, 9)
        return f"{a_val} ÷ {b_val} 的余数是多少？", a_val % b_val

    def gen_prime(self):
        num = random.randint(10, 50)
        is_prime = num >= 2 and all(num % i != 0 for i in range(2, int(math.sqrt(num)) + 1))
        return f"{num} 是质数还是合数？", "质数" if is_prime else "合数"

    def gen_gcd_lcm(self):
        a_val = random.randint(10, 60)
        b_val = random.randint(10, 60)
        if random.random() < 0.5:
            return f"求{a_val}和{b_val}的最大公约数。", math.gcd(a_val, b_val)
        else:
            return f"求{a_val}和{b_val}的最小公倍数。", a_val * b_val // math.gcd(a_val, b_val)

    def gen_logic(self):
        return "小明说：'今天不是星期一也不是星期二。'小红说：'今天是星期三。'如果只有一人说对了，今天是星期几？", "推理题（答案略）"

    def gen_arrange(self):
        return "煎3张饼，每面要2分钟，锅里每次最多放2张，最少要几分钟？", 6

    def gen_best(self):
        return "a+b=12，a×b的最大值是多少？", 36

    def gen_draw(self):
        n_val = random.randint(3, 7)
        return f"{n_val}个苹果放入3个抽屉，至少有一个抽屉有几个苹果？", "抽屉原理（略）"

    def gen_container(self):
        a_set = random.randint(10, 30)
        b_set = random.randint(10, 30)
        both = random.randint(3, min(a_set, b_set))
        return f"一个班{a_set}人会画画，{b_set}人会唱歌，两项都会的有{both}人，至少会一项的有多少人？", a_set + b_set - both


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
        max_attempts = min(count * 20, 2000)
        
        # 如果是提升题且已使用爬虫题，减少生成数量
        target_count = count
        if q_type in ADVANCE_TYPES and spider_questions:
            # 计算该题型在爬虫题中的数量
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
                    if q_type in ADVANCE_TYPES:
                        advance.append((q_type, question, answer))
                    else:
                        basic.append((q_type, question, answer))
                    generated += 1
            except Exception:
                continue

    random.shuffle(basic)
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
        ("cb_100in", 6), ("cb_mul_2x1", 6), ("cb_div_1digit", 6),
        ("cb_mix_addmulsub", 4), ("cb_find_rule", 4), ("cb_tree", 4)
    ],
    "四年级": [
        ("cb_10000in", 4), ("cb_mul_2x2", 4), ("cb_div_2digit", 4),
        ("cb_mix_addmulsub", 4), ("cb_sum_diff", 4), ("cb_perimeter", 4),
        ("cb_chicken_rabbit", 3), ("cb_age", 3)
    ],
    "五年级": [
        ("cb_dec_addsub", 4), ("cb_mul_dec", 4), ("cb_div_dec", 4),
        ("cb_frac_addsub", 3), ("cb_mul_frac", 3), ("cb_mix_dec", 3),
        ("cb_project", 3), ("cb_form", 3), ("cb_concentration", 2), ("cb_3d_graph", 2)
    ],
    "六年级": [
        ("cb_frac_addsub", 4), ("cb_frac_skill", 3), ("cb_mix_frac", 3),
        ("cb_new_op", 3), ("cb_gcd_lcm", 3), ("cb_container", 3),
        ("cb_best", 3), ("cb_draw", 2), ("cb_equal_area", 2)
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