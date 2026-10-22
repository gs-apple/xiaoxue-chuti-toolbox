# -*- coding: utf-8 -*-
"""
yy.suyang123.com 英语朗读宝 全站小学课本课文爬虫
- 数据源: https://sitemap.suyang123.com/sitemap.xml (全站URL清单)
- 抓取目标: /xiaoxue/{年级}/{版本}_{学期}_listen{N}.html 的课文原文(英文) + 翻译(中文)
- 输出: D:/NEW/suyang_dump/{版本}/{年级}/{学期}/Unit N.txt
  每个文件内容: 每对 [英文行, 中文行, 空行]
- 特性: 断点续爬(跳过已存在文件)、并发6线程、失败重试3次、失败清单
"""
import urllib.request, re, os, sys, time, json

BASE = 'https://yy.suyang123.com'
OUT = r'D:\NEW\suyang_dump'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

GRADE_NAMES = {
    'yinianji': '一年级', 'ernianji': '二年级', 'sannianji': '三年级',
    'sinianji': '四年级', 'wunianji': '五年级', 'liunianji': '六年级',
}
SEM_NAMES = {'shangce': '上册', 'xiace': '下册'}

# 版本前缀 -> 中文名（便于识别；未知前缀保留原名）
VERSION_NAMES = {
    'rjbp': '人教版PEP', 'rjbxqd': '人教版新起点', 'rjjtb': '人教版精通版',
    'bjb': '北京版', 'bsdyq': '北师大版(一起)', 'bsdsq': '北师大版(三起)',
    'slb': '陕旅版', 'xlb': '湘鲁版', 'lkbwsz': '辽科版(五四制)',
    'wybyq': '外研版(一起)', 'wybsq': '外研版(三起)', 'wyjb': '外研Join In',
    'hjbsz': '冀教版(三起)', 'hjbsq': '冀教版(一起)', 'njylb': '牛津译林版',
    'njshbdb': '南京新版(沪版?)', 'kpb': '科普版', 'cjb': '剑桥版',
    'gdkxb': '广东开心版', 'cqdxb': '重庆大学版', 'qhdxb': '清华大学出版社',
    'jjbyq': '接力版(一起)', 'jjbsq': '接力版(三起)', 'jkbe': '教科版(鄂教版)',
    'jlbsq': '剑桥版?', 'lsdsq': '辽师大版(三起)', 'mjb': '闽教版',
    'gzb': '广州版', 'gzj kb': '', 'gzjkb': '广州教科版', 'rjdtb': '人教版(地方?)',
    'xglw': '湘教(牛津)版', 'xgnqsb': '新课标(内部?)', 'xsb': '新思维版',
    'yjhwb': '一年级核心版?', 'xlbs': '湘鲁(五年级?)', 'wyxjj': '外研衔接?',
    'wyxqh': '外研新标准?', 'lkbwsz': '辽科五四制', 'slb': '陕旅版',
}


def fetch(url, retries=3, timeout=20):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'replace')
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(1 + i)


def parse_page(html):
    """提取页面中所有 英文+中文 对"""
    items = re.findall(
        r'<span class="en"[^>]*>(.*?)</span>\s*<span class="cn"[^>]*>(.*?)</span>',
        html, re.S)
    out = []
    for en, cn in items:
        en = re.sub(r'<[^>]+>', '', en).strip()
        cn = re.sub(r'<[^>]+>', '', cn).strip()
        cn = cn.replace('翻译：', '').strip()
        if en:
            out.append((en, cn))
    return out


def get_listen_urls():
    sm = fetch('https://sitemap.suyang123.com/sitemap.xml')
    urls = re.findall(r'<loc>([^<]+)</loc>', sm)
    listen = [u for u in urls if '/xiaoxue/' in u and 'listen' in u]
    return listen


def crawl_one(url):
    m = re.search(r'/xiaoxue/(\w+)/(\w+)_(\w+)_listen(\d+)\.html', url)
    if not m:
        return ('skip', url, '')
    grade, pref, sem, unit = m.groups()
    if sem not in SEM_NAMES:
        return ('skip', url, '')
    sem_name = SEM_NAMES[sem]
    grade_name = GRADE_NAMES.get(grade, grade)
    out_dir = os.path.join(OUT, pref, grade_name, sem_name)
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, 'Unit %s.txt' % unit)
    if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
        return ('exists', out_file, '')
    try:
        html = fetch(url)
    except Exception:
        return ('fail', url, 'fetch')
    items = parse_page(html)
    if not items:
        return ('empty', url, '')
    body = []
    for en, cn in items:
        body.append(en)
        body.append(cn)
        body.append('')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(body))
    return ('ok', out_file, '')


def main():
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    print('获取 sitemap 单元页清单...')
    urls = get_listen_urls()
    print('单元页总数:', len(urls))
    os.makedirs(OUT, exist_ok=True)

    stats = {'ok': 0, 'exists': 0, 'fail': 0, 'empty': 0, 'skip': 0}
    fails = []
    done = 0
    lock = threading.Lock()

    def worker(url):
        return crawl_one(url)

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(worker, u): u for u in urls}
        for fut in as_completed(futs):
            u = futs[fut]
            try:
                st, path, why = fut.result()
            except Exception:
                st, path, why = 'fail', u, 'exception'
            with lock:
                stats[st] += 1
                done += 1
                if st in ('fail', 'empty'):
                    fails.append((u, why))
                if done % 200 == 0 or done == len(urls):
                    print('[%d/%d] ok=%d exists=%d fail=%d empty=%d skip=%d'
                          % (done, len(urls), stats['ok'], stats['exists'],
                             stats['fail'], stats['empty'], stats['skip']), flush=True)

    with open(os.path.join(OUT, '_fail_list.json'), 'w', encoding='utf-8') as f:
        json.dump(fails, f, ensure_ascii=False, indent=1)
    print('完成. 统计:', stats)
    print('失败清单:', os.path.join(OUT, '_fail_list.json'), '共', len(fails), '条')


if __name__ == '__main__':
    main()
