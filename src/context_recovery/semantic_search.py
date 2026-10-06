"""Retrieve evidence using locally generated semantic embeddings."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from context_recovery.ingest import Chunk, ingest


DEFAULT_MODEL = (
    "sentence-transformers/all-MiniLM-L6-v2"
)


@dataclass(frozen=True)
class SemanticSearchResult:
    """One retrieved chunk and its cosine similarity."""

    chunk: Chunk
    similarity: float


def embedding_text(chunk: Chunk) -> str:
    """
    Create the text representation embedded for one chunk.

    Including the path and source type gives the model useful context.
    For example, a query mentioning a runbook can match a file located
    at docs/operations_runbook.md even if the word "runbook" does not
    appear inside that particular chunk.
    """

    return (
        f"Source path: {chunk.source_path}\n"
        f"Source type: {chunk.source_type}\n"
        f"Content:\n{chunk.content}"
    )


def embed_chunks(
    chunks: list[Chunk],
    model: SentenceTransformer,
) -> np.ndarray:
    """Convert all evidence chunks into normalized vectors."""

    texts = [
        embedding_text(chunk)
        for chunk in chunks
    ]

    # Normalization gives every vector length 1. Therefore, the dot
    # product between two vectors is their cosine similarity.
    return model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )


def semantic_search(
    chunks: list[Chunk],
    chunk_embeddings: np.ndarray,
    query: str,
    model: SentenceTransformer,
    top_k: int = 5,
    min_similarity: float = 0.0,
) -> list[SemanticSearchResult]:
    """Return chunks with the highest semantic similarity."""

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than zero"
        )

    if not -1.0 <= min_similarity <= 1.0:
        raise ValueError(
            "min_similarity must be between -1 and 1"
        )

    if len(chunks) != len(chunk_embeddings):
        raise ValueError(
            "Each chunk must have one embedding"
        )

    if not query.strip():
        return []

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )[0]

    # chunk_embeddings has shape:
    #     number_of_chunks x embedding_dimensions
    #
    # query_embedding has shape:
    #     embedding_dimensions
    #
    # The result contains one similarity score per chunk.
    similarities = (
        chunk_embeddings @ query_embedding
    )

    # The negative sign makes argsort return highest scores first.
    ranked_indexes = np.argsort(-similarities)

    results: list[SemanticSearchResult] = []

    for index in ranked_indexes:
        similarity = float(similarities[index])

        if similarity < min_similarity:
            continue

        results.append(
            SemanticSearchResult(
                chunk=chunks[index],
                similarity=similarity,
            )
        )

        if len(results) == top_k:
            break

    return results


def parse_args() -> argparse.Namespace:
    """Read command-line search settings."""

    parser = argparse.ArgumentParser(
        description=(
            "Search evidence using local semantic embeddings."
        )
    )

    parser.add_argument(
        "query",
        help="Natural-language evidence query",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--input",
        default="sample_system",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
    )

    return parser.parse_args()


def main() -> None:
    """Load the corpus and print ranked semantic evidence."""

    args = parse_args()

    project_root = Path(__file__).resolve().parents[2]
    evidence_root = (
        project_root / args.input
    ).resolve()

    chunks, _ = ingest(evidence_root)

    print(f"Loading model: {args.model}")
    model = SentenceTransformer(args.model)

    print(f"Embedding {len(chunks)} chunks")
    chunk_embeddings = embed_chunks(
        chunks,
        model,
    )

    results = semantic_search(
        chunks,
        chunk_embeddings,
        args.query,
        model,
        top_k=args.top_k,
        min_similarity=args.min_similarity,
    )

    if not results:
        print("No matching evidence found.")
        return

    for position, result in enumerate(
        results,
        start=1,
    ):
        chunk = result.chunk

        citation = (
            f"{chunk.source_path}:"
            f"{chunk.start_line}-"
            f"{chunk.end_line}"
        )

        print(
            f"[{position}] "
            f"similarity={result.similarity:.3f}"
        )
        print(f"    source={citation}")


if __name__ == "__main__":
    main()
