# yingyu_phonetic.py — 国际音标表（按二级分组，供「内容→音标」选项使用）
# 与 yingyu_common.py 同款扁平格式，客户可直接手改。
# 结构：PHONETIC_GROUPS[一级分组][二级分组] = 多行字符串
# 每行格式：  音标 读法 中文读法 | 记忆口诀 | 例词1 /音标/ 意思1；例词2 /音标/ 意思2；例词3 /音标/ 意思3
# 例：/iː/ 长元音 依 | 织件毛衣 | bee /biː/ 蜜蜂；see /siː/ 看见；tea /tiː/ 茶
# 一级分组：元音 / 辅音
# 二级分组：长元音 / 短元音 / 双元音；爆破音·清 / 爆破音·浊 / 摩擦音·清 / 摩擦音·浊 /
#           破擦音·清 / 破擦音·浊 / 鼻音 / 半元音 / 舌侧音

PHONETIC_GROUPS = {

    "元音": {
        "长元音": """\
[ɑː] 长元音 啊 | 大叫一声 | car /kɑː/ 汽车；heart /hɑːt/ 心；far /fɑː/ 远
[ɔː] 长元音 噢 | 恍然大悟 | ball /bɔːl/ 球；horse /hɔːs/ 马；door /dɔː/ 门
[ɜː] 长元音 饿 | 三天没吃 | bird /bɜːd/ 鸟；girl /ɡɜːl/ 女孩；nurse /nɜːs/ 护士
[iː] 长元音 依 | 织件毛衣 | bee /biː/ 蜜蜂；see /siː/ 看见；tea /tiː/ 茶
[uː] 长元音 乌 | 火车鸣笛 | blue /bluː/ 蓝色；food /fuːd/ 食物；moon /muːn/ 月亮
""",

        "短元音": """\
[ʌ] 短元音 啊 | 尖角扎人 | bus /bʌs/ 巴士；cup /kʌp/ 杯子；duck /dʌk/ 鸭子
[ɒ] 短元音 哦 | 半边圆圈 | hot /hɒt/ 热的；dog /dɒɡ/ 狗；box /bɒks/ 盒子
[ə] 短元音 呃 | 小鹅倒立 | teacher /ˈtiːtʃə/ 老师；doctor /ˈdɒktə/ 医生；about /əˈbaʊt/ 关于
[ɪ] 短元音 衣 | 喊句口号 | big /bɪɡ/ 大的；pig /pɪɡ/ 猪；fish /fɪʃ/ 鱼
[ʊ] 短元音 乌 | 污污水坑 | book /bʊk/ 书；look /lʊk/ 看；good /ɡʊd/ 好的
[e] 短元音 诶 | 一指微笑 | bed /bed/ 床；red /red/ 红色；egg /eɡ/ 鸡蛋
[æ] 短元音 挨 | 三指咧嘴 | cat /kæt/ 猫；bag /bæɡ/ 包；hat /hæt/ 帽子
""",

        "双元音": """\
[ɪə] 双元音 衣饿 | 一只小鹅 | ear /ɪə/ 耳朵；near /nɪə/ 附近；here /hɪə/ 这里
[eə] 双元音 诶饿 | 挨饿小鹅 | hair /heə/ 头发；chair /tʃeə/ 椅子；bear /beə/ 熊
[ʊə] 双元音 乌饿 | 五只小鹅 | tour /tʊə/ 旅行；poor /pʊə/ 贫穷的；sure /ʃʊə/ 确信
[əʊ] 双元音 欧 | 疯狂呕吐 | home /həʊm/ 家；nose /nəʊz/ 鼻子；goat /ɡəʊt/ 山羊
[aʊ] 双元音 啊乌 | 老虎咆哮 | house /haʊs/ 房子；mouth /maʊθ/ 嘴；cow /kaʊ/ 奶牛
[eɪ] 双元音 诶一 | 应答一声 | cake /keɪk/ 蛋糕；name /neɪm/ 名字；rain /reɪn/ 雨
[aɪ] 双元音 啊一 | 爱的呼唤 | kite /kaɪt/ 风筝；like /laɪk/ 喜欢；time /taɪm/ 时间
[ɔɪ] 双元音 哦一 | 熬夜男孩 | boy /bɔɪ/ 男孩；toy /tɔɪ/ 玩具；enjoy /ɪnˈdʒɔɪ/ 喜欢
""",
    },

    "辅音": {
        "爆破音·清": """\
[p] 清辅音 波 | 婆婆泼水 | pen /pen/ 钢笔；pig /pɪɡ/ 猪；map /mæp/ 地图
[t] 清辅音 特 | 两指弹起 | ten /ten/ 十；cat /kæt/ 猫；hat /hæt/ 帽子
[k] 清辅音 科 | 轻轻咳嗽 | key /kiː/ 钥匙；cat /kæt/ 猫；book /bʊk/ 书
""",

        "爆破音·浊": """\
[b] 浊辅音 播 | 手剥香蕉 | bag /bæɡ/ 包；book /bʊk/ 书；big /bɪɡ/ 大的
[d] 浊辅音 的 | 小马跑步 | dog /dɒɡ/ 狗；desk /desk/ 课桌；bed /bed/ 床
[ɡ] 浊辅音 歌 | 农夫割草 | girl /ɡɜːl/ 女孩；bag /bæɡ/ 包；egg /eɡ/ 鸡蛋
""",

        "摩擦音·清": """\
[f] 清辅音 佛 | 轻轻抚摸 | fish /fɪʃ/ 鱼；five /faɪv/ 五；knife /naɪf/ 刀
[θ] 清辅音 思 | 轻咬舌尖 | three /θriː/ 三；thank /θæŋk/ 谢谢；mouth /maʊθ/ 嘴
[s] 清辅音 思 | 春蚕吐丝 | six /sɪks/ 六；sit /sɪt/ 坐；bus /bʌs/ 巴士
[ʃ] 清辅音 施 | 一位老师 | she /ʃiː/ 她；fish /fɪʃ/ 鱼；shop /ʃɒp/ 商店
[h] 清辅音 喝 | 大口喝水 | he /hiː/ 他；hot /hɒt/ 热的；hat /hæt/ 帽子
""",

        "摩擦音·浊": """\
[v] 浊辅音 乌 | 轻咬下唇 | very /ˈveri/ 非常；five /faɪv/ 五；love /lʌv/ 爱
[ð] 浊辅音 日 | 舌头发麻 | this /ðɪs/ 这个；that /ðæt/ 那个；mother /ˈmʌðə/ 母亲
[z] 浊辅音 兹 | 电钻打洞 | zoo /zuː/ 动物园；zero /ˈzɪərəʊ/ 零；nose /nəʊz/ 鼻子
[ʒ] 浊辅音 日 | 日头高照 | pleasure /ˈpleʒə/ 快乐；usually /ˈjuːʒuəli/ 通常；television /ˈtelɪvɪʒən/ 电视
[r] 浊辅音 若 | 卷起舌尖 | red /red/ 红色；run /rʌn/ 跑；rice /raɪs/ 米饭
""",

        "破擦音·清": """\
[tʃ] 清辅音 吃 | 大口吃饭 | chair /tʃeə/ 椅子；chicken /ˈtʃɪkɪn/ 鸡肉；watch /wɒtʃ/ 手表
[tr] 清辅音 戳 | 轻轻戳动 | tree /triː/ 树；train /treɪn/ 火车；try /traɪ/ 尝试
[ts] 清辅音 次 | 龇牙咧嘴 | cats /kæts/ 猫(复)；hats /hæts/ 帽子(复)；books /bʊks/ 书(复)
""",

        "破擦音·浊": """\
[dʒ] 浊辅音 之 | 蜘蛛织网 | juice /dʒuːs/ 果汁；orange /ˈɒrɪndʒ/ 橙子；page /peɪdʒ/ 页码
[dr] 浊辅音 捉 | 小鸟捉虫 | dress /dres/ 连衣裙；driver /ˈdraɪvə/ 司机；drink /drɪŋk/ 喝
[dz] 浊辅音 兹 | 工人伐木 | beds /bedz/ 床(复)；hands /hændz/ 手(复)；birds /bɜːdz/ 鸟(复)
""",

        "鼻音": """\
[m] 浊鼻音 木 | 嘴巴紧闭 | milk /mɪlk/ 牛奶；moon /muːn/ 月亮；map /mæp/ 地图
[n] 浊鼻音 呢 | 嘴巴微张 | nose /nəʊz/ 鼻子；nine /naɪn/ 九；sun /sʌn/ 太阳
[ŋ] 浊鼻音 嗯 | 舌头拱起 | sing /sɪŋ/ 唱歌；long /lɒŋ/ 长的；king /kɪŋ/ 国王
""",

        "半元音": """\
[j] 浊辅音 椰 | 一位爷爷 | yes /jes/ 是；you /juː/ 你；yellow /ˈjeləʊ/ 黄色的
[w] 浊辅音 握 | 学生是我 | water /ˈwɔːtə/ 水；we /wiː/ 我们；watch /wɒtʃ/ 手表
""",

        "舌侧音": """\
[l] 浊辅音 了 | 气从旁流 | leg /leɡ/ 腿；look /lʊk/ 看；lion /ˈlaɪən/ 狮子
""",
    },
}
