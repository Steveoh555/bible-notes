#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성경연구노트 사이트 빌드 스크립트

  python3 build.py            자료를 훑어 홈·사이트맵·RSS를 다시 만들고
                              모든 페이지에 공통 헤더/푸터/SEO 태그를 주입합니다.
  python3 build.py new 슬러그 "제목"
                              새 자료 페이지 뼈대를 studies/ 에 만듭니다.

자료 페이지는 <head> 안의 메타 태그로 자기 정보를 알려 줍니다.
  <title>…</title>
  <meta name="description" content="…">
  <meta name="study:scripture" content="누가복음 2:1-7">
  <meta name="study:tags" content="연대기, 로마사">
  <meta name="study:date" content="2026-08-27">
  <meta name="study:updated" content="2026-08-27">   (선택)
  <meta name="study:draft" content="true">           (선택. 목록에서 숨김)
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
    title = re.sub(r"\s*[-—|]\s*성경연구노트\s*$", "", title)
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
        "hero": m("study:hero"),
        "hero_alt": m("study:hero-alt"),
        "src": src,
    }

# ---------- 주입 블록 ----------
def nav(cfg, depth, current=None):
    up = "../" if depth else ""
    items = [(up + "index.html", "자료 목록", "index"), (up + "about.html", "소개", "about")]
    links = "".join(
        '\n          <a href="%s"%s>%s</a>'
        % (esc(h), ' aria-current="page"' if k == current else "", esc(t))
        for h, t, k in items)
    return """<a class="skip" href="#main">본문으로 건너뛰기</a>
    <header class="site-head">
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
    rss = (' <a href="%sfeed.xml">RSS</a>' % up) if cfg.get("site_url") else ""
    return """<footer class="site-foot">
      <div class="inner">
        <p><strong>{name}</strong></p>
        <p>{desc}</p>
        <p>인용한 고전·1차 자료(요세푸스, 미쉬나, 교부 문헌 등)의 출처는 각 자료 페이지 하단에 밝혀 두었습니다. 확정되지 않은 견해는 &ldquo;가설&rdquo; 또는 &ldquo;이견&rdquo;으로 표시합니다.</p>
        <p class="src">© {year} {name}{who}</p>
        <p class="foot-links"><a href="{up}index.html">자료 목록</a> <a href="{up}about.html">소개</a>{rss}</p>
      </div>
    </footer>""".format(name=esc(cfg["site_name"]), desc=esc(cfg["description"]),
                        year=year, who=who, up=up, rss=rss)

def headtags(cfg, info, depth):
    """canonical / Open Graph / JSON-LD. 검색엔진용"""
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
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    if base:
        img = ("/assets/img/" + info["hero"]) if info.get("hero") else "/assets/og.png"
        parts += [
            '<meta property="og:image" content="%s">' % esc(base + img),
            '<meta name="twitter:image" content="%s">' % esc(base + img),
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
    "HERO":   ("<!--#HERO-->",   "<!--/#HERO-->"),
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


FAVICON_BLOCK = (
    '<link rel="icon" type="image/svg+xml" href="{up}assets/favicon.svg">\n'
    '<link rel="apple-touch-icon" href="{up}assets/icon-180.png">\n'
    '<meta name="theme-color" content="#EFF0EA" media="(prefers-color-scheme: light)">\n'
    '<meta name="theme-color" content="#141714" media="(prefers-color-scheme: dark)">'
)

def ensure_head_links(src, depth):
    """파비콘·테마색이 없으면 viewport 메타 뒤에 넣는다."""
    if 'rel="icon"' in src:
        return src
    up = "../" if depth else ""
    block = FAVICON_BLOCK.format(up=up)
    m = re.search(r'<meta name="viewport"[^>]*>', src)
    if not m:
        return src
    return src[:m.end()] + "\n" + block + src[m.end():]

def ensure_main_id(src):
    """건너뛰기 링크가 닿을 곳을 만든다."""
    if 'id="main"' in src:
        return src
    return re.sub(r'<(article|main) class="wrap">', r'<\1 id="main" class="wrap">', src, count=1)


# ---------- 자산 캐시 무효화 ----------
def asset_versions():
    """site.css / site.js 의 내용 해시. 배포마다 주소가 바뀌어 옛 캐시를 안 쓴다."""
    import hashlib
    out = {}
    for f in ("site.css", "site.js"):
        fp = os.path.join(ROOT, "assets", f)
        out[f] = hashlib.md5(read(fp).encode()).hexdigest()[:8] if os.path.exists(fp) else "0"
    return out

def stamp_assets(src, ver):
    """assets/site.css|js 링크에 ?v=해시 를 붙이거나 갱신한다."""
    for f, key in (("site.css", "site.css"), ("site.js", "site.js")):
        src = re.sub(r'(assets/' + re.escape(f) + r')(\?v=[0-9a-f]+)?',
                     lambda m: m.group(1) + "?v=" + ver[key], src)
    return src


# ---------- 이미지 출처 원장 ----------
CRED_PATH = os.path.join(ROOT, "assets", "img", "출처.json")
# 홈·소개 템플릿(아래 hero figcaption)과 문구가 같아야 한다. 고치면 양쪽 다 고칠 것.
AI_NOTE = "그림: 내용을 돕기 위한 AI 생성 삽화입니다. 실제 유물이나 사료가 아닙니다."
FREE_LICENSES = ("public domain", "cc0", "pd-old", "pd-us", "no restrictions", "pd")

def credits():
    """assets/img/출처.json 을 읽는다. 없으면 빈 원장."""
    if not os.path.exists(CRED_PATH):
        return {}
    try:
        with open(CRED_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("  ! 출처.json 을 읽지 못했습니다: %s" % e)
        return {}

def is_free(lic):
    return (lic or "").strip().lower().startswith(FREE_LICENSES)

def jpeg_size(path):
    """JPEG/PNG 의 가로·세로를 헤더에서 읽는다. 실패하면 None."""
    try:
        with open(path, "rb") as f:
            d = f.read(24)
            if d[:8] == b"\x89PNG\r\n\x1a\n":
                import struct
                return struct.unpack(">II", d[16:24])
            if d[:2] != b"\xff\xd8":
                return None
            f.seek(2)
            while True:
                b = f.read(1)
                while b and b != b"\xff":
                    b = f.read(1)
                m = f.read(1)
                while m == b"\xff":
                    m = f.read(1)
                if not m:
                    return None
                if m[0] in range(0xC0, 0xD0) and m[0] not in (0xC4, 0xC8, 0xCC):
                    f.read(3)
                    import struct
                    h, w = struct.unpack(">HH", f.read(4))
                    return (w, h)
                import struct
                ln = struct.unpack(">H", f.read(2))[0]
                f.seek(ln - 2, 1)
    except Exception:
        return None

PLATE_RE = re.compile(r"<!--#PLATE:([^>]*?)-->.*?<!--/#PLATE-->", re.S)

def plate_figure(spec, cred, depth):
    """<!--#PLATE:파일명|옵션--> 을 출처가 붙은 그림으로 바꾼다."""
    bits  = [x.strip() for x in spec.split("|")]
    fname = bits[0]
    opts  = [b for b in bits[1:] if b]
    c     = cred.get(fname)
    if c is None:
        return None, "원장에 %s 항목이 없습니다" % fname
    if c.get("분류") == "사료" and not is_free(c.get("라이선스")):
        return None, "%s 의 라이선스(%s)는 허용 목록에 없습니다" % (fname, c.get("라이선스"))

    up  = "../" if depth else ""
    dim = jpeg_size(os.path.join(ROOT, "assets", "img", fname))
    wh  = ' width="%d" height="%d"' % dim if dim else ""
    alt = c.get("alt") or c.get("제목") or fname
    cls = " ".join(["plate"] + opts + ([] if c.get("분류") == "사료" else ["ai"]))

    img = ('<img src="%sassets/img/%s" alt="%s"%s loading="lazy" decoding="async">'
           % (up, esc(fname), esc(alt), wh))

    if c.get("분류") != "사료":
        return ('<figure class="%s">\n        %s\n        <figcaption>%s</figcaption>\n      </figure>'
                % (esc(cls), img, esc(AI_NOTE))), None

    src_page = c.get("원본페이지", "")
    if src_page:
        img = '<a class="plate-img" href="%s" target="_blank" rel="noopener">%s</a>' % (esc(src_page), img)

    head = esc(c.get("제목", fname))
    if c.get("연도"):
        head += ' <span class="plate-year">%s</span>' % esc(c["연도"])

    line = []
    if c.get("제작자"): line.append(esc(c["제작자"]))
    if c.get("소장"):   line.append(esc(c["소장"]))
    lic = esc(c.get("라이선스", ""))
    if c.get("라이선스URL"):
        lic = '<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(c["라이선스URL"]), lic)
    if lic: line.append(lic + " · 자유 이용")
    if src_page: line.append('<a href="%s" target="_blank" rel="noopener">원본 보기</a>' % esc(src_page))

    note = ('<span class="plate-note">%s</span>' % esc(c["설명"])) if c.get("설명") else ""
    return ('<figure class="%s">\n        %s\n        <figcaption>'
            '<b class="plate-title">%s</b>%s'
            '<span class="plate-src">%s</span>'
            '</figcaption>\n      </figure>'
            % (esc(cls), img, head, note, " · ".join(line))), None

def inject_plates(src, cred, depth, slug=""):
    """페이지 안의 모든 PLATE 표시자를 채운다. 반환: (본문, 경고목록)"""
    warns = []
    def one(m):
        fig, err = plate_figure(m.group(1), cred, depth)
        if err:
            warns.append("%s: %s" % (slug, err))
            return m.group(0)
        return "<!--#PLATE:%s-->\n      %s\n      <!--/#PLATE-->" % (m.group(1), fig)
    return PLATE_RE.sub(one, src), warns


def hero_band(info, depth):
    """study:hero 로 지정된 이미지를 제목 위 밴드로 만든다."""
    if not info.get("hero"):
        return ""
    up = "../" if depth else ""
    alt = info.get("hero_alt") or (info["title"] + " 분위기 그림")
    return ('<figure class="hero-band">\n'
            '        <span class="frame"><img src="%sassets/img/%s" alt="%s" '
            'width="1400" height="594" loading="eager" decoding="async"></span>\n'
            '        <figcaption>%s</figcaption>\n'
            '      </figure>') % (up, esc(info["hero"]), esc(alt),
                                  esc(AI_NOTE))

# ---------- 홈 ----------
def card(cfg, s):
    search = " ".join([s["title"], s["description"], s["scripture"]] + s["tags"]).lower()
    tags = "".join('<span class="tag">%s</span>' % esc(t) for t in s["tags"][:3])
    return """        <li><a class="entry" href="{url}" data-search="{search}">
          <span class="entry-ref">{scripture}</span>
          <span class="entry-main">
            <span class="entry-title">{title}</span>
            <span class="entry-desc">{desc}</span>
            <span class="entry-meta"><time datetime="{date}">{date}</time>{tags}</span>
          </span>
        </a></li>""".format(
        url=esc(s["url"]), search=esc(search),
        scripture=esc(s["scripture"] or "성경 배경"),
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
<title>{name} - {tag}</title>
<meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css">
<link rel="stylesheet" href="assets/site.css">\n{favicon}
{rsslink}<script>try{{var t=localStorage.getItem('bnote-theme');if(t&&t!=='auto')document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
</head>
<body>
    <!--#HEADER--><!--/#HEADER-->

    <main id="main" class="wrap">
      <header>
        <figure class="hero-band">
          <span class="frame"><img src="assets/img/hero-home.jpg" alt="올리브 나무가 선 유대 산지의 계단밭과 멀리 성벽으로 둘러싸인 마을을 그린 그림" width="1400" height="594" loading="eager" decoding="async"></span>
          <figcaption>그림: 내용을 돕기 위한 AI 생성 삽화입니다. 실제 유물이나 사료가 아닙니다.</figcaption>
        </figure>
        <div class="eyebrow">성경 배경 연구</div>
        <h1>{tag}</h1>
        <p class="lede">{desc}</p>
      </header>

      <section>
        <div class="search-row">
          <label for="q" class="sr-only" style="position:absolute;left:-9999px">자료 검색</label>
          <input id="q" type="search" placeholder="본문, 주제, 인물로 찾기. 누가복음, 호적, 헤롯…" autocomplete="off">
          <span class="count" id="count">{n} 편</span>
        </div>
        <ol class="index-list">
{cards}
        </ol>
        <p class="empty" id="empty" hidden>찾는 자료가 없습니다. 다른 낱말로 검색해 보세요.</p>
      </section>
    </main>

    <!--#FOOTER--><!--/#FOOTER-->
<script src="assets/site.js"></script>
</body>
</html>
""".format(name=esc(cfg["site_name"]), tag=esc(cfg["tagline"]),
           desc=esc(cfg["description"]), n=n, cards=cards,
           favicon=FAVICON_BLOCK.format(up=""),
           rsslink=('<link rel="alternate" type="application/rss+xml" title="%s" href="feed.xml">\n' % esc(cfg["site_name"])) if cfg.get("site_url") else "")
    body, _ = inject(body, "HEADER", nav(cfg, 0, "index"))
    body, _ = inject(body, "FOOTER", foot(cfg, 0))
    body = stamp_assets(body, asset_versions())
    write(os.path.join(ROOT, "index.html"), body)


# ---------- 404 ----------
def build_404(cfg):
    base = cfg.get("site_url", "").rstrip("/")
    home = (base + "/") if base else "index.html"
    body = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>찾는 자료가 없습니다 - {name}</title>
<meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css">
<link rel="stylesheet" href="{base}/assets/site.css">
<link rel="icon" type="image/svg+xml" href="{base}/assets/favicon.svg">
<meta name="theme-color" content="#EFF0EA" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#141714" media="(prefers-color-scheme: dark)">
<script>try{{var t=localStorage.getItem('bnote-theme');if(t&&t!=='auto')document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
</head>
<body>
    <!--#HEADER--><!--/#HEADER-->
    <main id="main" class="wrap">
      <header>
        <p class="eyebrow">404</p>
        <h1>이 주소에는 자료가 없습니다</h1>
        <p class="lede">주소가 바뀌었거나, 아직 없는 <span class="nb">자료일 수</span> 있습니다.
          자료 목록에서 찾아보시면 대부분 해결됩니다.</p>
      </header>
      <section>
        <div class="prose">
          <p><a href="{home}">자료 목록으로 돌아가기</a></p>
        </div>
      </section>
    </main>
    <!--#FOOTER--><!--/#FOOTER-->
</body>
</html>
""".format(name=esc(cfg["site_name"]), base=esc(base), home=esc(home))
    body, _ = inject(body, "HEADER", nav(cfg, 0))
    body, _ = inject(body, "FOOTER", foot(cfg, 0))
    # 404 는 어느 깊이에서든 뜨므로 링크를 절대 주소로
    if base:
        body = body.replace('href="index.html"', 'href="%s/index.html"' % esc(base))
        body = body.replace('href="about.html"', 'href="%s/about.html"' % esc(base))
        body = body.replace('href="feed.xml"', 'href="%s/feed.xml"' % esc(base))
    body = stamp_assets(body, asset_versions())
    write(os.path.join(ROOT, "404.html"), body)

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
<title>{title} - 성경연구노트</title>
<meta name="description" content="여기에 한 문장 요약을 씁니다. 검색 결과에 그대로 보입니다.">
<meta name="study:scripture" content="">
<meta name="study:tags" content="">
<meta name="study:hero" content="">
<meta name="study:hero-alt" content="">
<meta name="study:date" content="{today}">
<meta name="study:updated" content="{today}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css">
<link rel="stylesheet" href="../assets/site.css">
<script>try{{var t=localStorage.getItem('bnote-theme');if(t&&t!=='auto')document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
<!--#HEAD--><!--/#HEAD-->
</head>
<body>
    <!--#HEADER--><!--/#HEADER-->

    <article class="wrap">
      <header>
        <!--#HERO--><!--/#HERO-->
        <div class="eyebrow">본문 표기</div>
        <h1>{title}</h1>
        <p class="lede">한 문단 도입부.</p>
      </header>

      <section>
        <h2>첫 절</h2>
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


# ---------- 단일 파일로 뽑기 ----------
def cmd_standalone(slug, outdir=None):
    """공유·미리보기용. 외부 css/js 를 안에 넣어 파일 하나로 만듭니다."""
    src_path = os.path.join(ROOT, "studies", slug + ".html")
    if not os.path.exists(src_path):
        print("그런 자료가 없습니다:", src_path); return
    s = read(src_path)
    css = read(os.path.join(ROOT, "assets", "site.css"))
    js  = read(os.path.join(ROOT, "assets", "site.js"))
    s = s.replace('<link rel="stylesheet" href="../assets/site.css">',
                  "<style>\n" + css + "\n</style>")
    s = s.replace('<script src="../assets/site.js"></script>',
                  "<script>\n" + js + "\n</script>")
    # 사이트 내부 링크는 단독 파일에서 의미가 없으므로 헤더/푸터 메뉴를 걷어냅니다
    for k in ("HEADER", "FOOTER"):
        a, b = MARK[k]
        s = re.sub(re.escape(a) + r".*?" + re.escape(b), "", s, flags=re.S)
    out = os.path.join(outdir or ROOT, slug + ".standalone.html")
    write(out, s)
    print("만들었습니다:", out, "(%.1f KB)" % (len(s.encode()) / 1024))


# ---------- 성경 인용 현황 ----------
BQ = re.compile(
    r'<blockquote[^>]*class="[^"]*bible[^"]*"[^>]*data-ref="([^"]+)"[^>]*'
    r'(?:data-version="([^"]*)")?[^>]*>(.*?)</blockquote>', re.S)

def verse_count(ref):
    """'누가복음 2:4-5' → 2 ,  '출애굽기 4:20' → 1"""
    m = re.search(r"(\d+)\s*:\s*(\d+)(?:\s*[-–~]\s*(\d+))?", ref)
    if not m:
        return 0
    a = int(m.group(2)); b = int(m.group(3) or a)
    return max(1, b - a + 1)

def collect_quotes():
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "studies", "*.html"))):
        src = read(f)
        t = re.search(r"<title>(.*?)</title>", src, re.S)
        title = re.sub(r"\s*[-—|]\s*성경연구노트\s*$", "",
                       html.unescape(t.group(1)).strip()) if t else os.path.basename(f)
        for m in BQ.finditer(src):
            ref = html.unescape(m.group(1)).strip()
            ver = html.unescape(m.group(2) or "개역개정").strip()
            body = re.sub(r"<[^>]+>", "", m.group(3))
            body = html.unescape(body)
            # 한글만 세어 대략의 인용 분량을 낸다(원문 히브리어·헬라어 제외)
            ko = len(re.findall(r"[가-힣]", body))
            rows.append({"page": os.path.basename(f), "title": title,
                         "ref": ref, "version": ver,
                         "verses": verse_count(ref), "chars": ko})
    return rows

def build_quotes(cfg):
    rows = collect_quotes()
    lines = [
        "# 성경 인용 현황",
        "",
        "이 파일은 `build.py`가 자동으로 만듭니다. 직접 고치지 마세요.",
        "사이트에 실린 성경 본문 인용을 전부 모은 표입니다.",
        "대한성서공회에 저작권을 문의할 때 이 표를 그대로 쓰시면 됩니다.",
        "",
    ]
    if not rows:
        lines.append("아직 표시된 성경 인용이 없습니다.")
    else:
        by_ver = {}
        for r in rows:
            by_ver.setdefault(r["version"], []).append(r)
        tv = sum(r["verses"] for r in rows)
        tc = sum(r["chars"] for r in rows)
        lines += [f"**전체 {len(rows)}건 · 약 {tv}절 · 한글 {tc:,}자**", ""]
        for ver, rs in sorted(by_ver.items()):
            lines += [f"## {ver}: {len(rs)}건 · 약 {sum(r['verses'] for r in rs)}절", "",
                      "| 자료 | 구절 | 절 수 | 한글 글자 수 |", "|---|---|---:|---:|"]
            for r in sorted(rs, key=lambda x: x["page"]):
                lines.append(f"| {r['title']} | {r['ref']} | {r['verses']} | {r['chars']} |")
            lines.append("")
    write(os.path.join(ROOT, "인용현황.md"), "\n".join(lines) + "\n")
    return rows

# ---------- 메인 ----------
def main():
    cfg = load_cfg()
    if len(sys.argv) > 1 and sys.argv[1] == "standalone":
        if len(sys.argv) < 3:
            print("사용법: python3 build.py standalone 슬러그 [출력폴더]"); return
        cmd_standalone(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None); return
    if len(sys.argv) > 1 and sys.argv[1] == "new":
        if len(sys.argv) < 4:
            print('사용법: python3 build.py new 슬러그 "제목"'); return
        cmd_new(sys.argv[2], sys.argv[3]); return

    ver = asset_versions()
    files = sorted(glob.glob(os.path.join(ROOT, "studies", "*.html")))
    infos = [meta_of(f) for f in files]
    live = [i for i in infos if not i["draft"]]
    live.sort(key=lambda s: (s["date"], s["title"]), reverse=True)

    print("자료 %d편 (초안 %d편 제외)" % (len(live), len(infos) - len(live)))
    warn = 0
    cred = credits()
    plate_warn = []
    for i in infos:
        src = i["src"]
        src, ok1 = inject(src, "HEAD", headtags(cfg, i, 1))
        src, ok2 = inject(src, "HEADER", nav(cfg, 1))
        src, ok3 = inject(src, "FOOTER", foot(cfg, 1))
        src, _   = inject(src, "HERO", hero_band(i, 1))
        src, pw  = inject_plates(src, cred, 1, i["slug"])
        plate_warn += pw
        src = ensure_head_links(src, 1)
        src = ensure_main_id(src)
        src = stamp_assets(src, ver)
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
        s, _ = inject(s, "HEADER", nav(cfg, 0, "about"))
        s = ensure_head_links(s, 0)
        s = ensure_main_id(s)
        s = stamp_assets(s, ver)
        s, _ = inject(s, "FOOTER", foot(cfg, 0))
        write(ap, s)

    for w in plate_warn:
        print("  ! 도판 %s" % w)
    warn += len(plate_warn)

    qrows = build_quotes(cfg)
    if qrows:
        print("  성경 인용 %d건 · 약 %d절 → 인용현황.md"
              % (len(qrows), sum(r["verses"] for r in qrows)))

    build_index(cfg, live)
    build_404(cfg)
    if build_sitemap(cfg, live):
        build_feed(cfg, live)
        print("  sitemap.xml · feed.xml 갱신")
    print("index.html 갱신 완료" + ("  (경고 %d건)" % warn if warn else ""))

if __name__ == "__main__":
    main()
