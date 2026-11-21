#!/usr/bin/env python3
"""プラグインの skills / agents / rules を Codex・agy (Antigravity) 向けに変換する。

使い方:
  scripts/convert-harness.py <プラグインDir> --target codex|agy --out <配置先プロジェクト>
  scripts/convert-harness.py <プラグインDir> --target codex --out ~ --user   # ユーザー全体へ配置

出力:
  codex: <out>/.agents/skills/<skill>/   スキル（そのままコピー）
         <out>/.codex/agents/<name>.toml エージェント
         <out>/AGENTS.md                 rules を MARKER 区間に埋め込む（区間外は保持）
  agy  : <out>/.agents/skills/<skill>/
         <out>/.agents/agents/<name>.md
         <out>/.agents/rules/<name>.md   frontmatter(trigger) 付き

  --user を付けると配置先をユーザー全体にする（codex: ~/.agents/skills, ~/.codex/agents,
  ~/.codex/AGENTS.md / agy: ~/.gemini/config/{skills,agents,rules}）。

変換の前提（公式ドキュメントに基づくが実機未検証。README の対応状況を参照）:
  - Codex のエージェントはツール許可リストも sandbox_mode も持てないため、
    読み取り専用のエージェントは developer_instructions に制約を追記する。
  - agy の tools は実機で確認した名前だけを出力する（Grep / Glob は対応なしで省略し警告）。
  - Claude のモデル名は Codex には対応先がないため省略（親を継承）。agy は flash / pro に対応づける。
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

PLUGIN_ROOT_VAR = "${CLAUDE_PLUGIN_ROOT}"
MARKER_BEGIN = "<!-- BEGIN dev-aidd-harness:{plugin} -->"
MARKER_END = "<!-- END dev-aidd-harness:{plugin} -->"

# Claude Code のツール名 -> agy のツール名（agy 1.5.12 の実機で確認した名前。
# 公式ドキュメントの view_file / grep_search / replace_file_content は実機では使えなかった。
# grep / glob に相当するツールは無いため Grep・Glob は対応なし）
AGY_TOOLS = {
    "Read": "read_file",
    "Write": "write_file",
    "Edit": "edit_file",
    "Bash": "run_command",
}
AGY_MODELS = {"sonnet": "flash", "haiku": "flash", "opus": "pro", "inherit": "inherit"}
WRITE_TOOLS = {"Write", "Edit", "Bash"}


def warn(msg):
    print(f"WARN: {msg}", file=sys.stderr)


def split_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        return {}, text
    fields = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep:
            fields[k.strip()] = v.strip()
    return fields, m.group(2).lstrip("\n")


def rewrite_refs(text, target):
    """${CLAUDE_PLUGIN_ROOT}/rules/ を変換先で解決できる表現に置き換える。"""
    rules_ref = ".agents/rules/" if target == "agy" else "AGENTS.md の rules 節 "
    text = text.replace(f"{PLUGIN_ROOT_VAR}/rules/", rules_ref)
    if PLUGIN_ROOT_VAR in text:
        warn(f"{PLUGIN_ROOT_VAR} が残っています（rules 以外の参照は変換できません）")
    return text


def tools_of(fm):
    return [t.strip() for t in fm.get("tools", "").split(",") if t.strip()]


def toml_str(s):
    return '"""\n' + s.replace("\\", "\\\\").replace('"""', '\\"\\"\\"').rstrip() + '\n"""'


def toml_basic(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def convert_agent_codex(src):
    fm, body = split_frontmatter(src)
    name, desc = fm.get("name"), fm.get("description")
    if not name or not desc:
        raise SystemExit(f"NG: name / description が未指定: {src}")
    body = rewrite_refs(body, "codex")
    tools = tools_of(fm)
    if tools and not WRITE_TOOLS & set(tools):
        body = "ファイルを変更しない（読み取り専用）。\n\n" + body
    if fm.get("model") not in (None, "inherit"):
        warn(f"{src.name}: model={fm['model']} は Codex に対応先がないため省略（親を継承）")
    return (
        f"name = {toml_basic(name)}\n"
        f"description = {toml_basic(desc)}\n"
        f"developer_instructions = {toml_str(body)}\n"
    )


def convert_agent_agy(src):
    fm, body = split_frontmatter(src)
    name, desc = fm.get("name"), fm.get("description")
    if not name or not desc:
        raise SystemExit(f"NG: name / description が未指定: {src}")
    out = ["---", f"name: {name}", f"description: {desc}"]
    mapped = []
    for t in tools_of(fm):
        if t in AGY_TOOLS:
            if AGY_TOOLS[t] not in mapped:
                mapped.append(AGY_TOOLS[t])
        else:
            warn(f"{src.name}: ツール {t} は agy に対応するツールがないため省略")
    if mapped:
        out.append("tools:")
        out += [f"  - {t}" for t in mapped]
    out += ["mainAgent: false", "subagent: true"]
    model = fm.get("model")
    if model:
        if model in AGY_MODELS:
            out.append(f"model: {AGY_MODELS[model]}")
        else:
            warn(f"{src.name}: model={model} は agy に対応先がないため inherit にする")
            out.append("model: inherit")
    out += ["---", "", rewrite_refs(body, "agy").rstrip(), ""]
    return "\n".join(out)


def rule_files(plugin):
    return sorted(p for p in (plugin / "rules").glob("*.md") if p.name != "README.md")


def rule_description(src):
    fm, body = split_frontmatter(src)
    if fm.get("description"):
        return fm["description"]
    m = re.search(r"^#\s+(.+)$", body, re.M)
    return m.group(1).strip() if m else src.stem


def convert_rule_agy(src):
    fm, body = split_frontmatter(src)
    desc = rule_description(src).replace('"', '\\"')
    trigger = fm.get("trigger", "model_decision")
    return f'---\ntrigger: {trigger}\ndescription: "{desc}"\n---\n\n{rewrite_refs(body, "agy").rstrip()}\n'


def render_agents_md_block(plugin):
    parts = [MARKER_BEGIN.format(plugin=plugin.name), f"## rules ({plugin.name})", ""]
    for src in rule_files(plugin):
        _, body = split_frontmatter(src)
        # 見出しを1段下げて AGENTS.md の階層に収める
        body = re.sub(r"^(#+) ", r"#\1 ", rewrite_refs(body, "codex"), flags=re.M)
        parts += [f"<!-- rule: {src.stem} -->", body.rstrip(), ""]
    parts.append(MARKER_END.format(plugin=plugin.name))
    return "\n".join(parts) + "\n"


def merge_marked(path, block, plugin):
    begin, end = MARKER_BEGIN.format(plugin=plugin.name), MARKER_END.format(plugin=plugin.name)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    pat = re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"\n?", re.S)
    if pat.search(existing):
        # 置換文字列としてではなくリテラルとして差し込む（バックスラッシュ対策）
        return pat.sub(lambda _: block, existing)
    return existing + ("\n" if existing and not existing.endswith("\n\n") else "") + block


def copy_skills(plugin, dest, target):
    count = 0
    for skill in sorted(p for p in (plugin / "skills").iterdir() if p.is_dir()):
        out = dest / skill.name
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(skill, out)
        for md in out.rglob("*.md"):
            md.write_text(rewrite_refs(md.read_text(encoding="utf-8"), target), encoding="utf-8")
        count += 1
    return count


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("plugin", type=Path)
    ap.add_argument("--target", required=True, choices=["codex", "agy"])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--user", action="store_true", help="ユーザー全体の配置先に出力する")
    args = ap.parse_args()

    plugin = args.plugin.resolve()
    out = args.out.expanduser().resolve()
    if not (plugin / ".claude-plugin" / "plugin.json").exists():
        raise SystemExit(f"NG: プラグインではありません: {plugin}")

    if args.target == "codex":
        skills_dir = out / ".agents" / "skills"
        agents_dir = out / ".codex" / "agents"
        agents_md = (out / ".codex" / "AGENTS.md") if args.user else (out / "AGENTS.md")
    else:
        base = out / ".gemini" / "config" if args.user else out / ".agents"
        skills_dir, agents_dir, rules_dir = base / "skills", base / "agents", base / "rules"

    n_skills = copy_skills(plugin, skills_dir, args.target) if (plugin / "skills").is_dir() else 0

    n_agents = 0
    for src in sorted((plugin / "agents").glob("*.md")) if (plugin / "agents").is_dir() else []:
        agents_dir.mkdir(parents=True, exist_ok=True)
        if args.target == "codex":
            (agents_dir / f"{src.stem}.toml").write_text(convert_agent_codex(src), encoding="utf-8")
        else:
            (agents_dir / src.name).write_text(convert_agent_agy(src), encoding="utf-8")
        n_agents += 1

    n_rules = len(rule_files(plugin)) if (plugin / "rules").is_dir() else 0
    if n_rules:
        if args.target == "codex":
            agents_md.parent.mkdir(parents=True, exist_ok=True)
            agents_md.write_text(merge_marked(agents_md, render_agents_md_block(plugin), plugin), encoding="utf-8")
        else:
            rules_dir.mkdir(parents=True, exist_ok=True)
            for src in rule_files(plugin):
                (rules_dir / src.name).write_text(convert_rule_agy(src), encoding="utf-8")

    print(f"OK: {args.target} 向けに変換 skills={n_skills} agents={n_agents} rules={n_rules} -> {out}")


if __name__ == "__main__":
    main()
