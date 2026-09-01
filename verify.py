#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""성경연구노트 — 배포 전 점검

  python3 verify.py

링크, 태그 균형, 필수 메타, 공통 요소 주입, 다크모드 토큰 누락을 확인합니다.
문제가 있으면 종료 코드 1을 돌려줍니다.
"""
import re, os, glob, io, sys, json

ROOT = os.path.dirname(os.path.abspath(__file__))
VOID = {'br','img','hr','meta','link','input','path','rect','circle','line',
        'use','source','col','area','base','polyline','polygon','ellipse','stop'}
problems = []

def read(p):
    return io.open(p, encoding='utf-8').read()

def pages():
    return sorted(glob.glob(os.path.join(ROOT, "*.html")) +
                  glob.glob(os.path.join(ROOT, "studies", "*.html")))

def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")

print("성경연구노트 점검\n" + "=" * 52)

# 1) 링크
print("\n[1] 링크")
for p in pages():
    base = os.path.dirname(p)
    for href in re.findall(r'(?:href|src)="([^"#]+)"', read(p)):
        if href.startswith(("http", "//", "mailto:", "data:")):
            continue
        href = href.split("?", 1)[0]          # ?v= 캐시 버전은 떼고 검사
        if not href:
            continue
        if not os.path.exists(os.path.normpath(os.path.join(base, href))):
            problems.append(f"{rel(p)} → {href} (파일 없음)")
            print(f"    X {rel(p)} → {href}")
print("    깨진 링크 없음" if not problems else "")

# 2) 태그 균형
print("\n[2] 태그 균형")
for p in pages():
    stack, errs = [], []
    for m in re.finditer(r'<(/?)([a-zA-Z][\w-]*)([^>]*?)(/?)>', read(p)):
        close, tag, _, selfc = m.groups()
        tag = tag.lower()
        if tag in VOID or selfc == '/':
            continue
        if close:
            if not stack or stack[-1] != tag:
                errs.append(tag)
            else:
                stack.pop()
        else:
            stack.append(tag)
    if errs or stack:
        problems.append(f"{rel(p)} 태그 불일치: {errs or stack}")
        print(f"    X {rel(p)}: {errs or stack}")
    else:
        print(f"    OK {rel(p)}")

# 3) 자료 페이지 필수 요소
print("\n[3] 자료 페이지 메타와 주입 표시자")
for p in sorted(glob.glob(os.path.join(ROOT, "studies", "*.html"))):
    s = read(p)
    miss = []
    if not re.search(r'<meta name="description" content="[^"]{10,}"', s):
        miss.append("description")
    for k in ("study:scripture", "study:date"):
        if not re.search(r'<meta name="%s" content="[^"]+"' % k, s):
            miss.append(k)
    for mk in ("HEAD", "HEADER", "FOOTER"):
        if "<!--#%s-->" % mk not in s:
            miss.append("#" + mk + " 표시자")
    if "application/ld+json" not in s:
        miss.append("SEO 태그 미주입 — build.py 를 돌리세요")
    if miss:
        problems.append(f"{rel(p)}: {', '.join(miss)}")
        print(f"    X {rel(p)}: {', '.join(miss)}")
    else:
        print(f"    OK {rel(p)}")

# 4) 다크모드 토큰 — 미디어쿼리 밖에도 정의됐는지
print("\n[4] 다크모드 토큰")
for p in pages():
    s = read(p)
    styles = re.findall(r'<style>(.*?)</style>', s, re.S)
    for css in styles:
        used = set(re.findall(r'var\((--[\w-]+)\)', css))
        bare = re.findall(r':root\s*\{([^}]*)\}', css)
        declared = set()
        for b in bare:
            declared |= set(re.findall(r'(--[\w-]+)\s*:', b))
        local = set()
        for b in re.findall(r'\{([^}]*)\}', css):
            local |= set(re.findall(r'(--[\w-]+)\s*:', b))
        risky = (used & local) - declared
        if risky:
            problems.append(f"{rel(p)}: {sorted(risky)} 가 기본 :root 에 없음")
            print(f"    X {rel(p)}: {sorted(risky)} — 기본 :root 에도 정의하세요")
    if not styles:
        print(f"    -- {rel(p)} (페이지 전용 스타일 없음)")
    elif not any((set(re.findall(r'var\((--[\w-]+)\)', c)) &
                  {x for b in re.findall(r'\{([^}]*)\}', c)
                   for x in re.findall(r'(--[\w-]+)\s*:', b)}) -
                 {x for b in re.findall(r':root\s*\{([^}]*)\}', c)
                  for x in re.findall(r'(--[\w-]+)\s*:', b)} for c in styles):
        print(f"    OK {rel(p)}")

# 5) 설정
print("\n[5] 설정")
cfg_path = os.path.join(ROOT, "site.config.json")
if os.path.exists(cfg_path):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    if not cfg.get("site_url"):
        print("    ! site_url 이 비어 있습니다 — sitemap·feed·canonical 이 생성되지 않습니다")
    else:
        print("    OK site_url =", cfg["site_url"])
        for f in ("sitemap.xml", "feed.xml"):
            print(("    OK " if os.path.exists(os.path.join(ROOT, f)) else "    X ") + f)

# 6) 성경 인용 분량
print("\n[6] 성경 인용 분량")
BQ = re.compile(r'<blockquote[^>]*class="[^"]*bible[^"]*"[^>]*data-ref="([^"]+)"', re.S)
UNTAGGED = re.compile(r'<blockquote(?![^>]*class=)', re.S)
MAXV = 4          # 한 인용에서 이 절 수를 넘으면 경고
MAXCH = 8         # 한 페이지에서 같은 장을 이만큼 넘게 인용하면 경고

def vcount(ref):
    m = re.search(r"(\d+)\s*:\s*(\d+)(?:\s*[-\u2013~]\s*(\d+))?", ref)
    if not m:
        return 0, ""
    a = int(m.group(2)); b = int(m.group(3) or a)
    chap = re.sub(r"\s*\d+\s*:.*$", "", ref).strip() + " " + m.group(1) + "장"
    return max(1, b - a + 1), chap

any_q = False
for p_ in sorted(glob.glob(os.path.join(ROOT, "studies", "*.html"))):
    src = read(p_)
    refs = BQ.findall(src)
    plain = len(UNTAGGED.findall(src))
    per_chap = {}
    for r in refs:
        n, chap = vcount(r)
        per_chap[chap] = per_chap.get(chap, 0) + n
        if n > MAXV:
            problems.append(f"{rel(p_)}: {r} — {n}절 인용 (권장 {MAXV}절 이하)")
            print(f"    X {rel(p_)}: {r} — {n}절, 너무 깁니다")
    for chap, n in per_chap.items():
        if n > MAXCH:
            print(f"    ! {rel(p_)}: {chap}에서 합계 {n}절 — 분량을 줄이는 편이 안전합니다")
    if refs:
        any_q = True
        print(f"    OK {rel(p_)}: {len(refs)}건 · {sum(vcount(r)[0] for r in refs)}절")
    if plain:
        print(f"    ! {rel(p_)}: 표시 없는 인용블록 {plain}개 — 성경 본문이면"
              f' class="bible" data-ref="..." 를 달아 주세요')
if not any_q:
    print("    표시된 성경 인용 없음")

# ---------- [7] 이미지 출처와 라이선스 ----------
print("\n[7] 이미지 출처")
CRED = os.path.join(ROOT, "assets", "img", "출처.json")
FREE = ("public domain", "cc0", "pd-old", "pd-us", "no restrictions", "pd")
cred = {}
if not os.path.exists(CRED):
    problems.append("assets/img/출처.json 이 없습니다")
    print("    X 출처 원장이 없습니다")
else:
    try:
        cred = json.load(io.open(CRED, encoding="utf-8"))
    except Exception as e:
        problems.append("출처.json 을 읽을 수 없습니다: %s" % e)
        print("    X 출처.json 파손:", e)

# 원장 자체가 온전한가
for k, c in cred.items():
    if k.startswith("_"):
        continue
    if not os.path.exists(os.path.join(ROOT, "assets", "img", k)):
        problems.append("출처.json 에 있으나 파일이 없습니다: %s" % k)
        print("    X 파일 없음:", k)
        continue
    if c.get("분류") == "사료":
        lic = (c.get("라이선스") or "").strip().lower()
        miss = [f for f in ("제목", "라이선스", "원본페이지") if not c.get(f)]
        if miss:
            problems.append("%s: 출처 항목 누락 %s" % (k, ", ".join(miss)))
            print("    X %s — %s 가 비어 있습니다" % (k, ", ".join(miss)))
        elif not lic.startswith(FREE):
            problems.append("%s: 허용되지 않는 라이선스 '%s'" % (k, c.get("라이선스")))
            print("    X %s — 라이선스 '%s' 는 쓸 수 없습니다" % (k, c.get("라이선스")))
        else:
            print("    OK %s — %s · %s" % (k, c.get("제목"), c.get("라이선스")))
    elif c.get("분류") == "삽화":
        print("    OK %s — AI 삽화 (사료 아님을 캡션에 밝힘)" % k)
    else:
        problems.append("%s: 분류가 '사료' 나 '삽화' 가 아닙니다" % k)
        print("    X %s — 분류 없음" % k)

# 페이지가 쓰는 이미지가 모두 원장에 있는가
used = set()
for p_ in pages():
    for m in re.finditer(r'assets/img/([^"\'?\s>]+)', read(p_)):
        used.add(m.group(1))
for u in sorted(used):
    if u not in cred:
        problems.append("원장에 없는 이미지를 쓰고 있습니다: %s" % u)
        print("    X 원장 미등록:", u)

# 사료 도판이 출처 없이 붙어 있지 않은가
for p_ in pages():
    src = read(p_)
    for m in re.finditer(r'<!--#PLATE:([^>]*?)-->(.*?)<!--/#PLATE-->', src, re.S):
        fn = m.group(1).split("|")[0].strip()
        body = m.group(2)
        c = cred.get(fn, {})
        if c.get("분류") == "사료" and "plate-src" not in body:
            problems.append("%s: %s 도판에 출처 표기가 렌더링되지 않았습니다" % (rel(p_), fn))
            print("    X %s — %s 출처 미표기 (build.py 를 먼저 돌리세요)" % (rel(p_), fn))


# ---------- [8] 문체 통일 ----------
# 규약: 자료 페이지 본문은 해요체. 「근거 자료」 절과 푸터만 합니다체.
# 자세한 규정은 작업규약.md 의 「문체」 절.
print("\n[8] 문체")

HAEYO = re.compile(r'(어요|에요|예요|아요|해요|세요|네요|잖아요|거든요|죠)[.!?]')
HAPNIDA = re.compile(r'(습니다|입니다|ㅂ니다)[.!?]')

def body_text(src):
    """머리·스타일·스크립트·푸터·「근거 자료」 절을 뺀 본문만 남긴다."""
    src = re.sub(r'(?s)<head.*?</head>', ' ', src)
    src = re.sub(r'(?s)<script.*?</script>', ' ', src)
    src = re.sub(r'(?s)<style.*?</style>', ' ', src)
    src = re.sub(r'(?s)<footer.*?</footer>', ' ', src)
    # 히어로 밴드의 AI 삽화 고정 문구는 build.py 가 넣는 것이라 검사 대상이 아니다
    src = re.sub(r'(?s)<figure class="hero-band">.*?</figure>', ' ', src)
    # 근거 자료 / 참고 자료 / 참고 문헌 절은 합니다체 허용 — 통째로 제외
    src = re.sub(r'(?s)<section>\s*<h2>\s*(근거 자료|참고 자료|참고 문헌)\s*</h2>.*?</section>', ' ', src)
    return re.sub(r'<[^>]*>', ' ', src)

for p_ in pages():
    # 검사 대상은 자료 페이지(studies/)뿐. 홈·404·소개는 제외한다.
    if os.sep + "studies" + os.sep not in p_:
        continue
    t = body_text(read(p_))
    hy, hp = len(HAEYO.findall(t)), len(HAPNIDA.findall(t))
    if hy + hp == 0:
        print("    -- %s (검사할 문장 없음)" % rel(p_))
    elif hp == 0:
        print("    OK %s — 해요체 %d문장" % (rel(p_), hy))
    elif hy == 0:
        problems.append("%s: 본문이 합니다체입니다 (규약은 해요체)" % rel(p_))
        print("    X %s — 합니다체 %d문장. 작업규약.md 「문체」 절을 보세요" % (rel(p_), hp))
    else:
        problems.append("%s: 해요체와 합니다체가 섞였습니다 (해요 %d / 합니다 %d)" % (rel(p_), hy, hp))
        print("    X %s — 어미 혼용: 해요체 %d · 합니다체 %d" % (rel(p_), hy, hp))


# ---------- [9] 줄바꿈 (권고) ----------
# word-break:keep-all 은 어절만 지키고 text-wrap:balance 는 의미 단위를 모른다.
# 관형어+의존명사("추론한 것"), 수+단위("26 회")가 줄 첫머리에서 갈라지면 읽기가 끊긴다.
# 제목·짧은 표시 문구에서만 본다. 배포를 막지는 않고 알려만 준다.
print("\n[9] 줄바꿈 (권고 — 배포를 막지 않습니다)")

DEPENDENT = "것 수 줄 리 바 때 데 뿐 지 채 터 만큼 대로".split()
UNITS = "회 편 절 장 일 년 개 명 번 시간 km m".split()
DISPLAY = re.compile(
    r'<(h1|h2|h3|caption|figcaption|summary|dt)[^>]*>(.*?)</\1>'
    r'|<(p|div)[^>]*class="(?:lede|sub|stamp)"[^>]*>(.*?)</\3>', re.S)

def jong(ch):
    """한글 음절의 받침 번호. ㄴ=4, ㄹ=8."""
    o = ord(ch) - 0xAC00
    return (o % 28) if 0 <= o < 11172 else -1

def loose_pairs(text):
    out, w = [], text.split(" ")
    for i in range(len(w) - 1):
        a, b = w[i], w[i + 1]
        if not a or not b:
            continue
        head = b[0]
        two = b[:2]
        # 의존명사 뒤에는 조사·접미사·문장부호만 와야 한다.
        # 그래야 "지역마다"(= '지'로 시작하는 보통명사) 같은 오탐을 거른다.
        TAIL = set("이가을를은는와과의도로만에서부터까지처럼들뿐이나라며야여요·,.?!)\u201d\u2019\u300d\u300f")
        tail_ok = len(b) == 1 or all(c in TAIL for c in b[1:])
        if (head in DEPENDENT or two in ("만큼", "대로")) and tail_ok and jong(a[-1]) in (4, 8):
            out.append("%s %s" % (a, b))
        elif a[-1].isdigit() and (head in UNITS or two in ("시간", "km")):
            out.append("%s %s" % (a, b))
    return out

flagged = 0
for p_ in pages():
    src = read(p_)
    src = re.sub(r'(?s)<head.*?</head>', ' ', src)
    src = re.sub(r'(?s)<script.*?</script>', ' ', src)
    for m in DISPLAY.finditer(src):
        inner = m.group(2) if m.group(2) is not None else m.group(4)
        if inner is None:
            continue
        # 이미 묶어 둔 것은 검사에서 뺀다 (span 이든 b 든 class 에 nb 가 있으면)
        inner = re.sub(r'(?s)<(\w+)[^>]*class="[^"]*\bnb\b[^"]*"[^>]*>.*?</\1>', "\u3007", inner)
        txt = " ".join(re.sub(r'<[^>]*>', " ", inner).replace("\u00a0", "\u3007").split())
        if len(txt) > 90:
            continue
        for pair in loose_pairs(txt):
            flagged += 1
            print('    !  %s — 「%s」 이 갈라질 수 있습니다' % (rel(p_), pair))
            print('       <span class="nb">%s</span> 로 묶으세요' % pair)
if not flagged:
    print("    OK 묶여야 할 짝이 모두 묶여 있습니다")


print("\n" + "=" * 52)
if problems:
    print("문제 %d건" % len(problems))
    sys.exit(1)
print("모두 통과")
