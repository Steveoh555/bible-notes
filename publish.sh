#!/usr/bin/env bash
# 성경연구노트 — 빌드 → 점검 → 커밋 → 푸시를 한 번에
#   사용법: ./publish.sh "커밋 메시지"
set -uo pipefail
cd "$(dirname "$0")"

# 이 폴더는 원격 연결(기기 브리지)을 통해 다뤄지는데, 거기서는 git 이 자기 임시 파일을
# 지우지 못한다. 남은 .lock 이 다음 git 명령을 막으므로 매 단계 앞에서 치워 준다.
unlock() {
  mkdir -p .git/_junk 2>/dev/null
  while IFS= read -r f; do
    [ -n "$f" ] && mv "$f" ".git/_junk/$(basename "$f").$$.$RANDOM" 2>/dev/null
  done < <(find .git -name '*.lock' -not -path '*/_junk/*' 2>/dev/null)
  while IFS= read -r f; do
    [ -n "$f" ] && mv "$f" ".git/_junk/$(basename "$f").$$.$RANDOM" 2>/dev/null
  done < <(find .git -name 'tmp_obj_*' -not -path '*/_junk/*' 2>/dev/null)
}
quiet() { grep -viE 'unable to unlink|^warning: ' || true; }

MSG="${1:-사이트 갱신}"

echo "[1/4] 빌드"
python3 build.py || { echo "  빌드 실패 — 중단"; exit 1; }

echo
echo "[2/4] 점검"
if ! python3 verify.py; then
  echo
  echo "  점검에서 문제가 나왔습니다. 고치고 다시 실행하세요. 배포하지 않았습니다."
  exit 1
fi

echo
echo "[3/4] 커밋"
unlock
git add -A 2>&1 | quiet
unlock
if git diff --cached --quiet 2>/dev/null; then
  echo "  바뀐 것이 없습니다."
else
  git commit -q -m "$MSG" 2>&1 | quiet
  unlock
  echo "  $(git log --oneline -1)"
fi

echo
echo "[4/4] 푸시"
if [ -z "$(git remote 2>/dev/null)" ]; then
  echo "  원격 저장소가 없습니다. 아직 배포 설정 전입니다."
  echo "  git remote add origin https://github.com/<아이디>/<저장소>.git"
  exit 0
fi
if [ ! -s .git/.git-credentials ]; then
  echo "  인증 파일이 없습니다 (.git/.git-credentials)."
  echo "  GitHub 토큰을 site/github-token.txt 에 저장해 주시면 설정합니다."
  exit 0
fi
# 이 폴더의 절대경로는 세션마다 바뀐다. 저장된 credential.helper 가 옛 세션 경로를
# 가리키면 git 이 자격 증명을 못 읽어 "could not read Username" 으로 실패한다.
# 매번 현재 경로로 다시 맞춘다.
git config --local credential.helper "store --file=$PWD/.git/.git-credentials"
# 프록시 자격 증명이 중복 누적되므로 같은 줄은 하나만 남긴다.
awk '!seen[$0]++' .git/.git-credentials > .git/_cred.tmp 2>/dev/null \
  && cat .git/_cred.tmp > .git/.git-credentials && : > .git/_cred.tmp

unlock
BR="$(git branch --show-current)"
if git rev-parse --abbrev-ref "@{upstream}" >/dev/null 2>&1; then
  OUT="$(git push 2>&1)"
else
  OUT="$(git push -u origin "$BR" 2>&1)"
fi
unlock
if echo "$OUT" | grep -qiE 'error|fatal|rejected|denied'; then
  echo "$OUT" | quiet | head -6
  echo "  푸시 실패."
  exit 1
fi
echo "$OUT" | quiet | grep -viE '^remote:|^To |^ \*|^Enumerating|^Counting|^Compressing|^Writing|^Total|^delta' | head -3
echo "  올렸습니다 → https://steveoh555.github.io/bible-notes"
echo "  GitHub Pages 반영까지 1~3분 걸립니다."
