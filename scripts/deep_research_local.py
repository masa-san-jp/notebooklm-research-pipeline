"""Deep-research orchestration using local LLM (LM Studio / Ollama) + Brave Search.

Reads ./out/mindmap.md as outline, runs a search/fetch/summarize loop per
node, and writes ./out/report.md.

Usage:
    python scripts/deep_research_local.py
    python scripts/deep_research_local.py --input <md> --output <md>
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import time
from typing import Iterable

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LM_URL = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1")
LM_KEY = os.environ.get("LM_STUDIO_API_KEY", "lm-studio")
TEXT_MODEL = os.environ.get("LM_STUDIO_TEXT_MODEL", "gpt-oss-20b")

BRAVE_KEY = os.environ.get("BRAVE_API_KEY")
QUERIES_PER_NODE = int(os.environ.get("BRAVE_QUERIES_PER_NODE", "3"))
RESULTS_PER_QUERY = int(os.environ.get("BRAVE_RESULTS_PER_QUERY", "5"))

DEFAULT_INPUT = "./out/mindmap.md"
DEFAULT_OUTPUT = "./out/report.md"

client = OpenAI(base_url=LM_URL, api_key=LM_KEY)


def llm(prompt: str, max_tokens: int = 2000) -> str:
    resp = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


def brave_search(query: str, top: int) -> list[dict[str, str]]:
    response = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": top},
        headers={"X-Subscription-Token": BRAVE_KEY or ""},
        timeout=30,
    )
    response.raise_for_status()
    results = response.json().get("web", {}).get("results", []) or []
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "desc": r.get("description", ""),
        }
        for r in results[:top]
    ]


def fetch_text(url: str) -> str:
    try:
        response = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (notebooklm-research-pipeline)"},
        )
        response.raise_for_status()
    except Exception as exc:
        return f"[fetch error: {exc}]"

    # Try trafilatura for high-quality extraction
    try:
        import trafilatura

        extracted = trafilatura.extract(response.text, include_comments=False)
        if extracted:
            return extracted[:8000]
    except Exception:
        pass

    # Fallback: strip tags
    text = re.sub(r"<[^>]+>", " ", response.text)
    text = re.sub(r"\s+", " ", text)
    return text[:8000]


def parse_outline(md: str) -> list[str]:
    nodes: list[str] = []
    for line in md.splitlines():
        heading = re.match(r"^(#{1,3})\s+(.+)", line)
        if heading:
            nodes.append(heading.group(2).strip())
            continue
        bullet = re.match(r"^- (.+)", line)
        if bullet:
            nodes.append(bullet.group(1).strip())
    # de-dup while preserving order
    seen: set[str] = set()
    return [n for n in nodes if not (n in seen or seen.add(n))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not BRAVE_KEY:
        raise SystemExit("ERROR: BRAVE_API_KEY is not set")

    outline = pathlib.Path(args.input).read_text(encoding="utf-8")
    nodes = parse_outline(outline)
    print(f"Outline nodes: {len(nodes)}")

    node_reports: list[str] = []
    for index, node in enumerate(nodes, 1):
        print(f"[{index}/{len(nodes)}] {node}")
        try:
            queries_raw = llm(
                f"次のトピックを Web で調べる検索クエリを {QUERIES_PER_NODE} 個、"
                f"改行区切りで挙げてください（各行 1 クエリ、説明不要）:\n{node}",
                max_tokens=400,
            )
        except Exception as exc:
            print(f"  llm error (queries): {exc}")
            continue

        queries: Iterable[str] = (
            q.strip(" -*0123456789.") for q in queries_raw.splitlines() if q.strip()
        )

        summaries: list[str] = []
        for query in list(queries)[:QUERIES_PER_NODE]:
            try:
                hits = brave_search(query, RESULTS_PER_QUERY)
            except Exception as exc:
                print(f"  brave error: {exc}")
                continue
            for hit in hits:
                content = fetch_text(hit["url"])
                if content.startswith("[fetch error"):
                    continue
                try:
                    summary = llm(
                        f"出典 {hit['url']} の内容を 200 字以内で要約してください。"
                        f"事実のみ、推測は除く。\n\n---\n{content}",
                        max_tokens=400,
                    )
                except Exception as exc:
                    summary = f"[summary error: {exc}]"
                summaries.append(f"- ({hit['url']}) {summary}")
                time.sleep(0.2)  # gentle pacing

        if not summaries:
            node_reports.append(f"## {node}\n\n(調査結果が得られませんでした)\n")
            continue

        try:
            integrated = llm(
                f"以下の出典付き要約を統合し、トピック「{node}」のレポートを"
                f"800 字程度で書いてください。出典 URL を本文中に明記:\n\n"
                + "\n".join(summaries),
                max_tokens=2000,
            )
        except Exception as exc:
            integrated = f"[integration error: {exc}]"

        node_reports.append(f"## {node}\n\n{integrated}\n")

    if not node_reports:
        raise SystemExit("ERROR: No node reports generated")

    final = llm(
        "以下のトピック別レポートを統合して、エグゼクティブサマリー付きの最終"
        "レポートにしてください。Markdown で出力。\n\n" + "\n".join(node_reports),
        max_tokens=4000,
    )

    pathlib.Path(args.output).write_text(final, encoding="utf-8")
    print(f"Wrote {args.output} ({len(final)} chars)")


if __name__ == "__main__":
    main()
