"""Explicit local migration command; never run during import or app startup."""

from application.saved_comparisons import SavedComparisonError
from infrastructure.sqlite_comparisons import migrate_comparisons


if __name__ == "__main__":
    try:
        migrate_comparisons()
    except SavedComparisonError as error:
        raise SystemExit(f"Comparison storage migration failed: {error.code}") from None
    print("Comparison storage schema v1 is ready.")
