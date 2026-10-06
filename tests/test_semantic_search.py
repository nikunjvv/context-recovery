"""Unit tests for local semantic retrieval."""

import unittest
from unittest.mock import Mock

import numpy as np

from context_recovery.ingest import Chunk
from context_recovery.semantic_search import (
    embedding_text,
    semantic_search,
)


def make_chunk(
    chunk_id: str,
    source_path: str,
    content: str,
) -> Chunk:
    """Create a small synthetic chunk for unit tests."""

    return Chunk(
        chunk_id=chunk_id,
        source_path=source_path,
        source_type="test_source",
        start_line=1,
        end_line=1,
        content_sha256="test-hash",
        content=content,
    )


class SemanticSearchTests(unittest.TestCase):
    """Test semantic ranking without downloading a real model."""

    def test_embedding_text_contains_metadata(self) -> None:
        """Embedding input should include source context."""

        chunk = make_chunk(
            "chunk-1",
            "docs/operations_runbook.md",
            "Nightly rerating instructions.",
        )

        text = embedding_text(chunk)

        self.assertIn(
            "docs/operations_runbook.md",
            text,
        )
        self.assertIn("test_source", text)
        self.assertIn(
            "Nightly rerating instructions.",
            text,
        )

    def test_results_are_ranked_and_filtered(
        self,
    ) -> None:
        """
        Results should be ranked by cosine similarity.

        A mock model keeps this test fast and prevents network access.
        """

        chunks = [
            make_chunk(
                "chunk-1",
                "docs/runbook.md",
                "Operational documentation.",
            ),
            make_chunk(
                "chunk-2",
                "src/program.pc",
                "Implementation source.",
            ),
        ]

        # Both chunk vectors are already normalized.
        chunk_embeddings = np.array(
            [
                [1.0, 0.0],
                [0.0, 1.0],
            ]
        )

        model = Mock()

        # The query is most similar to the first chunk:
        # first score  = 0.8
        # second score = 0.6
        model.encode.return_value = np.array(
            [[0.8, 0.6]]
        )

        results = semantic_search(
            chunks,
            chunk_embeddings,
            "operational instructions",
            model,
            top_k=5,
            min_similarity=0.7,
        )

        self.assertEqual(1, len(results))
        self.assertEqual(
            "docs/runbook.md",
            results[0].chunk.source_path,
        )
        self.assertAlmostEqual(
            0.8,
            results[0].similarity,
        )

    def test_invalid_settings_are_rejected(
        self,
    ) -> None:
        """Invalid limits should fail with clear errors."""

        chunk = make_chunk(
            "chunk-1",
            "docs/runbook.md",
            "Documentation.",
        )

        embeddings = np.array([[1.0, 0.0]])
        model = Mock()

        with self.assertRaises(ValueError):
            semantic_search(
                [chunk],
                embeddings,
                "query",
                model,
                top_k=0,
            )

        with self.assertRaises(ValueError):
            semantic_search(
                [chunk],
                embeddings,
                "query",
                model,
                min_similarity=1.1,
            )


if __name__ == "__main__":
    unittest.main()
