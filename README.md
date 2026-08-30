# 성경연구노트 — 사이트 폴더

성경 배경 연구 자료를 **HTML 페이지 그대로** 모아 공개하는 정적 사이트입니다.
서버도, 데이터베이스도, 월 이용료도 없습니다. 파일이 곧 사이트입니다.

## 폴더 구조

```
site/
├── index.html          홈 (자동 생성 — 직접 고치지 마세요)
├── about.html          소개
├── studies/            ← 자료 페이지가 쌓이는 곳
│   └── bethlehem-rulers.html
├── assets/
│   ├── site.css        공통 디자인. 색·글꼴은 맨 위 :root 만 고치면 전체가 바뀝니다
│   └── site.js         테마 전환 + 홈 검색
├── build.py            자동화 스크립트
├── site.config.json    사이트 이름·주소·글쓴이
├── sitemap.xml         자동 생성 (검색엔진용)
├── feed.xml            자동 생성 (RSS)
└── robots.txt
```

## 자료 한 편이 올라가는 과정

Claude가 대화창에서 전부 처리합니다. 직접 하실 일은 없습니다.

1. 연구 → `studies/<제목>.html` 작성
2. `./publish.sh "커밋 메시지"` — 빌드 · 점검 · 커밋 · 푸시가 한 번에
3. 몇 분 뒤 사이트에 반영

`publish.sh` 는 점검(`verify.py`)에 실패하면 배포를 중단합니다.
따로 돌리고 싶으면 `python3 build.py`, `python3 verify.py` 를 쓰면 됩니다.

## 자료 페이지가 지켜야 할 두 가지

**하나 — `<head>` 안에 자기 정보를 적습니다.** 홈 카드와 검색 결과가 여기서 나옵니다.

```html
<title>제목 — 성경연구노트</title>
<meta name="description" content="한 문장 요약. 검색 결과에 그대로 보입니다.">
<meta name="study:scripture" content="누가복음 2:1–7">
<meta name="study:tags" content="연대기, 로마사">
<meta name="study:date" content="2026-08-27">
<meta name="study:updated" content="2026-08-27">
<meta name="study:draft" content="true">   <!-- 있으면 목록에서 숨겨집니다 -->
```

**둘 — 세 개의 표시자를 그대로 둡니다.** `build.py`가 이 자리를 채웁니다.

```html
<!--#HEAD--><!--/#HEAD-->        (</head> 바로 위)
<!--#HEADER--><!--/#HEADER-->    (<body> 바로 아래)
<!--#FOOTER--><!--/#FOOTER-->    (</body> 바로 위)
```

새 페이지 뼈대는 이렇게 만들 수 있습니다.

```bash
python3 build.py new luke2-census "구레뇨 호적은 언제인가"
```

## 미리보기

```bash
python3 -m http.server 8000
```
브라우저에서 `http://localhost:8000` 을 엽니다.
(파일을 그냥 더블클릭해도 열리지만, 링크 경로는 서버로 봐야 정확합니다.)

## 공개 준비 — 한 번만 하면 되는 일 (아직 안 됨)

1. GitHub에서 저장소를 만듭니다 (공개 / Public).
2. `site.config.json` 의 `site_url` 에 사이트 주소를 적습니다.
   예: `https://아이디.github.io/저장소이름`
3. 저장소 **Settings → Pages** 에서 Source 를 `main` 브랜치 `/ (root)` 로 지정합니다.
4. 검색 등록 — 구글 [Search Console](https://search.google.com/search-console) 과
   네이버 [서치어드바이저](https://searchadvisor.naver.com) 양쪽에 사이트를 등록하고
   `sitemap.xml` 을 제출합니다. 네이버는 `Yeti` 로봇을 허용해 두었습니다.

## 성경 본문 인용에 대하여

대한성서공회 안내에 따르면 **개역한글판(1961)** 은 저작재산권 보호기간 50년이 지나
저작권료 없이 사용할 수 있습니다(성명표시권·동일성유지권은 준수).
**개역개정판(1998)** 은 저작권이 살아 있으므로, 본문을 길게 싣는 페이지는
개역한글로 바꾸거나 성서공회 저작권부(02-2103-8730)에 문의하시는 편이 안전합니다.
원문(히브리어·헬라어) + 사역(私譯) 방식은 이 문제에서 자유롭습니다.
