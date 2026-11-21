#!/usr/bin/env python3
"""各プラグインの skills/*/SKILL.md から CATALOG.md を生成する。

使い方:
  scripts/generate-catalog.py           # CATALOG.md を更新
  scripts/generate-catalog.py --check   # 最新でなければ非0で終了（CI用）
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise SystemExit(f"NG: frontmatter がありません: {path}")
    fields = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep:
            fields[k.strip()] = v.strip()
    return fields


def render(plugin_dir):
    rows = []
    for skill_md in sorted((plugin_dir / "skills").glob("*/SKILL.md")):
        fm = frontmatter(skill_md)
        name, desc = fm.get("name"), fm.get("description")
        if not name or not desc:
            raise SystemExit(f"NG: name / description が未指定: {skill_md}")
        if name != skill_md.parent.name:
            raise SystemExit(f"NG: name とディレクトリ名が不一致: {skill_md}")
        rows.append((name, desc.replace("|", "\\|")))
    lines = [
        f"# {plugin_dir.name} スキルカタログ",
        "",
        "<!-- scripts/generate-catalog.py で自動生成。直接編集しない。 -->",
        "",
        "| スキル | 説明 |",
        "|---|---|",
    ]
    lines += [f"| [{n}](skills/{n}/SKILL.md) | {d} |" for n, d in rows]
    return "\n".join(lines) + "\n"


def main():
    check = "--check" in sys.argv[1:]
    status = 0
    for manifest in sorted(ROOT.glob("*/plugin/*/.claude-plugin/plugin.json")):
        plugin_dir = manifest.parent.parent
        out = plugin_dir / "CATALOG.md"
        content = render(plugin_dir)
        if check:
            if not out.exists() or out.read_text(encoding="utf-8") != content:
                print(f"NG: CATALOG.md が最新ではありません: {out}", file=sys.stderr)
                status = 1
        else:
            out.write_text(content, encoding="utf-8")
            print(f"生成: {out.relative_to(ROOT)}")
    if check and status == 0:
        print("OK: CATALOG.md は最新です")
    sys.exit(status)


main()
