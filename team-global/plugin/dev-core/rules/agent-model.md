---
description: エージェントを追加・変更するとき、frontmatter の model の指定ルールを確認する
---

# agent-model

## ルール

`agents/` 配下の全エージェントは、frontmatter に `model` を必ず明示する。省略しない。

## 指定できる値

`sonnet` / `opus` / `haiku` / `inherit` / 完全なモデルID（例：`claude-sonnet-5-5`）

## 選び方の目安

| 用途 | model |
|------|-------|
| 設計・レビューなど深い推論が必要 | `opus` |
| 実装・一般的な作業 | `sonnet` |
| 検索・要約など軽量で高速さが必要 | `haiku` |
| 呼び出し元に合わせたい | `inherit`（理由をエージェント本文に書く） |

## 例

```yaml
---
name: example-agent
description: ...
model: sonnet
tools: Read, Grep, Glob
---
```

## 確認

エージェントを追加・変更したときは、次を実行して frontmatter に `model` があることを確認する。

```
scripts/validate-agents.sh
```

未指定があると非0で終了する。CI でも同じスクリプトを実行する。
