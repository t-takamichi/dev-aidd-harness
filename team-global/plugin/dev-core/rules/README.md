# rules

プラグインの標準コンポーネントではないため、自動では読み込まれない。
次のいずれかで参照させる。

- skill / agent の本文から `${CLAUDE_PLUGIN_ROOT}/rules/<ファイル名>.md` を読むよう指示する（相対パスは配布先で解決される保証がない）
- プロジェクトの `CLAUDE.md` から参照する
- 強制したい内容は `hooks/` で実装する

ルールは1ファイル1テーマで置く（例：`coding-style.md`, `review-criteria.md`）。
