#!/bin/bash
# Fallback: Brave Search 経由で URL を取得し、nlm source add で投入する
# `nlm source discover` が利用できない環境向け
#
# Usage: source_add_via_brave.sh <NB_ID> <QUERY>
set -euo pipefail

NB_ID="${1:?Notebook ID is required}"
QUERY="${2:?Query is required}"
COUNT="${SOURCES_MAX:-20}"

if [ -z "${BRAVE_API_KEY:-}" ]; then
    echo "ERROR: BRAVE_API_KEY is not set" >&2
    exit 1
fi

ENCODED_QUERY=$(jq -rn --arg q "$QUERY" '$q|@uri')

URLS=$(curl -sf \
    -H "X-Subscription-Token: $BRAVE_API_KEY" \
    "https://api.search.brave.com/res/v1/web/search?q=${ENCODED_QUERY}&count=${COUNT}" \
    | jq -r '.web.results[]?.url // empty')

if [ -z "$URLS" ]; then
    echo "ERROR: No URLs returned from Brave" >&2
    exit 1
fi

ADDED=0
FAILED=0
while IFS= read -r url; do
    [ -z "$url" ] && continue
    if nlm source add "$NB_ID" --url "$url" 2>/dev/null; then
        ADDED=$((ADDED + 1))
    else
        FAILED=$((FAILED + 1))
        echo "  skip: $url" >&2
    fi
done <<< "$URLS"

echo "Added: $ADDED, Failed: $FAILED"
