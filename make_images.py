"""ヘッダー画像と記事ごとのアイキャッチ画像を作る（図形と文字だけ。他人の作品は使わない）。

site.json の "images" 設定:
    {"motif": "hearts" | "spice" | "music" | "rings", "bg": "#色", "colors": ["#色", ...],
     "header_image": "assets/header.jpg"}  ← 任意。指定するとヘッダーはその画像を使う
出力: docs/img/header.jpg（1600x480）、docs/img/articles/<slug>.jpg（1200x630）
assets/articles/<slug>.jpg があれば、その記事のアイキャッチは描かずにその画像を使う（幅1200に縮小）
build.py から generate(arts, sitecfg, out_dir) として呼ばれる。
"""
import math, os, random
from PIL import Image, ImageDraw, ImageFont

FONT_B = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
FONT_M = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
FONT_R = "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc"

def font(path, size):
    return ImageFont.truetype(path, size)

# ---------- モチーフ ----------
def heart(d, cx, cy, r, color, width):
    pts = []
    for i in range(80):
        t = 2 * math.pi * i / 80
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * r / 17, cy + y * r / 17))
    d.line(pts + [pts[0]], fill=color, width=width, joint="curve")

def star(d, cx, cy, r, color):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=color)

def note(d, x, y, s, color):
    d.ellipse((x, y, x + s * 1.3, y + s), fill=color)
    d.rectangle((x + s * 1.15, y - s * 2.6, x + s * 1.3, y + s * 0.5), fill=color)
    d.polygon([(x + s * 1.3, y - s * 2.6), (x + s * 2.1, y - s * 1.9), (x + s * 1.3, y - s * 1.8)], fill=color)

def draw_motif(d, motif, colors, box, seed):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    rnd = random.Random(seed)
    if motif == "hearts":
        for i, c in enumerate(colors):
            r = h * (0.30 - i * 0.04)
            heart(d, x0 + w * (0.35 + 0.18 * i), y0 + h * (0.42 + 0.08 * (i % 2)), r, c, 9)
        for _ in range(7):
            star(d, x0 + rnd.random() * w, y0 + rnd.random() * h, rnd.randint(8, 18), rnd.choice(colors))
        # ペンライト
        for i, c in enumerate(colors[:3]):
            bx = x0 + w * (0.12 + 0.07 * i)
            d.rounded_rectangle((bx, y0 + h * 0.55, bx + 16, y0 + h * 0.92), 8, fill=c)
            d.rounded_rectangle((bx - 3, y0 + h * 0.86, bx + 19, y0 + h * 0.98), 4, fill="#3a3d46")
    elif motif == "spice":
        cx, cy = x0 + w * 0.55, y0 + h * 0.6
        R = min(w, h) * 0.36
        d.chord((cx - R, cy - R * 0.9, cx + R, cy + R * 0.9), 0, 180, fill=colors[0])        # 皿
        d.ellipse((cx - R, cy - R * 0.25, cx + R, cy + R * 0.25), fill=colors[1])             # カレー面
        d.ellipse((cx - R * 0.55, cy - R * 0.2, cx + R * 0.05, cy + R * 0.12), fill="#f5f0e6")  # ご飯
        for _ in range(26):                                                                    # スパイスの粒
            a, rr = rnd.random() * 2 * math.pi, R * (1.1 + rnd.random() * 0.5)
            px, py = cx + rr * math.cos(a), cy - abs(rr * math.sin(a)) * 0.9
            s = rnd.randint(4, 10)
            d.ellipse((px - s, py - s, px + s, py + s), fill=rnd.choice(colors))
        for i in range(3):                                                                     # 湯気
            sx = cx - R * 0.3 + i * R * 0.3
            d.arc((sx - 20, cy - R * 1.05, sx + 20, cy - R * 0.65), 90, 270, fill="#ffffff55", width=5)
            d.arc((sx - 20, cy - R * 0.85, sx + 20, cy - R * 0.45), 270, 90, fill="#ffffff55", width=5)
    elif motif == "music":
        mid = y0 + h * 0.55
        for i in range(48):                                                                    # 音の波形
            bx = x0 + i * w / 48
            bh = h * (0.08 + 0.32 * abs(math.sin(i * 0.45 + seed % 7)) * (0.6 + 0.4 * rnd.random()))
            d.rounded_rectangle((bx, mid - bh, bx + w / 48 * 0.55, mid + bh), 4, fill=colors[i % len(colors)])
        for _ in range(4):
            note(d, x0 + rnd.random() * w * 0.85, y0 + h * (0.15 + rnd.random() * 0.15), rnd.randint(18, 28), rnd.choice(colors))
    elif motif == "shapes":
        cx, cy, s = x0 + w * 0.5, y0 + h * 0.5, min(w, h) * 0.28
        d.ellipse((cx - s * 1.3, cy - s * 1.2, cx + s * 0.3, cy + s * 0.4), fill=colors[0])                 # 丸
        d.rounded_rectangle((cx - s * 0.2, cy - s * 0.3, cx + s * 1.2, cy + s * 1.1), 18, fill=colors[2])    # 四角
        d.polygon([(cx - s * 0.9, cy + s * 1.3), (cx - s * 0.1, cy - s * 0.1), (cx + s * 0.7, cy + s * 1.3)],
                  fill=colors[1] + "cc")                                                                    # 三角
        # ペン（斜めの軸とペン先）
        px, py = cx + s * 1.1, cy - s * 1.3
        d.line((px, py, px - s * 0.9, py + s * 0.9), fill=colors[3], width=22)
        d.polygon([(px - s * 0.9 - 14, py + s * 0.9 - 6), (px - s * 0.9 + 6, py + s * 0.9 + 14), (px - s * 1.15, py + s * 1.15)],
                  fill="#f5f0e6")
        for _ in range(8):                                                                                  # きらめき
            star(d, x0 + rnd.random() * w, y0 + rnd.random() * h, rnd.randint(6, 12), rnd.choice(colors))
    else:
        for i, c in enumerate(colors):
            r = h * 0.38
            cx, cy = x0 + w * (0.3 + 0.13 * i), y0 + h * (0.45 + 0.07 * i)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=c, width=10)

# ---------- 文字の折り返し ----------
def wrap(d, text, f, maxw, maxlines):
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=f) > maxw:
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    if len(lines) > maxlines:
        lines = lines[:maxlines]
        lines[-1] = lines[-1][:-1] + "…"
    return lines

def header(sitecfg, path):
    im_cfg = sitecfg["images"]
    if im_cfg.get("header_image"):
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), im_cfg["header_image"])
        im = Image.open(src).convert("RGB")
        if im.width > 1600:
            im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
        im.save(path, quality=88)
        return
    W, H = 1600, 480
    im = Image.new("RGB", (W, H), im_cfg["bg"])
    d = ImageDraw.Draw(im, "RGBA")
    draw_motif(d, im_cfg["motif"], im_cfg["colors"], (860, 30, 1560, 450), 1)
    og = sitecfg["og"]
    d.text((90, 120), og["line1"], font=font(FONT_B, 92), fill="#ffffff")
    d.text((90, 230), og["line2"], font=font(FONT_B, 92), fill=im_cfg["colors"][1])
    d.text((92, 360), og["sub"], font=font(FONT_R, 34), fill="#d4d6dd")
    im.save(path, quality=88)

def eyecatch(sitecfg, art, path):
    im_cfg = sitecfg["images"]
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "articles", art["slug"] + ".jpg")
    if os.path.exists(src):
        im = Image.open(src).convert("RGB")
        if im.width > 1200:
            im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
        im.save(path, quality=86)
        return
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), im_cfg["bg"])
    d = ImageDraw.Draw(im, "RGBA")
    seed = sum(map(ord, art["slug"]))
    draw_motif(d, im_cfg["motif"], im_cfg["colors"], (790, 150, 1180, 600), seed)
    d.rectangle((0, 0, W, H), fill=None)
    cat = art.get("category", "")
    fc = font(FONT_M, 30)
    tw = d.textlength(cat, font=fc)
    d.rounded_rectangle((70, 70, 70 + tw + 44, 122), 26, fill=im_cfg["colors"][0])
    d.text((92, 78), cat, font=fc, fill="#ffffff")
    # 見出しは「｜」の前を大きく、後ろを小さく
    main, _, sub = art["title"].partition("｜")
    ft = font(FONT_B, 60)
    y = 170
    for ln in wrap(d, main, ft, 660, 4):
        d.text((70, y), ln, font=ft, fill="#ffffff"); y += 80
    if sub:
        fs = font(FONT_R, 30)
        for ln in wrap(d, sub, fs, 640, 2):
            d.text((72, y + 12), ln, font=fs, fill="#c9ccd4"); y += 44
    d.text((70, H - 70), sitecfg["og"]["line1"] + sitecfg["og"]["line2"], font=font(FONT_M, 26), fill=im_cfg["colors"][1])
    im.save(path, quality=86)

def generate(arts, sitecfg, out_dir):
    os.makedirs(os.path.join(out_dir, "img", "articles"), exist_ok=True)
    header(sitecfg, os.path.join(out_dir, "img", "header.jpg"))
    for a in arts:
        eyecatch(sitecfg, a, os.path.join(out_dir, "img", "articles", a["slug"] + ".jpg"))
