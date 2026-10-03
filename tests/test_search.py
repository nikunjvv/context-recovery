"""Tests for deterministic lexical evidence retrieval."""

import sys
import unittest
from pathlib import Path


# The application package is under <project>/src.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(PROJECT_ROOT / "src"),
)

from context_recovery.ingest import ingest  # noqa: E402
from context_recovery.search import search, tokenize  # noqa: E402


class SearchTests(unittest.TestCase):
    """Verify normalization, ranking and abstention behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        # Ingest the evidence once for all retrieval tests.
        cls.chunks, _ = ingest(
            PROJECT_ROOT / "sample_system"
        )

    def test_tokenize_normalizes_source_code_terms(
        self,
    ) -> None:
        # Underscores become token boundaries and stop words disappear.
        tokens = tokenize(
            "Why is LEGACY_BILLER sent to manual review?"
        )

        self.assertEqual(
            tokens,
            [
                "legacy",
                "biller",
                "sent",
                "manual",
                "review",
            ],
        )

    def test_search_recovers_historical_and_code_evidence(
        self,
    ) -> None:
        results = search(
            self.chunks,
            (
                "Why are finalized legacy corporate invoices "
                "sent to manual review?"
            ),
        )

        result_paths = {
            result.chunk.source_path
            for result in results
        }

        # The result must contain both the historical reason and the
        # source-code implementation.
        self.assertIn(
            "change_records/CR-2009-017.md",
            result_paths,
        )
        self.assertIn(
            "src/rerate_usage.pc",
            result_paths,
        )

        # Every returned result must satisfy the default threshold.
        self.assertTrue(
            all(
                result.query_coverage >= 0.6
                for result in results
            )
        )

        # Results must be ranked from highest score to lowest.
        scores = [
            result.score
            for result in results
        ]

        self.assertEqual(
            scores,
            sorted(scores, reverse=True),
        )

    def test_unsupported_query_is_rejected(
        self,
    ) -> None:
        results = search(
            self.chunks,
            "What is the customer service phone number?",
        )

        self.assertEqual(results, [])

    def test_stop_word_only_query_returns_no_results(
        self,
    ) -> None:
        results = search(
            self.chunks,
            "why is the",
        )

        self.assertEqual(results, [])

    def test_invalid_search_settings_are_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            search(
                self.chunks,
                "legacy invoice",
                top_k=0,
            )

        with self.assertRaises(ValueError):
            search(
                self.chunks,
                "legacy invoice",
                min_query_coverage=1.5,
            )


if __name__ == "__main__":
    unittest.main()
