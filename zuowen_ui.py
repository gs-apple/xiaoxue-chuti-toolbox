# zuowen_ui.py — 作文标签页 (tkinter 版，保留原版布局)
import tkinter as tk
from tkinter import ttk
from widgets import GradientButton

BG = "#f0f0f0"
MODERN_BTN = dict(bg="#2563eb", fg="white", font=("Microsoft YaHei", 10, "bold"),
                   bd=0, relief="flat", activebackground="#1d4ed8",
                   activeforeground="white", width=10, height=1,
                   cursor="hand2")


class ZuowenTabWidget:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=BG)
        self._init_ui()

    def _init_ui(self):
        main_layout = tk.Frame(self.frame, bg=BG)
        main_layout.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ========== 顶部：课本作文 + 自由作文 ==========
        top_frame = tk.Frame(main_layout, bg=BG)
        top_frame.pack(fill=tk.X)

        # 1.1 课本作文
        textbook_group = ttk.LabelFrame(top_frame, text="课本作文")
        textbook_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        textbook_inner = tk.Frame(textbook_group, bg=BG)
        textbook_inner.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # 左侧：年级 + 单元列表
        left_frame = tk.Frame(textbook_inner, bg=BG)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.grade_combo = ttk.Combobox(left_frame, width=8, state="readonly",
                                         values=["一年级", "二年级", "三年级",
                                                 "四年级", "五年级", "六年级",
                                                 "七年级", "八年级", "九年级"])
        self.grade_combo.current(0)
        self.grade_combo.pack(fill=tk.X, pady=(0, 4))
        self.grade_combo.bind("<<ComboboxSelected>>", lambda e: self._on_grade_changed())

        self.unit_zuowen_titles = {
            "一年级": [
                "第一单元：我说我做",
                "第二单元：一起做游戏",
                "第三单元：大自然的声音",
                "第四单元：我最喜欢的玩具",
                '第五单元：身边的"小事"',
                "第六单元：长大以后做什么",
                "第七单元：这样想象真有趣",
                "第八单元：这样想象真有趣（二）"
            ],
            "二年级": [
                "第一单元：我的好朋友",
                "第二单元：看图讲故事",
                "第三单元：我最喜欢的季节",
                "第四单元：我的奇思妙想",
                "第五单元：我的动物朋友",
                "第六单元：学写留言条",
                "第七单元：写观察日记",
                "第八单元：有趣的动物"
            ],
            "三年级": [
                "第一单元：我的植物朋友",
                "第二单元：看图画，写一写",
                "第三单元：中华传统节日",
                "第四单元：续写故事",
                "第五单元：我们眼中的缤纷世界",
                "第六单元：这儿真美",
                "第七单元：我有一个想法",
                "第八单元：那次玩得真高兴"
            ],
            "四年级": [
                "第一单元：推荐一个好地方",
                '第二单元：小小"动物园"',
                "第三单元：写观察日记",
                "第四单元：我和____过一天",
                "第五单元：生活中的万花筒",
                "第六单元：生活需要掌声",
                '第七单元：我的"自画像"',
                "第八单元：故事新编"
            ],
            "五年级": [
                "第一单元：我的心爱之物",
                "第二单元：漫画里的我",
                "第三单元：民间故事讲述会",
                "第四单元：二十年后的家乡",
                "第五单元：介绍一种事物",
                "第六单元：我想对你说",
                "第七单元：____即景",
                "第八单元：推荐一本书"
            ],
            "六年级": [
                "第一单元：变形记",
                "第二单元：多彩的生活",
                "第三单元：让真情自然流露",
                "第四单元：心愿",
                "第五单元：围绕中心意思写",
                "第六单元：学写倡议书",
                "第七单元：我的拿手好戏",
                "第八单元：这样的人让我感动"
            ],
            "七年级": [
                "第一单元：这就是我",
                "第二单元：有你，真好",
                "第三单元：写人要抓住特点",
                "第四单元：思路要清晰",
                "第五单元：如何突出中心",
                "第六单元：文从字顺",
                "第七单元：语言要连贯",
                "第八单元：说明事物要抓住特征"
            ],
            "八年级": [
                "第一单元：新闻采访与写作",
                "第二单元：学写传记",
                "第三单元：学习描写景物",
                "第四单元：学写读后感",
                "第五单元：表达要得体",
                "第六单元：学写游记",
                "第七单元：学写故事",
                "第八单元：说明的顺序"
            ],
            "九年级": [
                "第一单元：观点要明确",
                "第二单元：驳论文写作",
                "第三单元：走进小说天地",
                "第四单元：选择你能驾驭的体裁写作",
                "第五单元：扩写与缩写",
                "第六单元：学写议论文",
                "第七单元：青春随想",
                "第八单元：走进传统文化"
            ]
        }

        self.unit_zuowen_requires = {
            "一年级": [
                "用简单的话说说自己会做什么，语句通顺，表达清楚。",
                "描述和同学一起做游戏的经过，写出游戏的乐趣。",
                "仔细听一听大自然的声音，用几句话写下来。",
                "写自己最喜欢的一件玩具，说明喜欢的理由。",
                "写身边发生的一件小事，语句通顺，意思完整。",
                "用几句话说说长大以后想做什么，并说明原因。",
                "发挥想象，写一件有趣的事，内容要奇特有趣。",
                "继续发挥想象，写一个新奇有趣的故事。"
            ],
            "二年级": [
                "介绍自己的好朋友，写出他（她）的特点和你们的故事。",
                "看图，发挥想象，把图中的故事写下来，语句通顺。",
                "写自己最喜欢的季节，说明喜欢的原因，描写要具体。",
                "写自己的奇思妙想，内容要大胆、有创意。",
                "介绍自己喜欢的一种动物，写出它的特点。",
                "学写留言条，格式正确，内容清楚，语言简洁。",
                "选择一种植物或动物，连续观察几天，写观察日记。",
                "写一种有趣的动物，突出它有趣的地方。"
            ],
            "三年级": [
                "介绍自己喜欢的一种植物，写出外形和特点，语言生动。",
                "仔细观察一幅图画，展开想象，把图中的内容写成一段话。",
                "介绍一个中华传统节日，写出节日的习俗和自己的感受。",
                "读完故事后，发挥想象，续写故事的结尾，情节合理。",
                "观察身边的一处景物或一件事物，写出自己的发现和感受。",
                "描写一处美丽的地方，用上好词好句，让人有身临其境的感觉。",
                "写自己对某件事情的想法或建议，观点明确，理由充分。",
                "写一次玩得开心的经历，把过程写清楚，表达出快乐的心情。"
            ],
            "四年级": [
                "推荐一个你觉得好的地方，写清楚理由，语言要有感染力。",
                "把家人比作动物园里的动物，抓住特点，幽默风趣地描写。",
                "选择一种事物连续观察，记录变化过程，内容真实具体。",
                "想象和某个人物（真实或虚构）过一天，写出有趣的经历。",
                "写生活中发生的一件事，内容要具体，有自己的感受。",
                "写一次受到鼓励或给别人鼓励的经历，写出内心的感受。",
                "介绍自己，抓住外貌、性格、爱好等特点，语言生动有趣。",
                "选一个熟悉的故事，改编成新的故事，情节要合理有创意。"
            ],
            "五年级": [
                "介绍自己的一件心爱之物，写出对它的感情，详略得当。",
                "看漫画，联系实际写自己的感受和想法，观点明确。",
                "讲一个民间故事，内容完整，情节生动，有自己的理解。",
                "想象二十年后家乡的变化，内容要具体，充满正能量。",
                "介绍一种事物，说清楚它的特点，语言准确，条理清晰。",
                "给亲人或朋友写一封信，表达真实情感，格式正确。",
                "描写一处景物，写出动态和静态，语言生动，有画面感。",
                "推荐一本好书，写出主要内容和推荐理由，语言有感染力。"
            ],
            "六年级": [
                "展开想象，写自己或某物变形后的经历，内容奇特有趣。",
                "写生活中的一件事，内容丰富，有真情实感。",
                "写一件让自己感动或难忘的事，真情流露，感情真挚。",
                "写自己的一个心愿，说明心愿的内容和原因，感情真实。",
                "围绕一个中心意思选材，内容集中，重点突出。",
                "写一份倡议书，格式正确，观点鲜明，语言有号召力。",
                "写自己的一项拿手好戏，通过具体事例展示特长。",
                "写一个令自己感动的人，抓住细节，情感真挚感人。"
            ],
            "七年级": [
                "写一篇介绍自己的作文，突出个性特点，语言自然真实。",
                "写一个对你很重要的人，表达真挚的情感，内容具体。",
                "写一个人，抓住外貌、动作、语言等特点，形象鲜明。",
                "记叙一件事，思路清晰，条理分明，详略得当。",
                "写一篇记叙文，围绕中心选材，突出主题，内容充实。",
                "写一篇文章，语言通顺，表达流畅，用词准确。",
                "写一篇文章，句与句、段与段之间衔接自然，语言连贯。",
                "介绍一种事物，抓住特征，说明清楚，条理分明。"
            ],
            "八年级": [
                "完成一次新闻采访，写一篇新闻稿，要素齐全，语言简洁。",
                "选一个你熟悉的人，为他（她）写一篇小传，内容真实。",
                "描写一处景物，运用多种描写手法，语言生动形象。",
                "读完一本书或一篇文章，写读后感，联系实际，有真情实感。",
                "根据具体情境写作，语言表达得体，符合交际需求。",
                "写一篇游记，写出游览顺序和所见所感，语言生动。",
                "写一个完整的故事，情节合理，人物形象鲜明，有吸引力。",
                "写一篇说明文，按照合理的顺序介绍事物，条理清晰。"
            ],
            "九年级": [
                "写一篇议论文，观点明确，论据充分，论证有力。",
                "写一篇驳论文，找准对方观点的漏洞，反驳有理有据。",
                "写一篇与小说相关的文章，可以是读后感或创作片段。",
                "根据自己的特长选择合适的文体写作，扬长避短。",
                "将一篇文章扩写或缩写，保留主要内容，语言流畅。",
                "写一篇完整的议论文，论点、论据、论证三要素齐全。",
                "围绕青春主题，写出自己的思考与感悟，内容真实感人。",
                "写一篇介绍传统文化的文章，内容丰富，有文化内涵。"
            ]
        }

        self.unit_list = tk.Listbox(left_frame, height=8, font=("Microsoft YaHei", 10))
        self.unit_list.pack(fill=tk.BOTH, expand=True)
        self.unit_list.insert(0, *self.unit_zuowen_titles["一年级"])
        self.unit_list.bind("<<ListboxSelect>>", lambda e: self._on_unit_selected())

        # 右侧：作文要求
        right_frame = tk.Frame(textbook_inner, bg=BG)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        tk.Label(right_frame, text="作文要求", font=("Microsoft YaHei", 10)).pack(anchor="w")
        self.unit_require_text = tk.Text(right_frame, bg=BG, height=6, wrap=tk.WORD, state="disabled",
                                          font=("Microsoft YaHei", 10))
        self.unit_require_text.pack(fill=tk.BOTH, expand=True)

        # 1.2 自由作文
        free_group = ttk.LabelFrame(top_frame, text="自由作文")
        free_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        free_inner = tk.Frame(free_group, bg=BG)
        free_inner.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        row0 = tk.Frame(free_inner, bg=BG)
        row0.pack(fill=tk.X, pady=2)
        tk.Label(row0, text="作文类型", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.type_combo = ttk.Combobox(row0, width=12, state="readonly",
                                        values=["续写", "命题作文", "半命题作文",
                                                "话题作文", "材料作文"])
        self.type_combo.current(0)
        self.type_combo.pack(side=tk.LEFT, padx=(5, 0))

        row1 = tk.Frame(free_inner, bg=BG)
        row1.pack(fill=tk.X, pady=2)
        tk.Label(row1, text="作文题目", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.title_edit = tk.Entry(row1, font=("Microsoft YaHei", 10))
        self.title_edit.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        tk.Label(free_inner, text="作文要求", font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(4, 0))
        self.require_text = tk.Text(free_inner, bg=BG, height=4, wrap=tk.WORD,
                                     font=("Microsoft YaHei", 10))
        self.require_text.pack(fill=tk.X)

        # ========== 搜索区域 ==========
        search_frame = tk.Frame(main_layout, bg=BG)
        search_frame.pack(fill=tk.X, pady=(5, 0))

        self.search_edit = tk.Entry(search_frame, font=("Microsoft YaHei", 10))
        self.search_edit.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.search_btn = tk.Button(search_frame, text="搜索", width=6)
        self.search_btn.pack(side=tk.LEFT, padx=(5, 0))

        # ========== 例文区域 ==========
        example_group = ttk.LabelFrame(main_layout, text="例文")
        example_group.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        example_frame = tk.Frame(example_group, bg=BG, relief=tk.SUNKEN, bd=1)
        example_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        example_scroll = tk.Scrollbar(example_frame)
        example_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.example_text = tk.Text(example_frame, bg="white", wrap=tk.WORD, height=8,
                                     yscrollcommand=example_scroll.set,
                                     font=("Microsoft YaHei", 11))
        self.example_text.pack(fill=tk.BOTH, expand=True)
        example_scroll.config(command=self.example_text.yview)

        # ========== 功能区 ==========
        func_group = ttk.LabelFrame(main_layout, text="功能区")
        func_group.pack(fill=tk.X, pady=(5, 0))
        func_inner = tk.Frame(func_group, bg=BG)
        func_inner.pack(padx=5, pady=3)

        self.clear_btn = GradientButton(func_inner, text="清空例文", width=100, height=32)
        self.export_word_btn = GradientButton(func_inner, text="导出Word", width=100, height=32)
        self.export_pdf_btn = GradientButton(func_inner, text="导出PDF", width=100, height=32)

        func_inner.columnconfigure(0, weight=1)
        func_inner.columnconfigure(4, weight=1)
        self.clear_btn.grid(row=0, column=1, padx=3)
        self.export_word_btn.grid(row=0, column=2, padx=3)
        self.export_pdf_btn.grid(row=0, column=3, padx=3)

    def _on_grade_changed(self):
        grade = self.grade_combo.get()
        self.unit_list.delete(0, tk.END)
        self.unit_list.insert(0, *self.unit_zuowen_titles[grade])
        self.unit_require_text.config(state="normal")
        self.unit_require_text.delete("1.0", tk.END)
        self.unit_require_text.config(state="disabled")

    def _on_unit_selected(self):
        sel = self.unit_list.curselection()
        if not sel:
            return
        row = sel[0]
        grade = self.grade_combo.get()
        requires = self.unit_zuowen_requires.get(grade, [])
        self.unit_require_text.config(state="normal")
        self.unit_require_text.delete("1.0", tk.END)
        if row < len(requires):
            self.unit_require_text.insert("1.0", requires[row])
        self.unit_require_text.config(state="disabled")
