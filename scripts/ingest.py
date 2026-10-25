"""Загрузка базы знаний в БД: python -m scripts.ingest [--force]"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.rag.embeddings import get_embedding_provider
from app.rag.service import RagService
from app.repositories.knowledge_chunk import KnowledgeChunkRepository
from app.repositories.scenario import ScenarioRepository

KB_ROOT = Path(__file__).resolve().parent.parent / "knowledge_base"


async def ingest_all(kb_root: Path, *, force: bool = False) -> int:
    embedder = get_embedding_provider()
    ingested = 0
    async with SessionLocal() as session:
        scenario_repo = ScenarioRepository(session)
        chunk_repo = KnowledgeChunkRepository(session)
        rag = RagService(embedder=embedder, chunk_repo=chunk_repo)

        for file in sorted(kb_root.glob("*/sources.json")):
            data = json.loads(file.read_text(encoding="utf-8"))
            sc = data["scenario"]
            scenario = await scenario_repo.get_by_slug(sc["slug"])
            if scenario is None:
                scenario = await scenario_repo.create(
                    slug=sc["slug"], title=sc["title"], description=sc.get("description", "")
                )
                print(f"[scenario] created {sc['slug']}")

            for src in data["sources"]:
                exists = await chunk_repo.has_source(scenario.id, src["url"])
                if exists and not force:
                    print(f"[skip] {sc['slug']} :: {src['url']} (already ingested)")
                    continue
                if exists and force:
                    removed = await chunk_repo.delete_by_source(scenario.id, src["url"])
                    print(f"[wipe] {sc['slug']} :: {src['url']} ({removed} chunks)")
                chunks = await rag.ingest_source(
                    scenario_id=scenario.id,
                    source_url=src["url"],
                    source_title=src.get("title", ""),
                    source_type=src.get("type", "open"),
                    content=src["content"],
                )
                ingested += len(chunks)
                print(f"[ok]   {sc['slug']} :: {src['url']} ({len(chunks)} chunks)")
    return ingested


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="переиндексировать источники")
    args = parser.parse_args()

    if not KB_ROOT.exists():
        print(f"knowledge_base not found at {KB_ROOT}", file=sys.stderr)
        raise SystemExit(1)
    total = asyncio.run(ingest_all(KB_ROOT, force=args.force))
    print(f"done, total chunks ingested: {total}")


if __name__ == "__main__":
    main()