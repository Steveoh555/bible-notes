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


print("\n" + "=" * 52)
if problems:
    print("문제 %d건" % len(problems))
    sys.exit(1)
print("모두 통과")
