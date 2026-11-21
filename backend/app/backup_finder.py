
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.database import supabase


router = APIRouter(
    prefix="/backups",
    tags=["Backup Employees"]
)


def get_all(query):
    """Read all matching records using pagination."""
    rows = []
    start = 0
    size = 500

    while True:
        batch = (
            query.order("id")
            .range(start, start + size - 1)
            .execute()
            .data
        )

        rows.extend(batch)

        if len(batch) < size:
            break

        start += size

    return rows


def get_one(table, record_id):
    result = (
        supabase.table(table)
        .select("*")
        .eq("id", str(record_id))
        .limit(1)
        .execute()
        .data
    )
    return result[0] if result else None


def minutes(value):
    hour, minute = map(int, str(value).split(":")[:2])
    return hour * 60 + minute


def active_on(record, day, start_field, end_field):
    return (
        record[start_field] <= day
        and (
            record[end_field] is None
            or record[end_field] >= day
        )
    )


@router.get("/available/{entry_id}")
def find_backup_employees(entry_id: UUID):

    # 1. Find the shift we want to cover.
    entry = get_one("roster_entries", entry_id)

    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Roster entry not found"
        )

    roster = get_one("rosters", entry["roster_id"])

    if not roster:
        raise HTTPException(404, "Roster not found")

    if roster["status"] != "draft":
        raise HTTPException(
            status_code=409,
            detail="Only draft rosters can be edited"
        )

    day = entry["work_date"]
    weekday = date.fromisoformat(day).isoweekday()

    shift_start = minutes(entry["start_time"])
    shift_end = minutes(entry["end_time"])
    shift_duration = shift_end - shift_start

    if shift_duration <= 0:
        raise HTTPException(409, "Invalid shift duration")

    bp = get_one(
        "brand_processes",
        entry["brand_process_id"]
    )

    if not bp or not bp["active"]:
        raise HTTPException(
            409, "Brand-process is inactive or missing"
        )

    brand = get_one("brands", bp["brand_id"])

    if not brand or not brand["active"]:
        raise HTTPException(409, "Brand is inactive")

    if weekday not in bp["operating_days"]:
        raise HTTPException(
            409, "Process is closed on this date"
        )

    holidays = (
        supabase.table("holidays")
        .select("id")
        .eq("holiday_date", day)
        .eq("calendar_code", bp["holiday_calendar_code"])
        .limit(1)
        .execute()
        .data
    )

    if holidays and not bp["works_on_holidays"]:
        raise HTTPException(
            409, "Process is closed for a holiday"
        )

    shift_template = (
        get_one("shift_templates", bp["shift_template_id"])
        if bp["shift_template_id"] else None
    )

    if not shift_template:
        raise HTTPException(409, "Shift template missing")

    if (
        shift_start < minutes(shift_template["start_time"])
        or shift_end > minutes(shift_template["end_time"])
    ):
        raise HTTPException(
            409, "Shift is outside the process time window"
        )

    # 2. Load employees and scheduling rules.
    employees = get_all(
        supabase.table("employees")
        .select("*")
        .eq("active", True)
    )

    assignments = get_all(
        supabase.table("assignments")
        .select("*")
        .lte("start_date", day)
    )

    assignments = [
        a for a in assignments
        if a["end_date"] is None or a["end_date"] >= day
    ]

    leaves = get_all(
        supabase.table("time_off")
        .select("*")
        .eq("status", "approved")
        .lte("start_date", day)
        .gte("end_date", day)
    )

    weekly_offs = get_all(
        supabase.table("weekly_offs")
        .select("*")
        .eq("day_of_week", weekday)
        .lte("effective_from", day)
        .eq("rule_type", "fixed")
    )

    daily_shifts = get_all(
        supabase.table("roster_entries")
        .select("*")
        .eq("roster_id", entry["roster_id"])
        .eq("work_date", day)
        .eq("status", "working")
    )

    # 3. Evaluate each possible replacement.
    assigned_backups = []
    potential_backups = []

    for employee in employees:
        employee_id = employee["id"]

        if employee_id == entry["employee_id"]:
            continue

        if any(
            leave["employee_id"] == employee_id
            for leave in leaves
        ):
            continue

        fixed_off = any(
            off["employee_id"] == employee_id
            and (
                off["effective_to"] is None
                or off["effective_to"] >= day
            )
            for off in weekly_offs
        )

        if fixed_off:
            continue

        existing = [
            shift for shift in daily_shifts
            if shift["employee_id"] == employee_id
        ]

        # Check existing shift overlap.
        overlaps = any(
            shift_start < minutes(shift["end_time"])
            and shift_end > minutes(shift["start_time"])
            for shift in existing
        )

        if overlaps:
            continue

        used_minutes = sum(
            minutes(shift["end_time"])
            - minutes(shift["start_time"])
            for shift in existing
        )

        daily_limit = employee["max_daily_minutes"]
        remaining = daily_limit - used_minutes

        if remaining < shift_duration:
            continue

        active_assignments = [
            a for a in assignments
            if a["employee_id"] == employee_id
        ]

        matching = [
            a for a in active_assignments
            if a["brand_process_id"]
            == entry["brand_process_id"]
        ]

        # Case A: Employee is already assigned.
        if matching:
            allocation_limit = round(
                daily_limit
                * min(
                    100,
                    sum(
                        float(a["allocation_percent"])
                        for a in matching
                    )
                ) / 100
            )

            used_for_process = sum(
                minutes(shift["end_time"])
                - minutes(shift["start_time"])
                for shift in existing
                if shift["brand_process_id"]
                == entry["brand_process_id"]
            )

            if (
                used_for_process + shift_duration
                <= allocation_limit
            ):
                assigned_backups.append({
                    "employee_code": employee["employee_code"],
                    "name": employee["name"],
                    "remaining_minutes": remaining,
                    "assignment_status": "already_assigned"
                })

        # Case B: Employee would need a new assignment.
        else:
            total_allocation = sum(
                float(a["allocation_percent"])
                for a in active_assignments
            )

            needed_allocation = (
                shift_duration / daily_limit * 100
            )

            if (
                total_allocation + needed_allocation
                <= 100.000001
            ):
                potential_backups.append({
                    "employee_code": employee["employee_code"],
                    "name": employee["name"],
                    "remaining_minutes": remaining,
                    "required_allocation_percent": round(
                        needed_allocation, 2
                    ),
                    "assignment_status": "temporary_assignment_needed"
                })

    return {
        "entry_id": str(entry_id),
        "entry_status": entry["status"],
        "work_date": day,
        "shift_start": entry["start_time"],
        "shift_end": entry["end_time"],
        "assigned_backups": assigned_backups,
        "potential_backups": potential_backups,
        "note": (
            "Only assigned backups can be used by the current "
            "replacement API. Potential backups require a "
            "separately approved assignment."
        )
    }
