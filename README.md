# dev-aidd-harness

開発プロセスにAI用ハーネス（skills / agents / rules）を配置するためのプラグイン集です。

## プラグイン一覧

| プラグイン | 説明 | カタログ |
| --- | --- | --- |
| `dev-core` | 開発プロセス用ハーネスの雛形プラグイン | [CATALOG.md](team-global/plugin/dev-core/CATALOG.md) |

## インストール方法

Claude Code 上で、このリポジトリをマーケットプレイスとして追加し、プラグインをインストールします。

```
/plugin marketplace add t-takamichi/dev-aidd-harness
/plugin install dev-core@dev-aidd-harness
```

SSH で clone 済みの場合は Git URL でも追加できます。

```
/plugin marketplace add git@github.com:t-takamichi/dev-aidd-harness.git
```

### ローカルのクローンから使う

```
git clone git@github.com:t-takamichi/dev-aidd-harness.git
```

```
/plugin marketplace add ./dev-aidd-harness
/plugin install dev-core@dev-aidd-harness
```

### 更新

```
/plugin marketplace update dev-aidd-harness
```

## 他のツールで使う（Codex / agy）

`scripts/convert-harness.py` で skills / agents / rules を Codex・agy 向けに変換して配置します（Python 3.9 以上、標準ライブラリのみ）。

```
git clone git@github.com:t-takamichi/dev-aidd-harness.git
cd dev-aidd-harness

# プロジェクトに配置
scripts/convert-harness.py team-global/plugin/dev-core --target codex --out /path/to/project
scripts/convert-harness.py team-global/plugin/dev-core --target agy   --out /path/to/project

# ユーザー全体に配置
scripts/convert-harness.py team-global/plugin/dev-core --target codex --out ~ --user
scripts/convert-harness.py team-global/plugin/dev-core --target agy   --out ~ --user
```

再実行すると上書き更新されます。Codex の `AGENTS.md` は `BEGIN/END dev-aidd-harness` の区間だけを置き換え、区間外は保持します。agy は実行中に追加した場合 `/skills reload` が必要です。

### `agy plugin install` について

`agy plugin install ./team-global/plugin/dev-core` でも Claude Code 形式のプラグインを取り込めますが、agy 1.5.12 では **skills しか使えません**。agents は Claude 形式のままコピーされるだけでサブエージェントとして登録されず（`not found`）、rules も `trigger` が無いため読み込まれません。agents と rules も使うには、上の変換スクリプトを使ってください。

### 変換内容

| 種別 | Codex | agy |
| --- | --- | --- |
| skills | `.agents/skills/` にコピー | `.agents/skills/` にコピー（`--user` は `~/.gemini/config/skills/`） |
| agents | `.codex/agents/<name>.toml`（`developer_instructions` に本文） | `.agents/agents/<name>.md`（`tools` / `model` を変換） |
| rules | `AGENTS.md` に埋め込み | `.agents/rules/<name>.md`（`trigger: model_decision`） |

`${CLAUDE_PLUGIN_ROOT}/rules/` は変換先の参照先に書き換えます。

### 制約（変換で失われるもの）

- **Codex**: エージェントにツール許可リストと `sandbox_mode` を指定できないため、読み取り専用のエージェントは本文に「ファイルを変更しない」を追記するだけです（強制はされません）。Claude の `model` は対応先がないため省略し、親のモデルを継承します。
- **agy**: `tools` は Read → `read_file`、Write → `write_file`、Edit → `edit_file`、Bash → `run_command` に変換します。Grep / Glob に当たるツールは agy 1.5.12 にないため省略して警告します（公式ドキュメントの `view_file` / `grep_search` は実機では使えませんでした）。`model` は sonnet・haiku → `flash`、opus → `pro` に対応づけています。
- agy 1.5.12 では、skills・rules の読み込みと、`design-investigator` がサブエージェントとして `result.md` を書き出すところまで確認済みです。Codex は公式ドキュメントに基づくのみで、実機では未検証です。

## ディレクトリ構成

```
.claude-plugin/marketplace.json     # マーケットプレイス定義
team-*/plugin/<名前>/
  .claude-plugin/plugin.json
  skills/
  agents/
  rules/
scripts/
  generate-catalog.py               # CATALOG.md の生成
  validate-agents.sh                # agents の検証
  convert-harness.py                # Codex / agy 向け変換
```
