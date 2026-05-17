"""
Build custom pinyin font - extend vertical stems only
"""
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.boundsPen import BoundsPen

SRC = 'fonts/pinyin.ttf'
DST = 'fonts/pinyin_custom.ttf'

# Glyphs with ascender stems to extend upward
ASCENDER_GLYPHS = {'t', 'd', 'k', 'l', 'h', 'b', 'f'}
# Glyphs with descender stems to extend downward
DESCENDER_GLYPHS = {'g', 'y', 'j'}
# How much to extend (font units, ~1mm)
EXTEND_UP = 280
EXTEND_DOWN = 280
# Points near the top/bottom are considered part of the stem
STEM_THRESHOLD = 250
# Slight bold expansion
BOLD_EXPAND = 6

def extend_stems(glyph, glyf, glyph_set, extend_up=0, extend_down=0):
    """Move topmost/bottommost points to extend vertical stems"""
    pen = TTGlyphPen(None)
    glyph_set[glyph].draw(pen)
    new_glyph = pen.glyph()

    if new_glyph.numberOfContours == 0:
        return new_glyph

    coords = list(new_glyph.coordinates)
    if len(coords) < 3:
        return new_glyph

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    max_y = max(ys)
    min_y = min(ys)

    new_coords = []
    for (x, y) in coords:
        ny = y
        # Move points near the top upward
        if extend_up > 0 and y >= max_y - STEM_THRESHOLD:
            ny = y + extend_up
        # Move points near the bottom downward
        if extend_down > 0 and y <= min_y + STEM_THRESHOLD:
            ny = y - extend_down
        new_coords.append((x, ny))

    new_glyph.coordinates = type(new_glyph.coordinates)(new_coords)
    xs2 = [c[0] for c in new_coords]
    ys2 = [c[1] for c in new_coords]
    new_glyph.xMin = min(xs2)
    new_glyph.yMin = min(ys2)
    new_glyph.xMax = max(xs2)
    new_glyph.yMax = max(ys2)
    return new_glyph

def bold_glyph(glyph, expand):
    """Expand glyph outlines slightly for bold effect"""
    if glyph.numberOfContours == 0:
        return glyph

    coords = list(glyph.coordinates)
    if len(coords) < 3:
        return glyph

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2

    new_coords = []
    for (x, y) in coords:
        dx = x - cx
        dy = y - cy
        dist = (dx*dx + dy*dy) ** 0.5
        if dist > 0:
            scale = (dist + expand) / dist
            new_coords.append((int(cx + dx * scale), int(cy + dy * scale)))
        else:
            new_coords.append((x, y))

    glyph.coordinates = type(glyph.coordinates)(new_coords)
    xs2 = [c[0] for c in new_coords]
    ys2 = [c[1] for c in new_coords]
    glyph.xMin = min(xs2)
    glyph.yMin = min(ys2)
    glyph.xMax = max(xs2)
    glyph.yMax = max(ys2)
    return glyph

def main():
    font = TTFont(SRC)
    glyph_set = font.getGlyphSet()
    glyf = font['glyf']

    # Step 1: Extend vertical stems
    for glyph_name in ASCENDER_GLYPHS | DESCENDER_GLYPHS:
        if glyph_name not in glyf:
            continue
        glyph = glyf[glyph_name]
        if glyph.isComposite():
            continue

        bp = BoundsPen(glyph_set)
        glyph_set[glyph_name].draw(bp)
        old = bp.bounds

        ext_up = EXTEND_UP if glyph_name in ASCENDER_GLYPHS else 0
        ext_down = EXTEND_DOWN if glyph_name in DESCENDER_GLYPHS else 0
        new_glyph = extend_stems(glyph_name, glyf, glyph_set, ext_up, ext_down)
        glyf[glyph_name] = new_glyph

        bp2 = BoundsPen(glyph_set)
        glyph_set[glyph_name].draw(bp2)
        print(f"{glyph_name}: {old} -> {bp2.bounds}")

    # Step 2: Bold all glyphs
    for glyph_name in glyf.keys():
        glyph = glyf[glyph_name]
        if glyph.isComposite() or glyph.numberOfContours == 0:
            continue
        glyf[glyph_name] = bold_glyph(glyph, BOLD_EXPAND)

    # Update metrics
    hhea = font['hhea']
    max_y = max((glyf[g].yMax for g in glyf.keys() if hasattr(glyf[g], 'yMax') and glyf[g].yMax is not None), default=0)
    min_y = min((glyf[g].yMin for g in glyf.keys() if hasattr(glyf[g], 'yMin') and glyf[g].yMin is not None), default=0)
    if max_y > hhea.ascent:
        hhea.ascent = max_y + 100
    if min_y < hhea.descent:
        hhea.descent = min_y - 100
    print(f"hhea: ascent={hhea.ascent}, descent={hhea.descent}")

    font.save(DST)
    font.close()
    print(f"Saved to {DST}")

if __name__ == '__main__':
    main()
