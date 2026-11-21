
from collections import defaultdict

from app.database import supabase


DAY = "2026-12-16"
ROSTER_ID = "9ab7d77f-dae4-4f11-a72a-cee52de877a5"


def load_all(query):
    rows = []
    start = 0

    while True:
        batch = (
            query.order("id")
            .range(start, start + 499)
            .execute()
            .data
        )

        rows.extend(batch)

        if len(batch) < 500:
            break

        start += 500

    return rows


def main():
    employees = load_all(
        supabase.table("employees").select("*")
    )

    shifts = load_all(
        supabase.table("roster_entries")
        .select("*")
        .eq("roster_id", ROSTER_ID)
        .eq("work_date", DAY)
        .eq("status", "working")
    )

    absences = load_all(
        supabase.table("time_off")
        .select("*")
        .eq("status", "approved")
        .lte("start_date", DAY)
        .gte("end_date", DAY)
    )

    absent_ids = {
        record["employee_id"]
        for record in absences
    }

    occupied = defaultdict(list)

    for shift in shifts:
        occupied[shift["employee_id"]].append(shift)

    def minutes(value):
        hour, minute = map(
            int, str(value).split(":")[:2]
        )
        return hour * 60 + minute

    print("=" * 65)
    print("EMPLOYEE AVAILABILITY - DECEMBER 16, 2026")
    print("=" * 65)

    for employee in sorted(
        employees,
        key=lambda e: e["employee_code"]
    ):
        if not employee["active"]:
            continue

        employee_shifts = occupied[employee["id"]]

        used = sum(
            minutes(shift["end_time"])
            - minutes(shift["start_time"])
            for shift in employee_shifts
        )

        max_minutes = employee["max_daily_minutes"]
        remaining = max_minutes - used

        absent = employee["id"] in absent_ids

        print(
            f"{employee['employee_code']:7} "
            f"{employee['name'][:22]:22} "
            f"Used: {used // 60}h "
            f"Remaining: {remaining // 60}h "
            f"Approved absence: {'YES' if absent else 'NO'}"
        )

    print("\nNote:")
    print(
        "Remaining hours alone do not establish eligibility. "
        "Assignments, overlapping times, fixed weekly offs, "
        "and process allocation must also be checked."
    )


if __name__ == "__main__":
    main()
