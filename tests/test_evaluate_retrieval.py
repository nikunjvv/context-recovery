"""Tests for the retrieval evaluation dataset and helper functions."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from evaluations.evaluate_retrieval import (
    load_cases,
    unique_source_paths,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = (
    PROJECT_ROOT
    / "evaluations"
    / "retrieval_cases.json"
)

EVIDENCE_ROOT = PROJECT_ROOT / "sample_system"


class RetrievalEvaluationTests(unittest.TestCase):
    """Protect assumptions used by the retrieval evaluation."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the shared dataset once for all tests."""

        cls.cases = load_cases(DATASET_PATH)

    def test_case_ids_are_unique(self) -> None:
        """
        Every case needs a unique identifier.

        Otherwise, two failures could have the same name and make
        evaluation reports ambiguous.
        """

        case_ids = [
            case["id"]
            for case in self.cases
        ]

        self.assertEqual(
            len(case_ids),
            len(set(case_ids)),
        )

    def test_abstention_cases_have_no_required_sources(
        self,
    ) -> None:
        """
        Unsupported questions must not expect evidence.

        A case cannot logically require the system to abstain while
        also requiring it to retrieve particular sources.
        """

        for case in self.cases:
            if case["should_abstain"]:
                self.assertEqual(
                    [],
                    case["required_sources"],
                )

    def test_required_source_files_exist(self) -> None:
        """
        Every expected source path must exist.

        This prevents a spelling mistake in the dataset from being
        incorrectly reported as a retrieval failure.
        """

        for case in self.cases:
            for source_path in case["required_sources"]:
                full_path = (
                    EVIDENCE_ROOT / source_path
                )

                self.assertTrue(
                    full_path.is_file(),
                    f"Missing required source: {source_path}",
                )

    def test_load_cases_rejects_non_list_json(
        self,
    ) -> None:
        """The dataset must contain a list of cases."""

        with tempfile.TemporaryDirectory() as temp_directory:
            dataset_path = (
                Path(temp_directory) / "invalid.json"
            )

            dataset_path.write_text(
                '{"id": "not-a-list"}',
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_cases(dataset_path)

    def test_unique_source_paths_removes_duplicates(
        self,
    ) -> None:
        """
        Multiple chunks from one file count as one source.

        SimpleNamespace creates small test objects with the same
        attributes used by unique_source_paths. This avoids creating
        complete search results when the test only needs source paths.
        """

        results = [
            SimpleNamespace(
                chunk=SimpleNamespace(
                    source_path="docs/runbook.md"
                )
            ),
            SimpleNamespace(
                chunk=SimpleNamespace(
                    source_path="docs/runbook.md"
                )
            ),
            SimpleNamespace(
                chunk=SimpleNamespace(
                    source_path="src/program.pc"
                )
            ),
        ]

        self.assertEqual(
            [
                "docs/runbook.md",
                "src/program.pc",
            ],
            unique_source_paths(results),
        )


if __name__ == "__main__":
    unittest.main()
