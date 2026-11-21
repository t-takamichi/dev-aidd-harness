#!/usr/bin/env python3
"""タスク一覧(README.md)とタスク詳細(task.md)の整合を検証する。

使い方: validate-tasks.py <プロジェクトDir または _work/draft>
検証: ID の一意・形式 / ディレクトリ名 {ID}-{slug} / 孤立ディレクトリ / リンク先の存在 /
      詳細の見出し ID / 依存先の存在・循環・順序・廃止タスクへの依存 /
      要件インベントリ(requirements.md)の網羅と主担当の一意
"""
import re
import sys
from pathlib import Path

ID_RE = re.compile(r"^T\d{2,3}$")
DIR_RE = re.compile(r"^(T\d{2,3})-[a-z0-9]+(-[a-z0-9]+)*$")
REQ_RE = re.compile(r"R-\d{3,}")
errors = []


def ng(msg):
    errors.append(msg)


def read(path):
    return path.read_text(encoding="utf-8-sig")


def split_row(line):
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [c.replace("\\|", "|").strip() for c in cells]


def is_sep(line):
    return bool(line.strip()) and set(line.strip()) <= set("|-: ")


def section_table(text, heading):
    """`## {heading}` 見出し直下の最初の表を (ヘッダ, 行リスト) で返す。なければ None。"""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if re.match(rf"^##\s+{re.escape(heading)}\s*$", l)), None)
    if start is None:
        return None
    header, rows = None, []
    for line in lines[start + 1:]:
        s = line.strip()
        if re.match(r"^#{1,6}\s", s):
            break
        if not s.startswith("|"):
            if header:
                break
            continue
        if is_sep(s):
            continue
        cells = split_row(s)
        if header is None:
            header = cells
        else:
            rows.append(cells)
    return (header, rows) if header else None


def col(header, name):
    return header.index(name) if name in header else None


def find_cycle(deps):
    state = {}

    def visit(n, path):
        state[n] = 1
        for d in deps.get(n, []):
            if state.get(d) == 1:
                return path + [n, d]
            if d not in state:
                c = visit(d, path + [n])
                if c:
                    return c
        state[n] = 2
        return None

    for n in deps:
        if n not in state:
            c = visit(n, [])
            if c:
                return c
    return None


def requirement_ids(base):
    for p in (base / "requirements.md", base.parent / "requirements.md", base.parent.parent / "requirements.md"):
        if p.exists():
            ids = set()
            for line in read(p).splitlines():
                m = re.match(r"^\|\s*\**(R-\d{3,})\**\s*\|", line)
                if m and "廃止" not in line:
                    ids.add(m.group(1))
            return p, ids
    return None, set()


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    base = Path(sys.argv[1]).resolve()
    readme = base / "README.md"
    if not readme.exists():
        raise SystemExit(f"NG: README.md がありません: {base}")

    table = section_table(read(readme), "タスク")
    if not table:
        raise SystemExit("NG: `## タスク` 直下にタスク表がありません")
    header, rows = table
    idx = {n: col(header, n) for n in ("ID", "依存", "詳細", "状態")}
    for n in ("ID", "依存", "詳細"):
        if idx[n] is None:
            raise SystemExit(f"NG: タスク表に必須列がありません: {n}")

    def cell(r, n):
        i = idx[n]
        return r[i] if i is not None and i < len(r) else ""

    ids = [cell(r, "ID") for r in rows]
    status = {cell(r, "ID"): (cell(r, "状態") or "active") for r in rows}
    for i in sorted(set(ids)):
        if ids.count(i) > 1:
            ng(f"ID が重複: {i}")

    deps, listed_dirs = {}, set()
    seen_above = set()
    primary = {}
    for r in rows:
        tid = cell(r, "ID")
        if not ID_RE.match(tid):
            ng(f"ID の形式が不正: {tid!r}")
            continue
        active = status[tid] != "廃止"
        link = re.search(r"\]\(<?([^)>]+)>?\)", cell(r, "詳細"))
        if active and not link:
            ng(f"{tid}: 詳細リンクがありません")
        if link:
            rel = Path(link.group(1))
            detail = (base / rel).resolve()
            try:
                detail.relative_to(base)
            except ValueError:
                ng(f"{tid}: リンク先が対象ディレクトリの外です: {rel}")
                continue
            listed_dirs.add(rel.parent.name)
            m = DIR_RE.match(rel.parent.name)
            if not m or m.group(1) != tid:
                ng(f"{tid}: ディレクトリ名が {tid}-{{slug}}（英小文字・数字・ハイフン）ではありません: {rel.parent}")
            if rel.name != "task.md":
                ng(f"{tid}: リンク先が task.md ではありません: {rel}")
            if not detail.exists():
                if active:
                    ng(f"{tid}: リンク先が存在しません: {rel}")
            else:
                text = read(detail)
                h = re.search(r"^#\s+(T\d+)\b", text, re.M)
                if not h or h.group(1) != tid:
                    ng(f"{tid}: 詳細の見出し ID が一致しません: {rel}")
                req = section_table(text, "要件")
                if active and req:
                    rh, rr = req
                    kind = col(rh, "区分")
                    for row in rr:
                        m2 = re.match(r"\**(R-\d{3,})\**$", row[0]) if row else None
                        if not m2:
                            continue
                        if kind is not None and kind < len(row) and row[kind] == "参照":
                            continue
                        primary.setdefault(m2.group(1), []).append(tid)
        raw = cell(r, "依存")
        deps[tid] = [] if raw in ("", "-") else re.findall(r"T\d{2,3}", raw)
        for d in deps[tid]:
            if d not in ids:
                ng(f"{tid}: 依存先が存在しません: {d}")
            elif status.get(d) == "廃止" and active:
                ng(f"{tid}: 廃止タスクに依存しています: {d}")
            elif d not in seen_above and d != tid:
                ng(f"{tid}: 依存先 {d} が下の行にあります（依存先が上に来る順に並べる）")
        seen_above.add(tid)

    cycle = find_cycle({k: [d for d in v if d in ids] for k, v in deps.items()})
    if cycle:
        ng("依存が循環: " + " -> ".join(cycle))

    for d in sorted(p.name for p in base.iterdir() if p.is_dir() and re.match(r"^T\d", p.name)):
        if d not in listed_dirs:
            ng(f"一覧にないディレクトリがあります: {d}")

    req_path, req_ids = requirement_ids(base)
    if req_path is None:
        ng("requirements.md が見つかりません（要件の網羅を検証できない）")
    else:
        for r in sorted(req_ids - set(primary)):
            ng(f"要件がどのタスクにも主担当で割り当てられていません: {r}")
        for r, ts in sorted(primary.items()):
            if len(ts) > 1:
                ng(f"要件の主担当が複数タスクにあります: {r} -> {', '.join(ts)}")
            if r not in req_ids:
                ng(f"要件インベントリにない ID です: {r}")

    if errors:
        for e in errors:
            print(f"NG: {e}", file=sys.stderr)
        raise SystemExit(1)
    print(f"OK: {len(rows)} 件のタスクを検証しました")


if __name__ == "__main__":
    main()
