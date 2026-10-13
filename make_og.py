"""SNS共有用の画像 docs/og.png（1200x630）を site.json の og 設定から作る。作品画像は使わず図形と文字だけ。"""
import json, os
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.abspath(__file__))
og = json.load(open(os.path.join(ROOT, "site.json"), encoding="utf-8"))["og"]
W, H = 1200, 630
im = Image.new("RGB", (W, H), "#15161a")
d = ImageDraw.Draw(im)
for i, c in enumerate(og["rings"]):
    d.ellipse((760 + i * 70, 120 + i * 60, 1060 + i * 70, 420 + i * 60), outline=c, width=10)
font = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
f1, f2 = ImageFont.truetype(font, 92), ImageFont.truetype(font.replace("W8", "W4"), 36)
d.text((80, 200), og["line1"], font=f1, fill="#ffffff")
d.text((80, 310), og["line2"], font=f1, fill=og["rings"][1])
d.text((80, 450), og["sub"], font=f2, fill="#c9ccd4")
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
im.save(os.path.join(ROOT, "docs", "og.png"))
