"""Fact storage and recall: SQLite rows + sqlite-vec cosine index, embeddings via Ollama."""

import logging
import time

import httpx
import sqlite_vec

import config
import db

log = logging.getLogger("jarvis.memory")

# Cosine distance below which two facts are considered duplicates,
# and above which recall results are dropped as irrelevant.
DUP_DISTANCE = 0.15
RECALL_MAX_DISTANCE = 0.55
RECALL_TOP_K = 5


async def embed(text: str) -> bytes:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{config.OLLAMA_URL}/api/embed",
            json={"model": config.EMBED_MODEL, "input": text},
        )
        r.raise_for_status()
        return sqlite_vec.serialize_float32(r.json()["embeddings"][0])


async def add_fact(
    content: str,
    *,
    subject: str = "user",
    source: str = "explicit",
    confidence: float = 1.0,
    dedup: bool = True,
) -> int | None:
    """Store a fact. Returns fact id, or None if deduplicated away."""
    vec = await embed(content)
    now = time.time()
    with db.connect() as conn:
        if dedup:
            row = conn.execute(
                "SELECT fact_id, distance FROM vec_facts WHERE embedding MATCH ? "
                "AND k = 1",
                (vec,),
            ).fetchone()
            if row and row["distance"] < DUP_DISTANCE:
                log.info("dedup: fact %d already covers %r", row["fact_id"], content[:60])
                return None
        cur = conn.execute(
            "INSERT INTO facts (subject, content, source, confidence, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?)",
            (subject, content, source, confidence, now, now),
        )
        conn.execute(
            "INSERT INTO vec_facts (fact_id, embedding) VALUES (?,?)", (cur.lastrowid, vec)
        )
    log.info("stored fact %d (%s): %r", cur.lastrowid, source, content[:80])
    return cur.lastrowid


async def search_facts(query: str, k: int = RECALL_TOP_K) -> list[dict]:
    vec = await embed(query)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT f.id, f.subject, f.content, f.source, f.confidence, v.distance "
            "FROM vec_facts v JOIN facts f ON f.id = v.fact_id "
            "WHERE v.embedding MATCH ? AND k = ? ORDER BY v.distance",
            (vec, k),
        ).fetchall()
    return [dict(r) for r in rows]


async def recall_block(query: str) -> str:
    """Top relevant facts formatted for the system prompt; empty string if none."""
    hits = [h for h in await search_facts(query) if h["distance"] <= RECALL_MAX_DISTANCE]
    if not hits:
        return ""
    return "\n".join(f"- {h['content']}" for h in hits)


def list_facts() -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, subject, content, source, confidence, created_at FROM facts "
            "ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_fact(fact_id: int) -> None:
    with db.connect() as conn:
        conn.execute("DELETE FROM facts WHERE id=?", (fact_id,))
        conn.execute("DELETE FROM vec_facts WHERE fact_id=?", (fact_id,))


async def update_fact(fact_id: int, content: str) -> None:
    vec = await embed(content)
    with db.connect() as conn:
        conn.execute(
            "UPDATE facts SET content=?, updated_at=? WHERE id=?",
            (content, time.time(), fact_id),
        )
        conn.execute("DELETE FROM vec_facts WHERE fact_id=?", (fact_id,))
        conn.execute("INSERT INTO vec_facts (fact_id, embedding) VALUES (?,?)", (fact_id, vec))


async def forget(query: str) -> dict | None:
    """Delete the fact best matching the query. Returns the deleted fact or None."""
    hits = await search_facts(query, k=1)
    if not hits or hits[0]["distance"] > RECALL_MAX_DISTANCE:
        return None
    delete_fact(hits[0]["id"])
    log.info("forgot fact %d: %r", hits[0]["id"], hits[0]["content"][:80])
    return hits[0]
