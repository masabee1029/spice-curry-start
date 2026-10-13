#!/usr/bin/env python3
"""AIデザイン実践ラボ: content/*.md から docs/ に静的サイトを生成する。

記事の書式（content/YYYY-MM-DD-slug.md）:
    ---
    title: 記事タイトル
    description: 120字程度の要約
    category: 基本 / 作り方 / 道具 / 著作権 / 印刷
    ---
    本文（Markdown の簡易版: ## 見出し, - 箇条書き, 1. 番号, **太字**, [文字](URL), | 表 |）
    商品ボタン: [[shop:検索キーワード|表示名]]　宿のボタン: [[travel:地名や会場名|表示名]]
"""
import html, json, os, re, shutil, urllib.parse
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "docs")
SITE = CFG["site_url"].rstrip("/") + "/"
NAME = CFG["site_name"]
SITECFG = json.load(open(os.path.join(ROOT, "site.json"), encoding="utf-8"))

# ---------- アフィリエイトリンク ----------
def amazon_link(q):
    url = "https://www.amazon.co.jp/s?k=" + urllib.parse.quote_plus(q)
    if CFG.get("amazon_tag"):
        url += "&tag=" + CFG["amazon_tag"]
    return url

def rakuten_link(q):
    search = "https://search.rakuten.co.jp/search/mall/" + urllib.parse.quote(q) + "/"
    if CFG.get("rakuten_affiliate_id"):
        return ("https://hb.afl.rakuten.co.jp/hgc/" + CFG["rakuten_affiliate_id"] +
                "/?pc=" + urllib.parse.quote(search, safe=""))
    return search

def travel_link(q):
    dest = "https://kw.travel.rakuten.co.jp/keyword/Search.do?f_keyword=" + urllib.parse.quote(q)
    if CFG.get("rakuten_affiliate_id"):
        return ("https://hb.afl.rakuten.co.jp/hgc/" + CFG["rakuten_affiliate_id"] +
                "/?pc=" + urllib.parse.quote(dest, safe=""))
    return dest

def travel_box(q, label):
    e = html.escape
    return ('<div class="shop"><div class="shop-name">%s</div>'
            '<a class="btn rkt" rel="nofollow sponsored noopener" target="_blank" href="%s">楽天トラベルで宿を探す</a></div>'
            % (e(label), e(travel_link(q))))

def shop_box(q, label):
    e = html.escape
    return ('<div class="shop"><div class="shop-name">%s</div>'
            '<a class="btn amz" rel="nofollow sponsored noopener" target="_blank" href="%s">Amazonで見る</a>'
            '<a class="btn rkt" rel="nofollow sponsored noopener" target="_blank" href="%s">楽天で見る</a></div>'
            % (e(label), e(amazon_link(q)), e(rakuten_link(q))))

# ---------- カテゴリ別のおすすめ（全ページに出すアフィリエイト誘導） ----------
IMAGES = bool(SITECFG.get("images")) and os.path.exists(os.path.join(ROOT, "make_images.py"))
PICKS = {k: [tuple(x) for x in v] for k, v in SITECFG["picks"].items()}
DEFAULT_PICKS = [tuple(x) for x in SITECFG["default_picks"]]

def picks_box(cat, title, compact=False):
    e = html.escape
    items = "".join(
        '<div class="pick"><div><strong>%s</strong><span>%s</span></div>'
        '<a class="btn amz" rel="nofollow sponsored noopener" target="_blank" href="%s">Amazon</a>'
        '<a class="btn rkt" rel="nofollow sponsored noopener" target="_blank" href="%s">楽天</a></div>'
        % (e(label), e(note), e(amazon_link(q)), e(rakuten_link(q)))
        for q, label, note in (PICKS.get(cat, DEFAULT_PICKS)[:2] if compact else PICKS.get(cat, DEFAULT_PICKS)))
    return '<div class="picks"><div class="picks-h">%s</div>%s</div>' % (e(title), items)

# ---------- Markdown（簡易） ----------
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    def link(m):
        url = m.group(2)
        ext = url.startswith("http")
        return '<a href="%s"%s>%s</a>' % (url, ' target="_blank" rel="noopener"' if ext else "", m.group(1))
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, s)

def md(text):
    out, lines, i = [], text.strip("\n").split("\n"), 0
    toc = []
    while i < len(lines):
        ln = lines[i].rstrip()
        m = re.match(r"\[\[(shop|travel):(.+?)\|(.+?)\]\]$", ln.strip())
        if not ln.strip():
            i += 1; continue
        if m:
            out.append((travel_box if m.group(1) == "travel" else shop_box)(m.group(2), m.group(3))); i += 1; continue
        if ln.startswith("## "):
            n = len(toc) + 1
            toc.append(ln[3:])
            out.append('<h2 id="s%d">%s</h2>' % (n, inline(ln[3:]))); i += 1; continue
        if ln.startswith("### "):
            out.append("<h3>%s</h3>" % inline(ln[4:])); i += 1; continue
        if ln.startswith("> "):
            buf = []
            while i < len(lines) and lines[i].startswith("> "):
                buf.append(inline(lines[i][2:])); i += 1
            out.append('<div class="note">%s</div>' % "<br>".join(buf)); continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            h = "<tr>" + "".join("<th>%s</th>" % inline(c) for c in rows[0]) + "</tr>"
            b = "".join("<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>" for r in rows[1:])
            out.append('<div class="tbl"><table>%s%s</table></div>' % (h, b)); continue
        if re.match(r"(- |\d+\. )", ln):
            tag = "ol" if ln[0].isdigit() else "ul"
            items = []
            while i < len(lines) and re.match(r"(- |\d+\. )", lines[i]):
                items.append("<li>%s</li>" % inline(re.sub(r"^(- |\d+\. )", "", lines[i]))); i += 1
            out.append("<%s>%s</%s>" % (tag, "".join(items), tag)); continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(#|- |\d+\. |\||> |\[\[)", lines[i]):
            buf.append(inline(lines[i].strip())); i += 1
        out.append("<p>%s</p>" % "<br>".join(buf))
    return "\n".join(out), toc

def load_articles():
    arts = []
    for fn in sorted(os.listdir(os.path.join(ROOT, "content"))):
        if not fn.endswith(".md"):
            continue
        raw = open(os.path.join(ROOT, "content", fn), encoding="utf-8").read()
        m = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
        meta = dict(l.split(":", 1) for l in m.group(1).split("\n") if ":" in l)
        meta = {k.strip(): v.strip() for k, v in meta.items()}
        d = fn[:10]
        slug = fn[11:-3]
        body, toc = md(m.group(2))
        arts.append(dict(meta, date=d, slug=slug, body=body, toc=toc, url="articles/%s.html" % slug))
    arts.sort(key=lambda a: a["date"], reverse=True)
    return arts

# ---------- レイアウト ----------
CSS = """
:root{--bg:#fbfaf7;--fg:#1f2328;--muted:#5b636e;--line:#e6e2da;--card:#fff;--accent:ACCENT_L;--accent2:ACCENT2_L}
@media (prefers-color-scheme:dark){:root{--bg:#15161a;--fg:#e9e9ee;--muted:#a3a8b3;--line:#2c2f37;--card:#1d1f25;--accent:ACCENT_D;--accent2:ACCENT2_D}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.9 "Hiragino Sans","Noto Sans JP",sans-serif}
a{color:var(--accent)}header{border-bottom:1px solid var(--line);background:var(--card)}
.wrap{max-width:820px;margin:0 auto;padding:0 16px}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 0;flex-wrap:wrap}
.logo{font-weight:800;font-size:20px;text-decoration:none;color:var(--fg)}.logo span{color:var(--accent)}
nav a{margin-left:14px;font-size:14px;color:var(--muted);text-decoration:none}nav a:first-child{margin-left:0}
.pr{font-size:12px;color:var(--muted);padding:6px 0;border-bottom:1px dashed var(--line)}
.hero{padding:40px 0 24px}.hero h1{font-size:28px;line-height:1.4;margin:0 0 8px}.hero p{color:var(--muted);margin:0}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;padding:16px 0 40px}
.thumb{display:block;width:calc(100% + 32px);margin:-16px -16px 12px;aspect-ratio:1200/630;object-fit:cover;border-radius:12px 12px 0 0}
.hero-img{display:block;width:100%;height:auto;border-radius:14px;margin-top:20px}
.eyecatch{display:block;width:100%;height:auto;border-radius:12px;margin:8px 0 20px}
.card{overflow:hidden;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;text-decoration:none;color:var(--fg);display:block}
.card:hover{border-color:var(--accent)}.card h2{font-size:17px;line-height:1.5;margin:6px 0}.card p{font-size:13px;color:var(--muted);margin:0}
.tag{display:inline-block;font-size:12px;padding:1px 10px;border-radius:99px;background:var(--accent);color:#fff}
.date{font-size:12px;color:var(--muted);margin-left:8px}
article{padding:28px 0 40px}article h1{font-size:26px;line-height:1.45}
article h2{font-size:21px;border-left:5px solid var(--accent);padding-left:10px;margin-top:40px}
article h3{font-size:18px;margin-top:28px}
.toc{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 20px;font-size:14px}
.note{background:var(--card);border-left:4px solid var(--accent2);padding:10px 14px;border-radius:6px;margin:16px 0}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid var(--line);padding:6px 10px;text-align:left}th{background:var(--card)}
code{background:var(--card);border:1px solid var(--line);border-radius:4px;padding:0 4px;font-size:14px}
.shop{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin:18px 0;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.shop-name{flex:1 1 100%;font-weight:700}
.btn{display:inline-block;padding:8px 18px;border-radius:8px;color:#fff;text-decoration:none;font-size:14px;font-weight:700}
.amz{background:#e88a00}.rkt{background:#bf0000}
.picks{background:var(--card);border:2px solid var(--accent);border-radius:12px;padding:14px 16px;margin:24px 0}
.picks-h{font-weight:800;margin-bottom:6px}
.pick{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:8px 0;border-top:1px solid var(--line)}
.pick div{flex:1 1 220px}.pick span{display:block;font-size:13px;color:var(--muted)}
.related{border-top:1px solid var(--line);padding-top:16px}
footer{border-top:1px solid var(--line);padding:20px 0 40px;font-size:13px;color:var(--muted)}footer a{color:var(--muted);margin-right:14px}
"""

for _k, _v in SITECFG["colors"].items():
    CSS = CSS.replace(_k, _v)

GA_ID = (CFG.get("ga_measurement_id") or "").strip()
GA = ("""<script async src="https://www.googletagmanager.com/gtag/js?id=%s"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','%s');</script>""" % (GA_ID, GA_ID)) if GA_ID else ""

def page(title, desc, body, path, depth=0, og_image="og.png"):
    up = "../" * depth
    e = html.escape
    full = title if title == NAME else "%s｜%s" % (title, NAME)
    html_out = """<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title><meta name="description" content="%s">
<link rel="canonical" href="%s"><meta property="og:title" content="%s"><meta property="og:description" content="%s">
<meta property="og:type" content="website"><meta property="og:url" content="%s"><meta property="og:image" content="%sOGIMG">
<meta name="twitter:card" content="summary_large_image">
<style>%s</style>%s</head><body>
<header><div class="wrap"><div class="top"><a class="logo" href="%sindex.html">LOGO_HTML</a>
<nav><a href="%sindex.html">記事一覧</a><a href="%sabout.html">このサイトについて</a></nav></div>
<div class="pr">※本ページはプロモーション（広告）を含みます。商品リンクから購入されると運営者に紹介料が入ることがあります。</div></div></header>
<main class="wrap">%s</main>
<footer><div class="wrap"><a href="%sabout.html">このサイトについて</a><a href="%sprivacy.html">プライバシーポリシー</a>%s
<div>© %d %s</div></div></footer></body></html>""" % (
        e(full), e(desc), SITE + path, e(full), e(desc), SITE + path, SITE, CSS, GA,
        up, up, up, body, up, up,
        ('<a href="%s" target="_blank" rel="noopener">お問い合わせ</a>' % e(CFG["contact_url"])) if CFG.get("contact_url") else "",
        date.today().year, NAME)
    return html_out.replace("OGIMG", og_image)

def card(a, up=""):
    e = html.escape
    thumb = ('<img class="thumb" loading="lazy" src="%simg/articles/%s.jpg" alt="">' % (up, a["slug"])) if IMAGES else ""
    return ('<a class="card" href="%s%s">%s<span class="tag">%s</span><span class="date">%s</span>'
            '<h2>%s</h2><p>%s</p></a>' % (up, a["url"], thumb, e(a.get("category", "")), a["date"], e(a["title"]), e(a["description"])))

def write(path, s):
    p = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(s.replace("LOGO_HTML", SITECFG["logo_html"]))

def build():
    arts = load_articles()
    if os.path.isdir(os.path.join(OUT, "articles")):
        shutil.rmtree(os.path.join(OUT, "articles"))
    if IMAGES:
        import make_images
        make_images.generate(arts, SITECFG, OUT)
    hero = '<div class="hero"><h1>%s</h1><p>%s</p></div>' % (SITECFG["hero_title"], SITECFG["hero_text"])
    if IMAGES:
        hero = '<img class="hero-img" src="img/header.jpg" alt="%s">' % html.escape(NAME) + hero
    write("index.html", page(NAME, SITECFG["home_description"],
                             hero + picks_box("", SITECFG["home_picks_title"]) +
                             '<div class="cards">' + "".join(card(a) for a in arts) + "</div>", "index.html"))
    for a in arts:
        e = html.escape
        toc = ('<div class="toc"><strong>目次</strong><ol>%s</ol></div>' %
               "".join('<li><a href="#s%d">%s</a></li>' % (n + 1, inline(t)) for n, t in enumerate(a["toc"]))) if a["toc"] else ""
        others = [o for o in arts if o is not a and o.get("category") == a.get("category")][:3] or [o for o in arts if o is not a][:3]
        rel = '<div class="related"><strong>関連記事</strong><div class="cards">%s</div></div>' % "".join(card(o, "../") for o in others)
        cat = a.get("category", "")
        art = a["body"]
        # 導入文のあと（最初の見出しの前）に短い誘導、まとめの前に全部入りの誘導
        k = art.find("<h2")
        if k > 0:
            art = art[:k] + picks_box(cat, SITECFG["picks_title_short"], compact=True) + art[k:]
        k = art.rfind('<h2 id="s%d">' % len(a["toc"])) if a["toc"] else -1
        if k > 0:
            art = art[:k] + picks_box(cat, SITECFG["picks_title_long"]) + art[k:]
        else:
            art += picks_box(cat, SITECFG["picks_title_long"])
        body = ('<article><span class="tag">%s</span><span class="date">%s</span><h1>%s</h1>%s%s%s</article>%s'
                % (e(cat), a["date"], e(a["title"]),
                   ('<img class="eyecatch" src="../img/articles/%s.jpg" alt="">' % a["slug"]) if IMAGES else "",
                   toc, art, rel))
        write(a["url"], page(a["title"], a["description"], body, a["url"], 1,
                             ("img/articles/%s.jpg" % a["slug"]) if IMAGES else "og.png"))
    about = ('<article><h1>このサイトについて</h1>' + SITECFG["about_html"] +
             '<h2>広告について</h2><p>当サイトは Amazonアソシエイト・楽天アフィリエイトに参加しており、紹介した商品の購入により運営者が紹介料を受け取ることがあります。Amazonのアソシエイトとして、当サイトは適格販売により収入を得ています。</p></article>'
             + picks_box("", SITECFG["home_picks_title"]))
    write("about.html", page("このサイトについて", NAME + "の運営方針と広告について。", about, "about.html"))
    privacy = """<article><h1>プライバシーポリシー</h1>
<h2>アクセス解析</h2><p>当サイトは Google アナリティクスを利用しています。Cookie を使ってアクセス情報を収集しますが、個人を特定する情報は含みません。Cookie はブラウザの設定で無効にできます。</p>
<h2>広告</h2><p>当サイトは Amazonアソシエイト・楽天アフィリエイトを利用しています。これらのサービスは Cookie を使用することがあります。</p>
<h2>免責事項</h2><p>掲載内容の正確性には注意していますが、内容を保証するものではありません。当サイトの情報によって生じた損害について責任を負いかねます。</p></article>"""
    write("privacy.html", page("プライバシーポリシー", NAME + "のプライバシーポリシーと免責事項。", privacy, "privacy.html"))
    urls = ["index.html", "about.html", "privacy.html"] + [a["url"] for a in arts]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join("<url><loc>%s%s</loc></url>\n" % (SITE, u) for u in urls) + "</urlset>\n")
    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n" % SITE)
    write(".nojekyll", "")
    print("built %d articles" % len(arts))

if __name__ == "__main__":
    build()
