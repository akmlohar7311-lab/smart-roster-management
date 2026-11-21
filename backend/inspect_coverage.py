
from collections import defaultdict
from datetime import date

from app.database import supabase


ROSTER_ID = "9ab7d77f-dae4-4f11-a72a-cee52de877a5"

DAYS = [
    "2026-12-15",
    "2026-12-16",
    "2026-12-22",
    "2026-12-23",
]



def fetch_all(query):
    result = []
    start = 0

    while True:
        batch = (
            query.order("id")
            .range(start, start + 499)
            .execute()
            .data
        )

        result.extend(batch)

        if len(batch) < 500:
            break

        start += 500

    return result


def to_minutes(time_value):
    hours, minutes = map(
        int, str(time_value).split(":")[:2]
    )
    return hours * 60 + minutes


def main():
    employees = fetch_all(
        supabase.table("employees").select("*")
    )

    shifts = fetch_all(
        supabase.table("roster_entries")
        .select("*")
        .eq("roster_id", ROSTER_ID)
        .in_("work_date", DAYS)
        .eq("status", "working")
    )

    leave_records = fetch_all(
        supabase.table("time_off")
        .select("*")
        .eq("status", "approved")
        .lte("start_date", DAYS[-1])
        .gte("end_date", DAYS[0])
    )

    assignments = fetch_all(
        supabase.table("assignments")
        .select("*")
    )

    brand_processes = fetch_all(
        supabase.table("brand_processes")
        .select("*")
    )

    brands = fetch_all(
        supabase.table("brands").select("*")
    )

    processes = fetch_all(
        supabase.table("processes").select("*")
    )

    brand_map = {
        b["id"]: b["name"]
        for b in brands
    }

    process_map = {
        p["id"]: p["name"]
        for p in processes
    }

    bp_map = {
        bp["id"]: bp
        for bp in brand_processes
    }

    shifts_by_day = defaultdict(list)

    for shift in shifts:
        shifts_by_day[shift["work_date"]].append(shift)

    for day in DAYS:
        print("\n" + "=" * 65)
        print("STAFF CAPACITY:", day)
        print("=" * 65)

        for employee in sorted(
            employees,
            key=lambda e: e["employee_code"]
        ):
            if not employee.get("active", False):
                continue

            employee_id = employee["id"]

            on_leave = any(
                leave["employee_id"] == employee_id
                and leave["start_date"] <= day
                and leave["end_date"] >= day
                for leave in leave_records
            )

            daily_shifts = [
                shift
                for shift in shifts_by_day[day]
                if shift["employee_id"] == employee_id
            ]

            used_minutes = sum(
                to_minutes(s["end_time"])
                - to_minutes(s["start_time"])
                for s in daily_shifts
            )

            remaining = (
                employee["max_daily_minutes"]
                - used_minutes
            )

            if on_leave or remaining < 240:
                continue

            current_assignments = [
                a for a in assignments
                if a["employee_id"] == employee_id
                and a["start_date"] <= day
                and (
                    a["end_date"] is None
                    or a["end_date"] >= day
                )
            ]

            assigned_processes = []

            for assignment in current_assignments:
                bp = bp_map.get(
                    assignment["brand_process_id"], {}
                )

                brand_name = brand_map.get(
                    bp.get("brand_id"), "Unknown"
                )

                process_name = process_map.get(
                    bp.get("process_id"), "Unknown"
                )

                assigned_processes.append(
                    f"{brand_name} / {process_name} "
                    f"({assignment['allocation_percent']}%)"
                )

            print(
                employee["employee_code"],
                employee["name"],
                "| Free:",
                remaining // 60,
                "hours"
            )

            print(
                "  Assignments:",
                ", ".join(assigned_processes)
                or "None"
            )

    print("\nInspection complete.")
    print(
        "Note: Free hours do not guarantee eligibility. "
        "Check weekly offs, skill requirements, "
        "overlapping shifts, and allocation limits."
    )


if __name__ == "__main__":
    main()
