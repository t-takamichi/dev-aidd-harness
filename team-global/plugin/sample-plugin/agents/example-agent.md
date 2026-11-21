---
name: example-agent
description: 雛形エージェント。委譲すべきタスクの条件をここに書く。
model: sonnet
tools: Read, Grep, Glob
---

あなたは（役割）を担当するエージェントです。

## 方針

- （ここに振る舞いを書く）
- 作業前に `${CLAUDE_PLUGIN_ROOT}/rules/` 配下の関連ルールを確認する（モデル指定は `${CLAUDE_PLUGIN_ROOT}/rules/agent-model.md`）。
