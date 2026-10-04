"""Validate an artifact directory against docs/ARTIFACT_SCHEMAS.md.

Usage: python scripts/validate_artifacts.py <artifact_dir>
Exit codes: 0 pass, 1 validation failure, 2 usage error.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.artifact_validation import artifact_warnings, read_and_validate  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python scripts/validate_artifacts.py <artifact_dir>", file=sys.stderr)
        return 2
    artifact_dir = Path(argv[1])
    raw, errors = read_and_validate(artifact_dir)
    if errors or raw is None:
        print(f"FAIL: {artifact_dir}")
        for err in errors:
            print(f"  ERROR: {err}")
        return 1
    print(f"PASS: {artifact_dir}")
    for warning in artifact_warnings(raw):
        print(f"  WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
