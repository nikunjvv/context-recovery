"""Measure retrieval quality against a human-reviewed dataset."""

from __future__ import annotations

import json
from pathlib import Path

from context_recovery.ingest import ingest
from context_recovery.search import search


# Recording these settings makes the evaluation reproducible.
TOP_K = 5
MIN_QUERY_COVERAGE = 0.6


def load_cases(dataset_path: Path) -> list[dict]:
    """Load evaluation cases from JSON."""

    cases = json.loads(
        dataset_path.read_text(encoding="utf-8")
    )

    # The outermost JSON structure must be a list because we expect
    # multiple independent evaluation cases.
    if not isinstance(cases, list):
        raise ValueError(
            "Evaluation dataset must contain a JSON list"
        )

    return cases


def unique_source_paths(results: list) -> list[str]:
    """
    Return each retrieved source once, preserving ranking order.

    Multiple chunks can come from the same file. For this evaluation,
    we care whether the correct file was found, not how many chunks
    from that file appeared.
    """

    source_paths: list[str] = []

    for result in results:
        source_path = result.chunk.source_path

        if source_path not in source_paths:
            source_paths.append(source_path)

    return source_paths


def main() -> None:
    """Run all evaluation cases and report retrieval quality."""

    # This script is inside <repository>/evaluations.
    # Moving up two directory levels gives the repository root.
    project_root = Path(__file__).resolve().parents[1]

    dataset_path = (
        project_root
        / "evaluations"
        / "retrieval_cases.json"
    )
    evidence_root = project_root / "sample_system"

    cases = load_cases(dataset_path)
    # Some questions contain related terminology but cannot be answered
    # from the available evidence. Those belong to answer validation,
    # which will be implemented separately.
    retrieval_cases = [
        case
        for case in cases
        if case.get(
            "evaluation_stage",
            "retrieval",
        ) == "retrieval"
    ]

    answer_cases = [
        case
        for case in cases
        if case.get(
            "evaluation_stage",
            "retrieval",
        ) == "answer"
    ]

    known_case_count = (
        len(retrieval_cases)
        + len(answer_cases)
    )

    if known_case_count != len(cases):
        raise ValueError(
            "Unknown evaluation_stage value"
        )

    # Ingest once and reuse the same chunks for every query.
    # Ingesting inside the loop would repeat identical work.
    chunks, source_files = ingest(evidence_root)

    passed_cases = 0

    supported_cases = 0
    passed_supported_cases = 0

    abstention_cases = 0
    passed_abstention_cases = 0

    required_source_count = 0
    retrieved_required_source_count = 0

    print(
        f"Evaluating {len(retrieval_cases)} cases against "
        f"{len(source_files)} source files and "
        f"{len(chunks)} chunks\n"
    )

    for case in retrieval_cases:
        results = search(
            chunks,
            case["query"],
            top_k=TOP_K,
            min_query_coverage=MIN_QUERY_COVERAGE,
        )

        retrieved_sources = unique_source_paths(results)

        if case["should_abstain"]:
            abstention_cases += 1

            # Returning no evidence is correct for an unsupported
            # question.
            case_passed = not results

            if case_passed:
                passed_abstention_cases += 1
                detail = "correctly abstained"
            else:
                detail = (
                    "unexpected evidence: "
                    + ", ".join(retrieved_sources)
                )

        else:
            supported_cases += 1

            required_sources = set(
                case["required_sources"]
            )
            retrieved_source_set = set(
                retrieved_sources
            )

            missing_sources = sorted(
                required_sources - retrieved_source_set
            )

            # Source recall measures partial retrieval separately.
            # Finding one of two required sources gives 50% recall,
            # although the complete case still fails.
            required_source_count += len(
                required_sources
            )
            retrieved_required_source_count += len(
                required_sources & retrieved_source_set
            )

            # A supported case passes only when every required
            # source appears in the top results.
            case_passed = not missing_sources

            if case_passed:
                passed_supported_cases += 1
                detail = "all required sources retrieved"
            else:
                detail = (
                    "missing: "
                    + ", ".join(missing_sources)
                )

        if case_passed:
            passed_cases += 1

        status = "PASS" if case_passed else "FAIL"

        print(
            f"[{status}] {case['id']}: {detail}"
        )

        if retrieved_sources:
            print(
                "       retrieved: "
                + ", ".join(retrieved_sources)
            )
        else:
            print("       retrieved: none")

    overall_rate = passed_cases / len(retrieval_cases)

    supported_rate = (
        passed_supported_cases / supported_cases
    )

    abstention_rate = (
        passed_abstention_cases / abstention_cases
    )

    source_recall = (
        retrieved_required_source_count
        / required_source_count
    )

    print("\nSummary")
    print(
        "Deferred answer-validation cases: "
        f"{len(answer_cases)}\n"
    )

    print(
        "  Overall case pass rate: "
        f"{passed_cases}/{len(retrieval_cases)} "
        f"({overall_rate:.0%})"
    )

    print(
        "  Supported-case pass rate: "
        f"{passed_supported_cases}/{supported_cases} "
        f"({supported_rate:.0%})"
    )

    print(
        "  Abstention accuracy: "
        f"{passed_abstention_cases}/{abstention_cases} "
        f"({abstention_rate:.0%})"
    )

    print(
        "  Required-source recall: "
        f"{retrieved_required_source_count}/"
        f"{required_source_count} "
        f"({source_recall:.0%})"
    )


if __name__ == "__main__":
    main()
