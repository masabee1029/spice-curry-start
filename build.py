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

site.json の任意項目: featured（「はじめての方へ」に出す記事の slug の並び）、profile_name /
profile_html（サイドバーと著者ボックス。無ければ about_html の2段落目）、category_slugs（{"カテゴリ名": "url用の英字"}）
"""
import hashlib, html, json, os, re, shutil, urllib.parse
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
# 収益化できている個人ブログ（SWELL / AFFINGER 系）でよく使われる作りに寄せている:
# カテゴリのグローバルナビ、PCは2カラム（サイドバーに運営者・おすすめ商品・人気記事）、
# パンくず、記事冒頭の小さな「PR」表記、著者ボックス、シェアボタン、カテゴリ別一覧ページ、
# 構造化データ（Article / BreadcrumbList）。広告表記の全文はフッター。
CSS = """
:root{--bg:#fbfaf7;--fg:#1f2328;--muted:#5b636e;--line:#e6e2da;--card:#fff;--soft:#f3f1ec;--accent:ACCENT_L;--accent2:ACCENT2_L}
@media (prefers-color-scheme:dark){:root{--bg:#15161a;--fg:#e9e9ee;--muted:#a3a8b3;--line:#2c2f37;--card:#1d1f25;--soft:#23252c;--accent:ACCENT_D;--accent2:ACCENT2_D}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.9 "Hiragino Sans","Noto Sans JP",sans-serif}
img{max-width:100%}a{color:var(--accent)}
header{border-bottom:1px solid var(--line);background:var(--card)}
.wrap{max-width:1140px;margin:0 auto;padding:0 16px}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 0 8px;flex-wrap:wrap}
.logo{font-weight:800;font-size:22px;text-decoration:none;color:var(--fg)}.logo span{color:var(--accent)}
.tagline{font-size:12px;color:var(--muted)}
.gnav{display:flex;gap:4px;overflow-x:auto;padding:4px 0 10px;scrollbar-width:none}.gnav::-webkit-scrollbar{display:none}
.gnav a{flex:0 0 auto;font-size:14px;font-weight:700;color:var(--fg);text-decoration:none;padding:6px 14px;border-radius:99px;background:var(--soft)}
.gnav a:hover,.gnav a.on{background:var(--accent);color:#fff}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:40px;padding:24px 0 48px}
@media (max-width:900px){.layout{grid-template-columns:minmax(0,1fr);gap:8px}}
.hero{padding:20px 0 8px}.hero h1{font-size:28px;line-height:1.4;margin:0 0 10px}.hero p{color:var(--muted);margin:0;font-size:15px}
.hero-img{display:block;width:100%;height:auto;border-radius:14px}
.sec-h{font-size:20px;margin:40px 0 4px;padding-bottom:8px;border-bottom:3px solid var(--accent);display:flex;justify-content:space-between;align-items:baseline}
.sec-h a{font-size:13px;font-weight:400}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px;padding:16px 0}
.thumb{display:block;width:calc(100% + 32px);margin:-16px -16px 12px;aspect-ratio:1200/630;object-fit:cover;border-radius:12px 12px 0 0}
.card{overflow:hidden;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;text-decoration:none;color:var(--fg);display:block;transition:transform .15s}
.card:hover{border-color:var(--accent);transform:translateY(-2px)}.card h2,.card h3{font-size:16px;line-height:1.5;margin:6px 0}.card p{font-size:13px;color:var(--muted);margin:0}
.tag{display:inline-block;font-size:12px;padding:1px 10px;border-radius:99px;background:var(--accent);color:#fff;text-decoration:none}
.prtag{display:inline-block;font-size:11px;padding:0 8px;border:1px solid var(--muted);border-radius:4px;color:var(--muted);margin-left:8px;vertical-align:1px}
.date{font-size:12px;color:var(--muted);margin-left:8px}
.crumb{font-size:12px;color:var(--muted);margin-bottom:10px}.crumb a{color:var(--muted)}
article h1{font-size:26px;line-height:1.45;margin:10px 0}
article h2{font-size:21px;background:var(--soft);border-left:6px solid var(--accent);padding:10px 14px;border-radius:4px;margin-top:44px}
article h3{font-size:18px;margin-top:28px;border-bottom:2px solid var(--line);padding-bottom:4px}
.eyecatch{display:block;width:100%;height:auto;border-radius:12px;margin:8px 0 16px}
.lead{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;font-size:14px;margin:16px 0}
.lead strong{display:block;color:var(--accent)}
.toc{background:var(--card);border:1px solid var(--line);border-top:4px solid var(--accent);border-radius:10px;padding:12px 20px;font-size:14px;margin:20px 0}
.note{background:var(--card);border-left:4px solid var(--accent2);padding:10px 14px;border-radius:6px;margin:16px 0}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid var(--line);padding:6px 10px;text-align:left}th{background:var(--soft)}
code{background:var(--card);border:1px solid var(--line);border-radius:4px;padding:0 4px;font-size:14px}
.shop{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin:18px 0;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.shop-name{flex:1 1 100%;font-weight:700}
.btn{display:inline-block;padding:8px 18px;border-radius:8px;color:#fff;text-decoration:none;font-size:14px;font-weight:700;box-shadow:0 2px 0 rgba(0,0,0,.18)}
.btn:hover{opacity:.88}.amz{background:#e88a00}.rkt{background:#bf0000}
.picks{background:var(--card);border:2px solid var(--accent);border-radius:12px;padding:14px 16px;margin:24px 0}
.picks-h{font-weight:800;margin-bottom:6px}
.pick{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:8px 0;border-top:1px solid var(--line)}
.pick div{flex:1 1 200px}.pick span{display:block;font-size:13px;color:var(--muted)}
.share{display:flex;gap:8px;flex-wrap:wrap;margin:28px 0 8px}.share a{flex:1 1 90px;text-align:center;padding:8px;border-radius:8px;color:#fff;text-decoration:none;font-size:13px;font-weight:700}
.sx{background:#111}.sl{background:#06c755}.sh{background:#00a4de}
.author{display:flex;gap:14px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:24px 0;font-size:14px}
.avatar{flex:0 0 56px;height:56px;border-radius:50%;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:22px}
.author p{margin:4px 0 0;color:var(--muted)}
.related{margin-top:24px}
aside .box{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:20px;font-size:14px}
aside .box-h{font-weight:800;font-size:15px;margin:-4px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--accent)}
aside .sticky{position:sticky;top:16px}
aside .picks{margin:0 0 20px}
.mini{display:flex;gap:10px;align-items:center;text-decoration:none;color:var(--fg);padding:8px 0;border-top:1px solid var(--line);line-height:1.5}
.mini:first-of-type{border-top:0}.mini img{flex:0 0 96px;width:96px;aspect-ratio:1200/630;object-fit:cover;border-radius:6px}
.mini b{display:inline-block;flex:0 0 22px;height:22px;border-radius:50%;background:var(--accent2);color:#fff;font-size:12px;text-align:center;line-height:22px}
.catlist a{display:flex;justify-content:space-between;text-decoration:none;color:var(--fg);padding:6px 0;border-top:1px solid var(--line)}.catlist a:first-of-type{border-top:0}
.catlist small{color:var(--muted)}
footer{border-top:1px solid var(--line);background:var(--card);padding:24px 0 40px;font-size:13px;color:var(--muted)}
footer a{color:var(--muted);margin-right:14px}.fcats{margin-bottom:10px}
.prnote{border-top:1px dashed var(--line);margin-top:14px;padding-top:12px}
"""

for _k, _v in SITECFG["colors"].items():
    CSS = CSS.replace(_k, _v)

GA_ID = (CFG.get("ga_measurement_id") or "").strip()
GA = ("""<script async src="https://www.googletagmanager.com/gtag/js?id=%s"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','%s');</script>""" % (GA_ID, GA_ID)) if GA_ID else ""

PR_TEXT = "※本サイトはプロモーション（広告）を含みます。商品リンクから購入されると運営者に紹介料が入ることがあります。"
CATS = []          # build() で埋める: [(カテゴリ名, 記事数)]
SIDEBAR = ""       # build() で埋める（各ページ共通）

def cat_slug(c):
    return (SITECFG.get("category_slugs") or {}).get(c) or "c" + hashlib.md5(c.encode()).hexdigest()[:6]

def page(title, desc, body, path, depth=0, og_image="og.png", ld="", cat_on="", sidebar=True):
    up = "../" * depth
    e = html.escape
    full = title if title == NAME else "%s｜%s" % (title, NAME)
    gnav = '<a href="%sindex.html"%s>ホーム</a>' % (up, ' class="on"' if path == "index.html" else "") + "".join(
        '<a href="%scategory/%s.html"%s>%s</a>' % (up, cat_slug(c), ' class="on"' if c == cat_on else "", e(c)) for c, _ in CATS)
    main = ('<div class="layout"><main>%s</main><aside>%s</aside></div>' % (body, SIDEBAR.replace("UP/", up))) if sidebar \
        else '<div class="layout" style="grid-template-columns:minmax(0,1fr)"><main>%s</main></div>' % body
    html_out = """<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title><meta name="description" content="%s">
<link rel="canonical" href="%s"><meta property="og:title" content="%s"><meta property="og:description" content="%s">
<meta property="og:type" content="website"><meta property="og:url" content="%s"><meta property="og:image" content="%sOGIMG">
<meta name="twitter:card" content="summary_large_image">
<style>%s</style>%s%s</head><body>
<header><div class="wrap"><div class="top"><a class="logo" href="%sindex.html">LOGO_HTML</a><span class="tagline">%s</span></div>
<nav class="gnav">%s</nav></div></header>
<div class="wrap">%s</div>
<footer><div class="wrap"><div class="fcats">%s</div><a href="%sabout.html">このサイトについて</a><a href="%sprivacy.html">プライバシーポリシー</a>%s
<div class="prnote">%s</div><div>© %d %s</div></div></footer></body></html>""" % (
        e(full), e(desc), SITE + path, e(full), e(desc), SITE + path, SITE, CSS, GA, ld,
        up, e(SITECFG.get("og", {}).get("sub", "")), gnav, main,
        "".join('<a href="%scategory/%s.html">%s</a>' % (up, cat_slug(c), e(c)) for c, _ in CATS),
        up, up,
        ('<a href="%s" target="_blank" rel="noopener">お問い合わせ</a>' % e(CFG["contact_url"])) if CFG.get("contact_url") else "",
        PR_TEXT, date.today().year, NAME)
    return html_out.replace("OGIMG", og_image)

def card(a, up="", h="h2"):
    e = html.escape
    thumb = ('<img class="thumb" loading="lazy" src="%simg/articles/%s.jpg" alt="">' % (up, a["slug"])) if IMAGES else ""
    return ('<a class="card" href="%s%s">%s<span class="tag">%s</span><span class="date">%s</span>'
            '<%s>%s</%s><p>%s</p></a>' % (up, a["url"], thumb, e(a.get("category", "")), a["date"], h, e(a["title"]), h, e(a["description"])))

def mini(a, n=0):
    e = html.escape
    img = ('<img loading="lazy" src="UP/img/articles/%s.jpg" alt="">' % a["slug"]) if IMAGES else ("<b>%d</b>" % n if n else "")
    return '<a class="mini" href="UP/%s">%s<span>%s</span></a>' % (a["url"], img, e(a["title"]))

def profile_html():
    if SITECFG.get("profile_html"):
        return SITECFG["profile_html"]
    m = re.findall(r"<p>(.*?)</p>", SITECFG["about_html"], re.S)
    return m[1] if len(m) > 1 else (m[0] if m else "")

def author_box(up):
    name = SITECFG.get("profile_name", "運営者")
    return ('<div class="author"><div class="avatar">%s</div><div><strong>この記事を書いた人：%s</strong><p>%s</p>'
            '<p><a href="%sabout.html">運営者について詳しく</a></p></div></div>' % (html.escape(name[:1]), html.escape(name), profile_html(), up))

def share(url, title):
    q = urllib.parse.quote
    return ('<div class="share"><a class="sx" rel="noopener" target="_blank" href="https://twitter.com/intent/tweet?url=%s&text=%s">Xでシェア</a>'
            '<a class="sl" rel="noopener" target="_blank" href="https://social-plugins.line.me/lineit/share?url=%s">LINEで送る</a>'
            '<a class="sh" rel="noopener" target="_blank" href="https://b.hatena.ne.jp/entry/panel/?url=%s">はてブ</a></div>'
            % (q(url, safe=""), q(title), q(url, safe=""), q(url, safe="")))

def jsonld(obj):
    return '<script type="application/ld+json">%s</script>' % json.dumps(obj, ensure_ascii=False)

def crumbs(items):
    """items: [(名前, 相対URL or None)]"""
    e = html.escape
    vis = " ＞ ".join(('<a href="%s">%s</a>' % (u, e(n))) if u else e(n) for n, u in items)
    return '<div class="crumb">%s</div>' % vis

def crumbs_ld(items):
    return jsonld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (n, u) in enumerate(items)]})

def write(path, s):
    p = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(s.replace("LOGO_HTML", SITECFG["logo_html"]))

def build():
    global CATS, SIDEBAR
    e = html.escape
    arts = load_articles()
    for d in ("articles", "category"):
        if os.path.isdir(os.path.join(OUT, d)):
            shutil.rmtree(os.path.join(OUT, d))
    if IMAGES:
        import make_images
        make_images.generate(arts, SITECFG, OUT)
    order = []
    for a in arts:
        if a.get("category") and a["category"] not in order:
            order.append(a["category"])
    pref = list(SITECFG.get("picks", {}).keys())
    order.sort(key=lambda c: pref.index(c) if c in pref else len(pref))
    CATS = [(c, sum(1 for a in arts if a.get("category") == c)) for c in order]
    by_slug = {a["slug"]: a for a in arts}
    featured = [by_slug[s] for s in SITECFG.get("featured", []) if s in by_slug] or arts[:5]

    # サイドバー（UP/ はページの深さに合わせて置き換える）
    SIDEBAR = ('<div class="box"><div class="box-h">運営者</div>%s<p style="margin:8px 0 0"><a href="UP/about.html">プロフィールを見る</a></p></div>'
               % profile_html()) + \
        '<div class="box"><div class="box-h">はじめての方におすすめ</div>%s</div>' % "".join(mini(a, n + 1) for n, a in enumerate(featured)) + \
        '<div class="box catlist"><div class="box-h">カテゴリ</div>%s</div>' % "".join(
            '<a href="UP/category/%s.html">%s<small>%d記事</small></a>' % (cat_slug(c), e(c), n) for c, n in CATS) + \
        '<div class="sticky">%s</div>' % picks_box("", SITECFG["home_picks_title"])

    # トップページ
    hero = '<div class="hero"><h1>%s</h1><p>%s</p></div>' % (SITECFG["hero_title"], SITECFG["hero_text"])
    if IMAGES:
        hero = '<img class="hero-img" src="img/header.jpg" alt="%s">' % e(NAME) + hero
    home = hero + '<h2 class="sec-h">はじめての方へ：まず読みたい記事</h2><div class="cards">%s</div>' % "".join(card(a, "", "h3") for a in featured)
    home += picks_box("", SITECFG["home_picks_title"])
    home += '<h2 class="sec-h">新着記事</h2><div class="cards">%s</div>' % "".join(card(a, "", "h3") for a in arts[:6])
    for c, n in CATS:
        items = [a for a in arts if a.get("category") == c]
        home += ('<h2 class="sec-h">%s<a href="category/%s.html">%sの記事をすべて見る（%d）</a></h2><div class="cards">%s</div>'
                 % (e(c), cat_slug(c), e(c), n, "".join(card(a, "", "h3") for a in items[:3])))
    home_ld = jsonld({"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE})
    write("index.html", page(NAME, SITECFG["home_description"], home, "index.html", ld=home_ld))

    # カテゴリページ
    for c, n in CATS:
        items = [a for a in arts if a.get("category") == c]
        url = "category/%s.html" % cat_slug(c)
        body = (crumbs([("ホーム", "../index.html"), (c, None)]) +
                '<h1 class="sec-h" style="margin-top:0">%s の記事一覧（%d件）</h1>' % (e(c), n) +
                '<div class="cards">%s</div>' % "".join(card(a, "../") for a in items) +
                picks_box(c, SITECFG["picks_title_long"]))
        write(url, page("%sの記事一覧" % c, "%s「%s」カテゴリの記事一覧。" % (NAME, c), body, url, 1,
                        ld=crumbs_ld([("ホーム", "index.html"), (c, url)]), cat_on=c))

    # 記事ページ
    for a in arts:
        toc = ('<div class="toc"><strong>目次</strong><ol>%s</ol></div>' %
               "".join('<li><a href="#s%d">%s</a></li>' % (n + 1, inline(t)) for n, t in enumerate(a["toc"]))) if a["toc"] else ""
        others = [o for o in arts if o is not a and o.get("category") == a.get("category")][:4]
        others += [o for o in arts if o is not a and o not in others][:4 - len(others)]
        rel = '<div class="related"><h2 class="sec-h">あわせて読みたい</h2><div class="cards">%s</div></div>' % "".join(card(o, "../", "h3") for o in others)
        cat = a.get("category", "")
        art = a["body"]
        # 導入文のあと（最初の見出しの前）に目次と短い誘導、まとめの前に全部入りの誘導
        k = art.find("<h2")
        if k > 0:
            art = art[:k] + toc + picks_box(cat, SITECFG["picks_title_short"], compact=True) + art[k:]
        else:
            art = toc + art
        k = art.rfind('<h2 id="s%d">' % len(a["toc"])) if a["toc"] else -1
        if k > 0:
            art = art[:k] + picks_box(cat, SITECFG["picks_title_long"]) + art[k:]
        else:
            art += picks_box(cat, SITECFG["picks_title_long"])
        cu = "category/%s.html" % cat_slug(cat)
        body = ('%s<article><a class="tag" href="../%s">%s</a><span class="prtag">PR</span><span class="date">%s</span><h1>%s</h1>%s'
                '<div class="lead"><strong>この記事でわかること</strong>%s</div>%s</article>%s%s%s'
                % (crumbs([("ホーム", "../index.html"), (cat, "../" + cu), (a["title"], None)]),
                   cu, e(cat), a["date"], e(a["title"]),
                   ('<img class="eyecatch" src="../img/articles/%s.jpg" alt="">' % a["slug"]) if IMAGES else "",
                   e(a["description"]), art, share(SITE + a["url"], a["title"]), author_box("../"), rel))
        ld = jsonld({"@context": "https://schema.org", "@type": "Article", "headline": a["title"], "description": a["description"],
                     "datePublished": a["date"], "image": SITE + (("img/articles/%s.jpg" % a["slug"]) if IMAGES else "og.png"),
                     "author": {"@type": "Person", "name": SITECFG.get("profile_name", "運営者"), "url": SITE + "about.html"},
                     "publisher": {"@type": "Organization", "name": NAME}, "mainEntityOfPage": SITE + a["url"]}) + \
            crumbs_ld([("ホーム", "index.html"), (cat, cu), (a["title"], a["url"])])
        write(a["url"], page(a["title"], a["description"], body, a["url"], 1,
                             ("img/articles/%s.jpg" % a["slug"]) if IMAGES else "og.png", ld=ld, cat_on=cat))
    about = ('<article><h1>このサイトについて</h1>' + SITECFG["about_html"] +
             '<h2>広告について</h2><p>当サイトは Amazonアソシエイト・楽天アフィリエイトに参加しており、紹介した商品の購入により運営者が紹介料を受け取ることがあります。Amazonのアソシエイトとして、当サイトは適格販売により収入を得ています。</p></article>')
    write("about.html", page("このサイトについて", NAME + "の運営方針と広告について。", about, "about.html"))
    privacy = """<article><h1>プライバシーポリシー</h1>
<h2>アクセス解析</h2><p>当サイトは Google アナリティクスを利用しています。Cookie を使ってアクセス情報を収集しますが、個人を特定する情報は含みません。Cookie はブラウザの設定で無効にできます。</p>
<h2>広告</h2><p>当サイトは Amazonアソシエイト・楽天アフィリエイトを利用しています。これらのサービスは Cookie を使用することがあります。</p>
<h2>免責事項</h2><p>掲載内容の正確性には注意していますが、内容を保証するものではありません。当サイトの情報によって生じた損害について責任を負いかねます。</p></article>"""
    write("privacy.html", page("プライバシーポリシー", NAME + "のプライバシーポリシーと免責事項。", privacy, "privacy.html", sidebar=False))
    urls = ["index.html", "about.html", "privacy.html"] + ["category/%s.html" % cat_slug(c) for c, _ in CATS] + [a["url"] for a in arts]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join("<url><loc>%s%s</loc></url>\n" % (SITE, u) for u in urls) + "</urlset>\n")
    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n" % SITE)
    write(".nojekyll", "")
    print("built %d articles, %d categories" % (len(arts), len(CATS)))

if __name__ == "__main__":
    build()
