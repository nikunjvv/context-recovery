"""Deterministic lexical retrieval for the evidence corpus."""

from __future__ import annotations

import argparse
import re
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from context_recovery.ingest import Chunk,ingest

# These common words occur frequently but carry little meaning when
# deciding whether a source is relevant to a technical question.
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "by",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "was",
    "were",
    "what",
    "when",
    "which",
    "why",
    "with",
}

@dataclass(frozen=True)
class SearchResult:
    """One retrieved chunk plus transparent scoring evidence."""

    chunk: Chunk
    score: float
    matched_terms: tuple[str, ...]
    query_coverage: float

def tokenize(text: str) -> list[str]:
    """Convert text into normalized terms used for matching.

    The regular expression extracts letters and numbers but treats
    underscores and punctuation as separators. Consequently,
    LEGACY_BILLER becomes the two tokens "legacy" and "biller".
    """

    # Lowercasing allows "Corporate" and "CORPORATE" to match.
    normalized_text = text.lower()

    # Extract alphanumeric sequences. Punctuation, underscores and
    # whitespace act as token boundaries.
    candidate_tokens = re.findall(
        r"[a-z0-9]+",
        normalized_text,
    )

    # Preserve meaningful terms while dropping common stop words.
    return [
        token
        for token in candidate_tokens
        if token not in STOP_WORDS
    ]

def calculate_idf(
    chunks: list[Chunk],
) -> dict[str, float]:
    """Calculate how informative each term is across the corpus.

    A term appearing in only a few chunks is usually more useful than
    a term appearing almost everywhere. For example, "finalized" should
    receive more weight than a common term such as "record".
    """

    # Count the number of chunks containing each term.
    # We use a set per chunk because multiple appearances in the same
    # chunk still count as one document occurrence for IDF.
    document_frequency: Counter[str] = Counter()

    for chunk in chunks:
        unique_terms = set(tokenize(chunk.content))
        document_frequency.update(unique_terms)

    chunk_count = len(chunks)

    # The +1 values prevent division-by-zero problems and keep the
    # formula usable for this small corpus.
    return {
        term: (
            math.log(
                (chunk_count + 1) /
                (frequency + 1)
            )
            + 1
        )
        for term, frequency in document_frequency.items()
    }


def score_chunk(
    query_tokens: list[str],
    chunk: Chunk,
    idf: dict[str, float],
) -> SearchResult | None:
    """Score one chunk using rarity, frequency and query coverage."""

    # The query set is used to determine which distinct query concepts
    # are represented in this chunk.
    unique_query_terms = set(query_tokens)

    # Counter preserves the number of times each term appears in the
    # source chunk.
    chunk_term_counts = Counter(
        tokenize(chunk.content)
    )

    matched_terms = unique_query_terms.intersection(
        chunk_term_counts
    )

    # A chunk matching none of the query terms is irrelevant.
    if not matched_terms:
        return None

    # Rare terms receive more weight through IDF.
    # Repetition increases the score, but logarithmic growth prevents
    # one repeated word from dominating the entire result.
    term_score = sum(
        idf.get(term, 1.0)
        * (
            1.0
            + math.log(
                chunk_term_counts[term]
            )
        )
        for term in matched_terms
    )

    # Reward chunks that cover more distinct parts of the query.
    query_coverage = (
        len(matched_terms)
        / len(unique_query_terms)
    )

    # Coverage adjusts the term score by a factor between 0.5 and 1.0.
    final_score = term_score * (
        0.5 + 0.5 * query_coverage
    )

    return SearchResult(
        chunk=chunk,
        score=final_score,
        matched_terms=tuple(
            sorted(matched_terms)
        ),
	query_coverage=query_coverage,
    )


def search(
    chunks: list[Chunk],
    query: str,
    top_k: int = 5,
    min_query_coverage: float = 0.6,
) -> list[SearchResult]:
    """Return the highest-scoring chunks for a query."""

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than zero"
        )

    if not 0.0 <= min_query_coverage <= 1.0:
        raise ValueError(
            "min_query_coverage must be between zero and one"
        )

    query_tokens = tokenize(query)

    # A query containing only stop words has no searchable meaning.
    if not query_tokens:
        return []

    idf = calculate_idf(chunks)
    results: list[SearchResult] = []

    for chunk in chunks:
        result = score_chunk(
            query_tokens,
            chunk,
            idf,
        )

        if (result is not None and result.query_coverage >= min_query_coverage):
            results.append(result)

    # Highest score first. Path and line number provide deterministic
    # ordering when two chunks have equal scores.
    results.sort(
        key=lambda result: (
            -result.score,
            result.chunk.source_path,
            result.chunk.start_line,
        )
    )

    return results[:top_k]

def parse_args() -> argparse.Namespace:
    """Read the query and retrieval settings from the command line."""

    parser = argparse.ArgumentParser(
        description=(
            "Search the Context Recovery evidence corpus."
        )
    )

    # The query is positional, so the user does not need to write
    # --query before every question.
    parser.add_argument(
        "query",
        help="Natural-language evidence query",
    )

    # Allow the user to control how many ranked chunks are returned.
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
    )

    # Keeping the input configurable allows us to search a different
    # synthetic application later without rewriting this module.
    parser.add_argument(
        "--input",
        default="sample_system",
    )

    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.6,
        help=(
           "Minimum fraction of distinct query terms "
           "that a chunk must match"
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Ingest the current corpus, rank chunks and print citations."""

    args = parse_args()

    # search.py is located at:
    # <project>/src/context_recovery/search.py
    #
    # parents[0] = context_recovery
    # parents[1] = src
    # parents[2] = repository root
    project_root = Path(__file__).resolve().parents[2]

    evidence_root = (
        project_root / args.input
    ).resolve()

    # For this small baseline, rebuild the chunks for each search.
    # A larger system would load them from a persistent index.
    chunks, _ = ingest(evidence_root)

    results = search(
        chunks,
        args.query,
        top_k=args.top_k,
	min_query_coverage=args.min_coverage,
    )

    if not results:
        print("No matching evidence found.")
        return

    for position, result in enumerate(
        results,
        start=1,
    ):
        chunk = result.chunk

        # The citation ties the result back to exact source lines.
        citation = (
            f"{chunk.source_path}:"
            f"{chunk.start_line}-"
            f"{chunk.end_line}"
        )

        # Collapse newlines so the preview remains readable in a
        # terminal. Limit it to 300 characters.
        preview = " ".join(
            chunk.content.split()
        )

        if len(preview) > 300:
            preview = preview[:297] + "..."

        print(
            f"[{position}] "
            f"score={result.score:.3f}"
        )
        print(f"    source={citation}")
        print(
            "    matched="
            f"{', '.join(result.matched_terms)}"
        )
        print(f"    preview={preview}")

        print(
            f"    coverage="
            f"{result.query_coverage:.0%}"
        )

if __name__ == "__main__":
    main()
