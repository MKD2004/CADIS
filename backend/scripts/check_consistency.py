"""Compare SQLite chunks with ChromaDB vectors and the FTS5 index (ADR-014).

    python backend/scripts/check_consistency.py            # report only
    python backend/scripts/check_consistency.py --repair   # fix from SQLite

Uses the same settings as the app (CADIS_DATA_DIR, CADIS_EMB_MODEL, …).
Exit code 0 = consistent (or repaired), 1 = differences found.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cadis.ingest.consistency import check  # noqa: E402
from cadis.storage.db import init_db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repair", action="store_true", help="delete orphan vectors, "
                        "re-embed missing ones, rebuild FTS5 if broken")
    args = parser.parse_args()
    init_db()
    report = check(repair=args.repair)
    print(report.summary())
    if report.orphan_vectors[:5]:
        print("  orphan vectors (first 5):", ", ".join(report.orphan_vectors[:5]))
    if report.missing_vectors[:5]:
        print("  missing vectors (first 5):", ", ".join(report.missing_vectors[:5]))
    return 0 if report.ok or report.repaired else 1


if __name__ == "__main__":
    sys.exit(main())
