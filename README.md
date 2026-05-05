# notebooklm-research-pipeline

NotebookLM を起点に、検索クエリ → ソース収集 → マインドマップ → 構造化 Markdown → Deep Research レポート、までを自動化するパイプライン。

二系統の Deep Research バックエンドを切替可能：

- **Branch A**: Claude Max（Claude Code Agent + WebSearch / WebFetch）
- **Branch B**: ローカル LLM（LM Studio + gpt-oss:20b）+ Brave Search API

NotebookLM ノートブック自体は永続 RAG として、後日も `nlm notebook query` で再利用可能。

---

## 設計仕様

詳細な設計仕様書は別リポに置いてあります：

→ [logs-with-llm/logs/20260505-notebooklm-rag-pipeline-spec.md](https://github.com/masa-san-jp/logs-with-llm/blob/main/logs/20260505-notebooklm-rag-pipeline-spec.md)

このリポはその仕様の実装です。

---

## クイックスタート

### 0. 前提

- Python 3.11+
- [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) v0.6.1+
- `jq`
- Branch A: Claude Code（Max プラン）または Anthropic API キー
- Branch B: LM Studio（または Ollama）+ Brave Search API キー

### 1. セットアップ

```bash
git clone https://github.com/masa-jp-art/notebooklm-research-pipeline.git
cd notebooklm-research-pipeline

# Python 依存
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# nlm セットアップ
uv tool install notebooklm-mcp-cli
nlm login

# 環境変数
cp .env.example .env
# .env を編集して必要なキーを設定
```

### 2. 実行

#### Branch A（Claude Max ルート）

```bash
./pipeline_claude.sh "日本の障害福祉サービスのDX動向 2026"
```

成果物：
- `out/mindmap.png`（マインドマップ画像）
- `out/mindmap.md`（構造化 Markdown）
- `out/report.md`（Deep Research レポート）
- `out/meta.json`（実行メタ情報、Notebook ID 含む）

#### Branch B（LM Studio + Brave ルート）

```bash
# LM Studio Local Server を :1234 で起動済みにしておく
./pipeline_local.sh "日本の障害福祉サービスのDX動向 2026"
```

---

## 構成

```
.
├── pipeline_claude.sh           # Branch A オーケストレーション
├── pipeline_local.sh            # Branch B オーケストレーション
├── scripts/
│   ├── source_add_via_brave.sh  # `nlm source discover` フォールバック
│   ├── img_to_md_claude.py      # Claude Vision で画像 → MD
│   ├── img_to_md_local.py       # ローカル Vision モデルで画像 → MD
│   ├── deep_research_claude.py  # Anthropic SDK で Deep Research
│   └── deep_research_local.py   # ローカル LLM + Brave で Deep Research
├── docs/
│   └── (将来：詳細ドキュメント)
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

---

## セキュリティ・運用上の注意

### シークレット管理

- API キーは **必ず** `.env` ファイル経由で読み込む。コードに直書きしない
- `.env` は `.gitignore` 済み。間違って `git add` しないよう注意
- 公開前に `git diff --cached` で機密情報がないか確認

### 出力物の取り扱い

- `out/` 以下は `.gitignore` 済み
- マインドマップ・レポートに機密情報が含まれる可能性があるため、明示的にコミットしない限り共有されない
- 例として共有したい出力は `examples/` ディレクトリ（要新設）に配置し、内容を確認のうえコミット

### NotebookLM の制限

- 非公式 API のため、NotebookLM 側の仕様変更で突然動かなくなる可能性
- 認証クッキーは数週間で失効 → 定期的に `nlm login` を再実行
- フリープランは ≒ 50 クエリ/日、本格運用なら Pro プラン検討

---

## ロードマップ

- [ ] PoC: Branch A で end-to-end 実行確認
- [ ] PoC: Branch B で end-to-end 実行確認
- [ ] `nlm source discover` の実機検証 / フォールバック実装
- [ ] `nlm studio mindmap` 出力形式の実機検証
- [ ] Brave Search のレスポンスキャッシュ層追加
- [ ] レポート品質ゲート（Claude/LLM レビュー工程）
- [ ] CI（lint, type check, smoke test）
- [ ] examples/ にサンプル出力を追加

---

## ライセンス

MIT License — see [LICENSE](./LICENSE)
