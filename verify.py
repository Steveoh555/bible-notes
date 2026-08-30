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

print("\n" + "=" * 52)
if problems:
    print("문제 %d건" % len(problems))
    sys.exit(1)
print("모두 통과")
