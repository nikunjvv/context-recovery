"""Tests for the deterministic evidence-ingestion layer."""

import sys
import unittest
from pathlib import Path


# The application code lives under the repository's src directory.
# Adding it to sys.path allows this test to import context_recovery
# without installing the package first.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from context_recovery.ingest import ingest  # noqa: E402


EVIDENCE_ROOT = PROJECT_ROOT / "sample_system"


class IngestTests(unittest.TestCase):
    """Verify that ingestion produces trustworthy citation metadata."""

    @classmethod
    def setUpClass(cls) -> None:
        # Run ingestion once and reuse the result across all tests.
        cls.chunks, cls.source_paths = ingest(EVIDENCE_ROOT)

    def test_only_approved_evidence_is_ingested(self) -> None:
        # Convert absolute paths into repository-relative evidence paths
        # so the assertion works on any developer's computer.
        actual_sources = {
            path.relative_to(EVIDENCE_ROOT).as_posix()
            for path in self.source_paths
        }

        expected_sources = {
            "change_records/CR-2009-017.md",
            "docs/operations_runbook.md",
            "scripts/nightly_rerate.sh",
            "src/rerate_usage.pc",
        }

        self.assertEqual(actual_sources, expected_sources)

        # scenario.md contains the expected conclusions and must never
        # become searchable evidence.
        self.assertNotIn("scenario.md", actual_sources)

    def test_chunks_contain_citation_metadata(self) -> None:
        self.assertGreater(len(self.chunks), 0)

        for chunk in self.chunks:
            # Every answer citation will need a source and line range.
            self.assertTrue(chunk.source_path)
            self.assertGreaterEqual(chunk.start_line, 1)
            self.assertGreaterEqual(
                chunk.end_line,
                chunk.start_line,
            )

            # IDs and hashes must be present for traceability.
            self.assertEqual(len(chunk.chunk_id), 16)
            self.assertEqual(len(chunk.content_sha256), 64)
            self.assertTrue(chunk.content)


if __name__ == "__main__":
    unittest.main()
