# rules

プラグインの標準コンポーネントではないため、自動では読み込まれない。
次のいずれかで参照させる。

- skill の本文から `${CLAUDE_PLUGIN_ROOT}/rules/<ファイル名>.md` を読むよう指示する（相対パスは配布先で解決される保証がない）
- agent 本文での `${CLAUDE_PLUGIN_ROOT}` 展開は未検証。確実にしたい内容は本文に直接書くか、呼び出し側が絶対パスで渡す
- プロジェクトの `CLAUDE.md` から参照する
- 強制したい内容は `hooks/` で実装する

ルールは1ファイル1テーマで置く（例：`coding-style.md`, `review-criteria.md`）。
