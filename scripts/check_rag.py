"""Smoke-check RAG: python -m scripts.check_rag [scenario] [query]"""
from __future__ import annotations

import asyncio
import json
import sys

import httpx

BASE_URL = "http://localhost:8000"


async def main(scenario: str, query: str, k: int = 3) -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        resp = await client.post(
            "/api/rag/search",
            json={"scenario_slug": scenario, "query": query, "k": k},
        )
        resp.raise_for_status()
        data = resp.json()

    print(f"query: {query!r}  scenario: {scenario}  k={k}\n")
    if not data["hits"]:
        print("(no hits)")
        return
    for i, hit in enumerate(data["hits"], 1):
        c = hit["citation"]
        print(f"{i}. score={hit['score']:.4f}  [{c['type']}] {c['title']}")
        print(f"   {c['url']}  chunk#{c['chunk_index']}")
        print(f"   {hit['content'][:160]}…\n")


if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "university_choice"
    query = sys.argv[2] if len(sys.argv) > 2 else "когда подавать документы и ЕГЭ"
    asyncio.run(main(scenario, query))