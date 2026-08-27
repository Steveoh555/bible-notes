#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성경연구노트 — 사이트 빌드 스크립트

  python3 build.py            자료를 훑어 홈·사이트맵·RSS를 다시 만들고
                              모든 페이지에 공통 헤더/푸터/SEO 태그를 주입합니다.
  python3 build.py new 슬러그 "제목"
                              새 자료 페이지 뼈대를 studies/ 에 만듭니다.

자료 페이지는 <head> 안의 메타 태그로 자기 정보를 알려 줍니다.
  <title>…</title>
  <meta name="description" content="…">
  <meta name="study:scripture" content="누가복음 2:1–7">
  <meta name="study:tags" content="연대기, 로마사">
  <meta name="study:date" content="2026-08-27">
  <meta name="study:updated" content="2026-08-27">   (선택)
  <meta name="study:draft" content="true">           (선택 — 목록에서 숨김)
"""
import os, re, json, html, sys, datetime, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(ROOT, "site.config.json")

DEFAULT_CFG = {
    "site_name": "성경연구노트",
    "tagline": "1차 자료로 확인하는 성경 배경",
    "site_url": "",
    "author": "",
    "description": "성경 본문의 역사·지리·문헌 배경을 1차 자료로 확인해 정리한 연구 자료 모음입니다.",
    "locale": "ko_KR"
}

def load_cfg():
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg = dict(DEFAULT_CFG); cfg.update(json.load(f)); return cfg
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CFG, f, ensure_ascii=False, indent=2)
    return dict(DEFAULT_CFG)

def read(p):
    with open(p, encoding="utf-8") as f: return f.read()

def write(p, s):
    with open(p, "w", encoding="utf-8", newline="\n") as f: f.write(s)

def esc(s):
    return html.escape(s or "", quote=True)

# ---------- 메타 읽기 ----------
def meta_of(path):
    src = read(path)
    def m(name):
        r = re.search(r'<meta\s+name="%s"\s+content="([^"]*)"' % re.escape(name), src, re.I)
        return html.unescape(r.group(1)).strip() if r else ""
    t = re.search(r"<title>(.*?)</title>", src, re.S | re.I)
    title = html.unescape(t.group(1)).strip() if t else os.path.basename(path)
    title = re.sub(r"\s*[—|]\s*성경연구노트\s*$", "", title)
    tags = [x.strip() for x in re.split(r"[,·]", m("study:tags")) if x.strip()]
    return {
        "path": path,
        "slug": os.path.splitext(os.path.basename(path))[0],
        "url": "studies/" + os.path.basename(path),
        "title": title,
        "description": m("description"),
        "scripture": m("study:scripture"),
        "tags": tags,
        "date": m("study:date") or "1970-01-01",
        "updated": m("study:updated") or m("study:date") or "1970-01-01",
        "draft": m("study:draft").lower() == "true",
        "src": src,
    }

# ---------- 주입 블록 ----------
def nav(cfg, depth):
    up = "../" if depth else ""
    items = [(up + "index.html", "자료 목록"), (up + "about.html", "소개")]
    links = "".join(
        '\n          <a href="%s">%s</a>' % (esc(h), esc(t)) for h, t in items)
    return """<header class="site-head">
      <div class="bar">
        <a class="brand" href="{up}index.html">
          <b>{name}</b><span>{tag}</span>
        </a>
        <nav class="site-nav" aria-label="주요 메뉴">{links}
        </nav>
        <button id="themeBtn" class="theme-btn" type="button" aria-label="화면 테마 바꾸기">자동</button>
      </div>
    </header>""".format(up=up, name=esc(cfg["site_name"]), tag=esc(cfg["tagline"]), links=links)

def foot(cfg, depth):
    up = "../" if depth else ""
    year = datetime.date.today().year
    who = (" · " + esc(cfg["author"])) if cfg.get("author") else ""
    rss = (' · <a href="%sfeed.xml">RSS</a>' % up) if cfg.get("site_url") else ""
    return """<footer class="site-foot">
      <div class="inner">
        <p><strong>{name}</strong> — {desc}</p>
        <p>인용한 고전·1차 자료(요세푸스, 미쉬나, 교부 문헌 등)의 출처는 각 자료 페이지 하단에 밝혀 두었습니다. 확정되지 않은 견해는 &ldquo;가설&rdquo; 또는 &ldquo;이견&rdquo;으로 표시합니다.</p>
        <p class="src">© {year} {name}{who} · <a href="{up}index.html">자료 목록</a> · <a href="{up}about.html">소개</a>{rss}</p>
      </div>
    </footer>""".format(name=esc(cfg["site_name"]), desc=esc(cfg["description"]),
                        year=year, who=who, up=up, rss=rss)

def headtags(cfg, info, depth):
    """canonical / Open Graph / JSON-LD — 검색엔진용"""
    base = cfg.get("site_url", "").rstrip("/")
    url = (base + "/" + info["url"]) if base else ""
    parts = []
    if url:
        parts.append('<link rel="canonical" href="%s">' % esc(url))
    parts += [
        '<meta property="og:type" content="article">',
        '<meta property="og:site_name" content="%s">' % esc(cfg["site_name"]),
        '<meta property="og:locale" content="%s">' % esc(cfg.get("locale", "ko_KR")),
        '<meta property="og:title" content="%s">' % esc(info["title"]),
        '<meta property="og:description" content="%s">' % esc(info["description"]),
        '<meta name="twitter:card" content="summary">',
    ]
    if url:
        parts.insert(-1, '<meta property="og:url" content="%s">' % esc(url))
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": info["title"],
        "description": info["description"],
        "datePublished": info["date"],
        "dateModified": info["updated"],
        "inLanguage": "ko",
        "isPartOf": {"@type": "WebSite", "name": cfg["site_name"]},
    }
    if url: ld["mainEntityOfPage"] = url
    if cfg.get("author"): ld["author"] = {"@type": "Person", "name": cfg["author"]}
    if info["tags"]: ld["keywords"] = ", ".join(info["tags"])
    parts.append('<script type="application/ld+json">%s</script>'
                 % json.dumps(ld, ensure_ascii=False))
    return "\n    ".join(parts)

MARK = {
    "HEAD":   ("<!--#HEAD-->",   "<!--/#HEAD-->"),
    "HEADER": ("<!--#HEADER-->", "<!--/#HEADER-->"),
    "FOOTER": ("<!--#FOOTER-->", "<!--/#FOOTER-->"),
}

def inject(src, key, content):
    a, b = MARK[key]
    if a not in src or b not in src:
        return src, False
    pat = re.compile(re.escape(a) + r".*?" + re.escape(b), re.S)
    return pat.sub(lambda _: a + "\n    " + content + "\n    " + b, src, count=1), True

# ---------- 홈 ----------
def card(cfg, s):
    search = " ".join([s["title"], s["description"], s["scripture"]] + s["tags"]).lower()
    tags = "".join('<span class="tag">%s</span>' % esc(t) for t in s["tags"][:3])
    return """      <a class="card" href="{url}" data-search="{search}">
        <span class="scripture">{scripture}</span>
        <h3>{title}</h3>
        <p>{desc}</p>
        <div class="meta"><time datetime="{date}">{date}</time>{tags}</div>
      </a>""".format(url=esc(s["url"]), search=esc(search), scripture=esc(s["scripture"] or "성경 배경"),
                     title=esc(s["title"]), desc=esc(s["description"]),
                     date=esc(s["date"]), tags=tags)

def build_index(cfg, studies):
    cards = "\n".join(card(cfg, s) for s in studies) or ""
    n = len(studies)
    body = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} — {tag}</title>
<meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="assets/site.css">
{rsslink}<script>try{{var t=localStorage.getItem('bnote-theme');if(t&&t!=='auto')document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
</head>
<body>
    <!--#HEADER--><!--/#HEADER-->

    <main class="wrap">
      <header>
        <div class="eyebrow">성경 배경 연구</div>
        <h1>{tag}</h1>
        <p class="lede">{desc}</p>
      </header>

      <section>
        <div class="search-row">
          <label for="q" class="sr-only" style="position:absolute;left:-9999px">자료 검색</label>
          <input id="q" type="search" placeholder="본문·주제·인물로 찾기 (예: 누가복음, 호적, 헤롯)" autocomplete="off">
          <span class="count" id="count">{n} 편</span>
        </div>
        <div class="grid">
{cards}
        </div>
        <p class="empty" id="empty" hidden>찾는 자료가 없습니다. 다른 낱말로 검색해 보세요.</p>
      </section>
    </main>

    <!--#FOOTER--><!--/#FOOTER-->
<script src="assets/site.js"></script>
</body>
</html>
""".format(name=esc(cfg["site_name"]), tag=esc(cfg["tagline"]),
           desc=esc(cfg["description"]), n=n, cards=cards,
           rsslink=('<link rel="alternate" type="application/rss+xml" title="%s" href="feed.xml">\n' % esc(cfg["site_name"])) if cfg.get("site_url") else "")
    body, _ = inject(body, "HEADER", nav(cfg, 0))
    body, _ = inject(body, "FOOTER", foot(cfg, 0))
    write(os.path.join(ROOT, "index.html"), body)

# ---------- 사이트맵 / RSS ----------
def build_sitemap(cfg, studies):
    base = cfg.get("site_url", "").rstrip("/")
    if not base:
        print("  ! site_url 이 비어 있어 sitemap/feed 를 건너뜁니다 (site.config.json)")
        return False
    urls = [(base + "/", datetime.date.today().isoformat(), "1.0"),
            (base + "/about.html", datetime.date.today().isoformat(), "0.3")]
    urls += [(base + "/" + s["url"], s["updated"], "0.8") for s in studies]
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, d, p in urls:
        body.append("  <url><loc>%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (esc(u), d, p))
    body.append("</urlset>")
    write(os.path.join(ROOT, "sitemap.xml"), "\n".join(body) + "\n")

    rt = read(os.path.join(ROOT, "robots.txt"))
    rt = re.sub(r"Sitemap: .*", "Sitemap: %s/sitemap.xml" % base, rt)
    write(os.path.join(ROOT, "robots.txt"), rt)
    return True

def rfc822(d):
    try:
        y, m, dd = [int(x) for x in d.split("-")]
        return datetime.datetime(y, m, dd).strftime("%a, %d %b %Y 00:00:00 +0900")
    except Exception:
        return datetime.datetime.now().strftime("%a, %d %b %Y 00:00:00 +0900")

def build_feed(cfg, studies):
    base = cfg.get("site_url", "").rstrip("/")
    if not base: return
    items = []
    for s in studies[:30]:
        link = base + "/" + s["url"]
        items.append("""    <item>
      <title>%s</title>
      <link>%s</link>
      <guid isPermaLink="true">%s</guid>
      <pubDate>%s</pubDate>
      <description>%s</description>
    </item>""" % (esc(s["title"]), esc(link), esc(link), rfc822(s["date"]), esc(s["description"])))
    body = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>%s</title>
    <link>%s/</link>
    <atom:link href="%s/feed.xml" rel="self" type="application/rss+xml"/>
    <description>%s</description>
    <language>ko</language>
%s
  </channel>
</rss>
""" % (esc(cfg["site_name"]), esc(base), esc(base), esc(cfg["description"]), "\n".join(items))
    write(os.path.join(ROOT, "feed.xml"), body)

# ---------- 새 페이지 ----------
SKELETON = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — 성경연구노트</title>
<meta name="description" content="여기에 한 문장 요약을 씁니다. 검색 결과에 그대로 보입니다.">
<meta name="study:scripture" content="">
<meta name="study:tags" content="">
<meta name="study:date" content="{today}">
<meta name="study:updated" content="{today}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="../assets/site.css">
<script>try{{var t=localStorage.getItem('bnote-theme');if(t&&t!=='auto')document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
<!--#HEAD--><!--/#HEAD-->
</head>
<body>
    <!--#HEADER--><!--/#HEADER-->

    <article class="wrap">
      <header>
        <div class="eyebrow">본문 표기</div>
        <h1>{title}</h1>
        <p class="lede">한 문단 도입부.</p>
      </header>

      <section>
        <h2><span class="num">1</span>첫 절</h2>
        <div class="prose"><p>내용.</p></div>
      </section>
    </article>

    <!--#FOOTER--><!--/#FOOTER-->
<script src="../assets/site.js"></script>
</body>
</html>
"""

def cmd_new(slug, title):
    p = os.path.join(ROOT, "studies", slug + ".html")
    if os.path.exists(p):
        print("이미 있습니다:", p); return
    write(p, SKELETON.format(title=title, today=datetime.date.today().isoformat()))
    print("만들었습니다:", p)

# ---------- 메인 ----------
def main():
    cfg = load_cfg()
    if len(sys.argv) > 1 and sys.argv[1] == "new":
        if len(sys.argv) < 4:
            print('사용법: python3 build.py new 슬러그 "제목"'); return
        cmd_new(sys.argv[2], sys.argv[3]); return

    files = sorted(glob.glob(os.path.join(ROOT, "studies", "*.html")))
    infos = [meta_of(f) for f in files]
    live = [i for i in infos if not i["draft"]]
    live.sort(key=lambda s: (s["date"], s["title"]), reverse=True)

    print("자료 %d편 (초안 %d편 제외)" % (len(live), len(infos) - len(live)))
    warn = 0
    for i in infos:
        src = i["src"]
        src, ok1 = inject(src, "HEAD", headtags(cfg, i, 1))
        src, ok2 = inject(src, "HEADER", nav(cfg, 1))
        src, ok3 = inject(src, "FOOTER", foot(cfg, 1))
        if src != i["src"]: write(i["path"], src)
        missing = [k for k, ok in (("HEAD", ok1), ("HEADER", ok2), ("FOOTER", ok3)) if not ok]
        flag = ""
        if missing: flag = "  ! 표시자 없음: " + ",".join(missing); warn += 1
        if not i["description"]: flag += "  ! description 비어 있음"; warn += 1
        print("  - %-34s %s%s" % (i["slug"], i["date"], flag))

    # about.html 도 헤더/푸터 갱신
    ap = os.path.join(ROOT, "about.html")
    if os.path.exists(ap):
        s = read(ap)
        s, _ = inject(s, "HEADER", nav(cfg, 0))
        s, _ = inject(s, "FOOTER", foot(cfg, 0))
        write(ap, s)

    build_index(cfg, live)
    if build_sitemap(cfg, live):
        build_feed(cfg, live)
        print("  sitemap.xml · feed.xml 갱신")
    print("index.html 갱신 완료" + ("  (경고 %d건)" % warn if warn else ""))

if __name__ == "__main__":
    main()
