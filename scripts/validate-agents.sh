#!/usr/bin/env bash
# 全エージェントの frontmatter に model が明示されているか検証する。
# 使い方: scripts/validate-agents.sh [検索ルート(省略時はリポジトリルート)]
set -u

root="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
status=0
count=0

while IFS= read -r file; do
  count=$((count + 1))
  # 先頭の frontmatter(--- から次の ---)内に model: があるか
  if ! awk '
    NR==1 { if ($0 != "---") exit 1; next }
    $0 == "---" { exit found ? 0 : 1 }
    /^model:[[:space:]]*[^[:space:]]+/ { found=1 }
    END { if (!found) exit 1 }
  ' "$file"; then
    echo "NG: model が未指定: $file" >&2
    status=1
  fi
done < <(find "$root" -type f -path '*/agents/*.md' -not -path '*/node_modules/*')

if [ "$status" -eq 0 ]; then
  echo "OK: ${count} 件のエージェントすべてに model が指定されています"
fi
exit "$status"
