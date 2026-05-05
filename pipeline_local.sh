#!/bin/bash
# Branch B: LM Studio + Brave Search ルートのオーケストレーション
#
# Usage: pipeline_local.sh "<検索クエリ>"
set -euo pipefail

QUERY="${1:-}"
if [ -z "$QUERY" ]; then
    echo "Usage: $0 \"<検索クエリ>\"" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$SCRIPT_DIR/.env"
    set +a
fi

OUT_DIR="${OUT_DIR:-./out}"
SOURCES_MAX="${SOURCES_MAX:-20}"
LM_URL="${LM_STUDIO_URL:-http://localhost:1234/v1}"

if [ -z "${BRAVE_API_KEY:-}" ]; then
    echo "ERROR: BRAVE_API_KEY is not set in .env" >&2
    exit 1
fi

echo "==> Checking local LLM endpoint: $LM_URL"
if ! curl -sf "$LM_URL/models" > /dev/null; then
    echo "ERROR: Local LLM endpoint not reachable. Start LM Studio Local Server (or Ollama)." >&2
    exit 1
fi

mkdir -p "$OUT_DIR"

NB_TITLE="${QUERY} ($(date +%Y-%m-%d))"
echo "==> Creating notebook: $NB_TITLE"
NB_ID=$(nlm notebook create "$NB_TITLE" --json | jq -r '.id')
echo "    Notebook ID: $NB_ID"

echo "==> Discovering sources for: $QUERY"
if ! nlm source discover "$NB_ID" --query "$QUERY" --max "$SOURCES_MAX" 2>/dev/null; then
    echo "    nlm source discover unavailable; falling back to Brave"
    bash "$SCRIPT_DIR/scripts/source_add_via_brave.sh" "$NB_ID" "$QUERY"
fi

SOURCES_COUNT=$(nlm source list "$NB_ID" --json 2>/dev/null | jq 'length' || echo 0)
echo "    Sources added: $SOURCES_COUNT"

echo "==> Generating mind map"
nlm studio mindmap "$NB_ID" --output "$OUT_DIR/mindmap.png"

echo "==> Converting mind map to Markdown (local vision model)"
python "$SCRIPT_DIR/scripts/img_to_md_local.py" "$OUT_DIR/mindmap.png" "$OUT_DIR/mindmap.md"

echo "==> Running Deep Research (local LLM + Brave)"
python "$SCRIPT_DIR/scripts/deep_research_local.py" \
    --input "$OUT_DIR/mindmap.md" \
    --output "$OUT_DIR/report.md"

cat > "$OUT_DIR/meta.json" <<EOF
{
  "query": $(jq -Rn --arg q "$QUERY" '$q'),
  "notebook_id": "$NB_ID",
  "notebook_title": $(jq -Rn --arg t "$NB_TITLE" '$t'),
  "branch": "local",
  "sources_count": $SOURCES_COUNT,
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "==> Done"
echo "    Notebook ID: $NB_ID (re-query later via: nlm notebook query $NB_ID \"...\")"
echo "    Outputs: $OUT_DIR/{mindmap.png, mindmap.md, report.md, meta.json}"
