#!/bin/bash
# Branch A: Claude Max ルートのオーケストレーション
#
# Usage: pipeline_claude.sh "<検索クエリ>"
set -euo pipefail

QUERY="${1:-}"
if [ -z "$QUERY" ]; then
    echo "Usage: $0 \"<検索クエリ>\"" >&2
    exit 1
fi

# Load .env if present
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$SCRIPT_DIR/.env"
    set +a
fi

OUT_DIR="${OUT_DIR:-./out}"
SOURCES_MAX="${SOURCES_MAX:-20}"

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

echo "==> Converting mind map to Markdown (Claude Vision)"
python "$SCRIPT_DIR/scripts/img_to_md_claude.py" "$OUT_DIR/mindmap.png" "$OUT_DIR/mindmap.md"

echo "==> Running Deep Research"
if [ "${USE_INTERACTIVE:-1}" = "1" ]; then
    cat <<EOF

To complete deep research within your Max plan, open Claude Code and run:

    Read $OUT_DIR/mindmap.md and run a deep-research pass over each heading.
    For each topic, use general-purpose agents in parallel to WebSearch + WebFetch
    3-5 sources, summarize with citations, then integrate to $OUT_DIR/report.md.

(Set USE_INTERACTIVE=0 to call the Anthropic SDK directly instead.)
EOF
else
    python "$SCRIPT_DIR/scripts/deep_research_claude.py" \
        --input "$OUT_DIR/mindmap.md" \
        --output "$OUT_DIR/report.md"
fi

cat > "$OUT_DIR/meta.json" <<EOF
{
  "query": $(jq -Rn --arg q "$QUERY" '$q'),
  "notebook_id": "$NB_ID",
  "notebook_title": $(jq -Rn --arg t "$NB_TITLE" '$t'),
  "branch": "claude",
  "sources_count": $SOURCES_COUNT,
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "==> Done"
echo "    Notebook ID: $NB_ID (re-query later via: nlm notebook query $NB_ID \"...\")"
echo "    Outputs: $OUT_DIR/{mindmap.png, mindmap.md, report.md, meta.json}"
