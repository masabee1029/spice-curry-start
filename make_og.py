"""SNS共有用の画像 docs/og.png（1200x630）を site.json の og 設定から作る。作品画像は使わず図形と文字だけ。
og.style（neon / riso / citypop / notebook / frame）があるサイトは、ヘッダー画像（images.header_image）をサイトの見た目に合わせた枠で囲み、
下に og.card_sub（無ければ og.sub）を置く（2026-10-27 本人「OGP画像もサイトごとに変えて」）。"""
import json, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(ROOT, "site.json"), encoding="utf-8"))
og = cfg["og"]
W, H = 1200, 630
GOTHIC = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
MARU = "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc"


def rings():
    im = Image.new("RGB", (W, H), "#15161a")
    d = ImageDraw.Draw(im)
    for i, c in enumerate(og["rings"]):
        d.ellipse((760 + i * 70, 120 + i * 60, 1060 + i * 70, 420 + i * 60), outline=c, width=10)
    f1, f2 = ImageFont.truetype(GOTHIC, 92), ImageFont.truetype(GOTHIC.replace("W8", "W4"), 36)
    d.text((80, 200), og["line1"], font=f1, fill="#ffffff")
    d.text((80, 310), og["line2"], font=f1, fill=og["rings"][1])
    d.text((80, 450), og["sub"], font=f2, fill="#c9ccd4")
    return im


def round_mask(size, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=255)
    return m


def glow(im, draw_fn, color, blur):
    """draw_fn(ImageDraw) で描いた形を、ぼかした光として im に重ねる"""
    m = Image.new("L", (W, H), 0)
    draw_fn(ImageDraw.Draw(m))
    m = m.filter(ImageFilter.GaussianBlur(blur))
    im.paste(Image.new("RGB", (W, H), color), (0, 0), m)


def styled(style):
    hdr = Image.open(os.path.join(ROOT, cfg["images"]["header_image"])).convert("RGB")
    iw = 1080
    hdr = hdr.resize((iw, round(hdr.height * iw / hdr.width)), Image.LANCZOS)
    if hdr.height > H - 132:  # 縦に長いヘッダーは、下の文字が入る高さまで縮める
        hdr = hdr.resize((round(hdr.width * (H - 132) / hdr.height), H - 132), Image.LANCZOS)
    iw, ih = hdr.size
    x, y = (W - iw) // 2, (H - ih - 92) // 2
    ty = y + ih + 30  # 下の文字の上端
    sub = og.get("card_sub", og["sub"])
    if style == "neon":  # ネオンのライブ会場
        im = Image.new("RGB", (W, H), "#130c25")
        glow(im, lambda d: d.ellipse((200, -380, 1000, 260), fill=255), "#3b1a6e", 60)
        glow(im, lambda d: d.rounded_rectangle((x - 4, y - 4, x + iw + 4, y + ih + 4), 22, outline=255, width=12), "#ff4fc4", 14)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((x - 3, y - 3, x + iw + 3, y + ih + 3), 20, outline="#ffb3ea", width=3)
        im.paste(hdr, (x, y), round_mask(hdr.size, 18))
        f = ImageFont.truetype(MARU, 44)
        tx = (W - d.textlength(sub, font=f)) / 2
        glow(im, lambda d: d.text((tx, ty), sub, font=f, fill=255), "#ff4fc4", 8)
        ImageDraw.Draw(im).text((tx, ty), sub, font=f, fill="#ffffff")
    elif style == "riso":  # 版画風の紙
        im = Image.new("RGB", (W, H), "#f6eedb")
        d = ImageDraw.Draw(im)
        for yy in range(0, H, 6):
            for xx in range(0, W, 6):
                d.point((xx, yy), fill="#e3d7bd")
        d.rectangle((x + 12, y + 12, x + iw + 12, y + ih + 12), fill="#b8321c")
        im.paste(hdr, (x, y))
        d.rectangle((x - 2, y - 2, x + iw + 2, y + ih + 2), outline="#3a2416", width=5)
        f = ImageFont.truetype(GOTHIC, 40)
        tw = d.textlength(sub, font=f)
        bx = (W - tw) / 2
        d.rectangle((bx - 24 + 6, ty - 6 + 6, bx + tw + 24 + 6, ty + 56 + 6), fill="#3a2416")
        d.rectangle((bx - 24, ty - 6, bx + tw + 24, ty + 56), fill="#d4920f", outline="#3a2416", width=4)
        d.text((bx, ty + 2), sub, font=f, fill="#3a2416")
    elif style == "citypop":  # 80 年代シティポップの夕暮れ
        im = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(im)
        for yy in range(H):
            t = yy / H
            d.line((0, yy, W, yy), fill=tuple(round(a + (b - a) * t) for a, b in ((0x2b, 0x17), (0x1f, 0x14), (0x5c, 0x3a))))
        im.paste(hdr, (x, y), round_mask(hdr.size, 8))
        for i, c in enumerate(("#ffb15c", "#ff7eb6", "#8e6bff")):
            d.rectangle((x, y + ih + 10 + i * 8, x + iw, y + ih + 14 + i * 8), fill=c)
        f = ImageFont.truetype(GOTHIC, 40)
        d.text(((W - d.textlength(sub, font=f)) / 2, ty + 20), sub, font=f, fill="#ffffff")
    elif style == "notebook":  # 白地の方眼ノート
        im = Image.new("RGB", (W, H), "#ffffff")
        d = ImageDraw.Draw(im)
        for v in range(0, W, 24):
            d.line((v, 0, v, H), fill="#e8ecfa")
        for v in range(0, H, 24):
            d.line((0, v, W, v), fill="#e8ecfa")
        d.rounded_rectangle((x + 10, y + 10, x + iw + 10, y + ih + 10), 16, fill="#ffe34d")
        im.paste(hdr, (x, y), round_mask(hdr.size, 14))
        d.rounded_rectangle((x - 2, y - 2, x + iw + 2, y + ih + 2), 16, outline="#14215a", width=4)
        f = ImageFont.truetype(GOTHIC, 40)
        tw = d.textlength(sub, font=f)
        bx = (W - tw) / 2
        d.rectangle((bx - 6, ty + 30, bx + tw + 6, ty + 52), fill="#ffe34d")
        d.text((bx, ty + 4), sub, font=f, fill="#14215a")
    elif style == "frame":  # 決まった見た目のないサイト: images.bg の地にアクセント色の枠
        col = cfg["colors"]
        im = Image.new("RGB", (W, H), cfg["images"].get("bg", "#15161a"))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((x - 5, y - 5, x + iw + 5, y + ih + 5), 16, fill=col["ACCENT_D"])
        im.paste(hdr, (x, y), round_mask(hdr.size, 12))
        f = ImageFont.truetype(GOTHIC, 40)
        tw = d.textlength(sub, font=f)
        d.text(((W - tw) / 2, ty), sub, font=f, fill="#ffffff")
        d.rectangle(((W - tw) / 2, ty + 56, (W + tw) / 2, ty + 61), fill=col["ACCENT2_D"])
    else:
        return rings()
    return im


im = styled(og["style"]) if og.get("style") and cfg.get("images", {}).get("header_image") else rings()
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
im.save(os.path.join(ROOT, "docs", "og.png"))
