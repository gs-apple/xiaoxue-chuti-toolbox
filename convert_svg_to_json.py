# -*- coding: utf-8 -*-
"""
将 makemeahanzi SVG 笔顺文件合并为单个紧凑 JSON 文件。
运行一次即可：python convert_svg_to_json.py
"""
import os
import re
import json
import glob

SVG_DIR = os.path.join(os.path.dirname(__file__), 'makemeahanzi-master', 'svgs')
OUTPUT = os.path.join(os.path.dirname(__file__), 'stroke_data.json')


def parse_svg_paths(svg_text):
    all_paths = re.findall(r'd="([^"]+)"', svg_text)
    stroke_paths = []
    seen = set()
    for p in all_paths:
        s = p.strip()
        if not re.match(r'^M\s*[\d]', s):
            continue
        if 'Q' not in s and 'C' not in s:
            continue
        if len(s) < 30:
            continue
        fp = s[:60]
        if fp in seen:
            continue
        seen.add(fp)
        stroke_paths.append(s)
    return stroke_paths


def main():
    data = {}
    svg_files = glob.glob(os.path.join(SVG_DIR, '*.svg'))
    total = len(svg_files)
    print(f"Found {total} SVG files")

    for i, fp in enumerate(svg_files):
        code = int(os.path.splitext(os.path.basename(fp))[0])
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                text = f.read()
            paths = parse_svg_paths(text)
            if paths:
                data[str(code)] = paths
        except Exception:
            pass
        if (i + 1) % 1000 == 0:
            print(f"  processed {i+1}/{total}")

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"Done! {len(data)} characters -> {OUTPUT} ({size_kb:.0f} KB)")


if __name__ == '__main__':
    main()
