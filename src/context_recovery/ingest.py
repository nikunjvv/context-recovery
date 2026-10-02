"""Create citation-ready chunks from the synthetic evidence corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator


SOURCE_DIRECTORIES = {
    "docs": "runbook",
    "change_records": "change_record",
    "scripts": "shell_script",
    "src": "source_code",
}

SUPPORTED_EXTENSIONS = {".md", ".sh", ".pc"}


@dataclass(frozen=True)
class Chunk:
    """A source fragment with enough metadata to produce a citation."""

    chunk_id: str
    source_path: str
    source_type: str
    start_line: int
    end_line: int
    content_sha256: str
    content: str


def discover_sources(evidence_root: Path) -> list[Path]:
    """Return supported evidence files from approved source directories."""

    sources: list[Path] = []

    for directory_name in SOURCE_DIRECTORIES:
        directory = evidence_root / directory_name

        if not directory.exists():
            continue

        sources.extend(
            path
            for path in directory.rglob("*")
            if path.is_file()
            and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    return sorted(sources)


def source_type_for(path: Path, evidence_root: Path) -> str:
    """Classify a source using its top-level evidence directory."""

    relative_path = path.relative_to(evidence_root)
    directory_name = relative_path.parts[0]

    return SOURCE_DIRECTORIES[directory_name]


def chunk_file(
    path: Path,
    evidence_root: Path,
    chunk_size: int,
    overlap: int,
) -> Iterator[Chunk]:
    """Split one file into overlapping, line-addressable chunks."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be between zero and chunk_size - 1"
        )

    relative_path = path.relative_to(evidence_root).as_posix()
    source_type = source_type_for(path, evidence_root)

    lines = path.read_text(
        encoding="utf-8"
    ).splitlines(keepends=True)

    step = chunk_size - overlap

    for start_index in range(0, len(lines), step):
        end_index = min(start_index + chunk_size, len(lines))

        content = "".join(
            lines[start_index:end_index]
        ).strip()

        if content:
            content_hash = hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest()

            identity = (
                f"{relative_path}:"
                f"{start_index + 1}:"
                f"{end_index}:"
                f"{content_hash}"
            )

            chunk_id = hashlib.sha256(
                identity.encode("utf-8")
            ).hexdigest()[:16]

            yield Chunk(
                chunk_id=chunk_id,
                source_path=relative_path,
                source_type=source_type,
                start_line=start_index + 1,
                end_line=end_index,
                content_sha256=content_hash,
                content=content,
            )

        if end_index == len(lines):
            break


def ingest(
    evidence_root: Path,
    chunk_size: int = 25,
    overlap: int = 5,
) -> tuple[list[Chunk], list[Path]]:
    """Read all approved evidence sources and return their chunks."""

    source_paths = discover_sources(evidence_root)
    chunks: list[Chunk] = []

    for source_path in source_paths:
        chunks.extend(
            chunk_file(
                source_path,
                evidence_root,
                chunk_size,
                overlap,
            )
        )

    return chunks, source_paths


def write_jsonl(
    chunks: list[Chunk],
    output_path: Path,
) -> None:
    """Write one JSON object per line for later indexing."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        for chunk in chunks:
            output_file.write(
                json.dumps(
                    asdict(chunk),
                    ensure_ascii=False,
                )
                + "\n"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create citation-ready chunks "
            "from the evidence corpus."
        )
    )

    parser.add_argument(
        "--input",
        default="sample_system",
    )
    parser.add_argument(
        "--output",
        default="artifacts/chunks.jsonl",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=25,
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=5,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    project_root = Path(__file__).resolve().parents[2]
    evidence_root = (project_root / args.input).resolve()
    output_path = (project_root / args.output).resolve()

    chunks, source_paths = ingest(
        evidence_root=evidence_root,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )

    write_jsonl(chunks, output_path)

    print(f"Sources ingested: {len(source_paths)}")
    print(f"Chunks created: {len(chunks)}")
    print(
        "Output: "
        f"{output_path.relative_to(project_root)}"
    )


if __name__ == "__main__":
    main()
