
import json
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


BASE_URL = "http://127.0.0.1:8002"
YEAR = 2026
MONTH = 12


def fetch_json(path):
    url = BASE_URL + path

    try:
        with urlopen(url, timeout=60) as response:
            return json.load(response)

    except HTTPError as error:
        raise RuntimeError(
            f"API returned HTTP {error.code}: {url}"
        ) from error

    except URLError as error:
        raise RuntimeError(
            "Cannot connect to FastAPI on port 8002. "
            "Make sure the backend is running."
        ) from error


def get_violation_type(item):
    return str(
        item.get("type")
        or item.get("conflict_type")
        or "unknown"
    )


def get_violation_date(item):
    return str(
        item.get("date")
        or item.get("work_date")
        or "Unknown date"
    )


def main():
    print("=" * 60)
    print("DATASTRAW SMART ROSTER - VALIDATION AUDIT")
    print("=" * 60)

    # 1. Find the latest saved roster for the month.
    roster = fetch_json(
        f"/roster-view/monthly?year={YEAR}&month={MONTH}"
    )

    roster_id = roster["roster_id"]

    print(f"\nRoster month: {YEAR}-{MONTH:02d}")
    print(f"Roster ID: {roster_id}")
    print(f"Version: {roster['version']}")
    print(f"Status: {roster['status']}")
    print(f"Saved entries: {roster['total_entries']}")
    print(f"Working shifts: {roster['working_shifts']}")
    print(f"Cancelled shifts: {roster['cancelled_shifts']}")

    # 2. Run the existing backend validator.
    result = fetch_json(
        f"/rosters/{roster_id}/validate"
    )

    violations = result.get("violations") or []
    summary = result.get("violation_summary") or {}

    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    print(
        "Total violations:",
        result.get("total_violations", "Unknown")
    )

    print("\nViolations by type:")

    if summary:
        for kind, count in sorted(summary.items()):
            print(f"  {kind}: {count}")
    else:
        print("  None reported")

    # 3. Check cancellation and replacement statistics.
    entries = roster.get("entries") or []

    linked_replacements = [
        entry
        for entry in entries
        if entry.get("replaces_entry_id")
        and entry.get("status") == "working"
    ]

    print("\nWorking linked replacements visible in API:",
          len(linked_replacements))

    # 4. Group violations by date.
    by_date = Counter(
        get_violation_date(item)
        for item in violations
    )

    print("\nViolations by date:")

    for day, count in sorted(by_date.items()):
        print(f"  {day}: {count}")

    # 5. Display sample violations.
    print("\nFirst 10 violation details:")

    for index, item in enumerate(violations[:10], 1):
        print(f"\n{index}. {get_violation_type(item)}")

        print(
            json.dumps(
                item,
                indent=2,
                default=str
            )
        )

    if not violations:
        print("No violations returned.")

    # 6. Save a report for later review.
    report = {
        "roster": {
            "id": roster_id,
            "month": f"{YEAR}-{MONTH:02d}",
            "version": roster["version"],
            "status": roster["status"],
            "total_entries": roster["total_entries"],
            "working_shifts": roster["working_shifts"],
            "cancelled_shifts": roster["cancelled_shifts"]
        },
        "validation": result,
        "violations_by_date": dict(
            sorted(by_date.items())
        )
    }

    output_file = Path(__file__).parent / (
        f"roster_audit_{YEAR}_{MONTH:02d}.json"
    )

    output_file.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)
    print("Report saved to:", output_file)

    if result.get("total_violations", 0) > 0:
        print(
            "\nResult: Issues remain and require review."
        )
    else:
        print(
            "\nResult: No violations detected by the "
            "current validator."
        )


if __name__ == "__main__":
    main()
