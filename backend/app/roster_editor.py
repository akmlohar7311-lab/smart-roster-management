
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from postgrest.exceptions import APIError

from app.database import supabase
from app.validator import validate_roster


router = APIRouter(
    prefix="/roster-editor",
    tags=["Roster Editing"]
)


class ReplacementRequest(BaseModel):
    employee_code: str = Field(min_length=1)


def fetch_one(table, record_id):
    rows = (
        supabase.table(table)
        .select("*")
        .eq("id", str(record_id))
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def fetch_all(query):
    """Fetch all matching records in pages."""
    result = []
    start = 0
    page_size = 500

    while True:
        batch = (
            query.order("id")
            .range(start, start + page_size - 1)
            .execute()
            .data
        )

        result.extend(batch)

        if len(batch) < page_size:
            break

        start += page_size

    return result


def minutes(value):
    hour, minute = map(int, str(value).split(":")[:2])
    return hour * 60 + minute


def get_draft_entry(entry_id):
    entry = fetch_one("roster_entries", entry_id)

    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Roster entry not found"
        )

    roster = fetch_one("rosters", entry["roster_id"])

    if not roster or roster["status"] != "draft":
        raise HTTPException(
            status_code=409,
            detail="Only draft rosters can be edited"
        )

    if entry["status"] != "working":
        raise HTTPException(
            status_code=409,
            detail="This shift is already cancelled"
        )

    return entry, roster


def ensure_no_working_replacement(entry_id):
    """Prevent multiple working replacements for one original shift."""
    rows = (
        supabase.table("roster_entries")
        .select("id")
        .eq("replaces_entry_id", str(entry_id))
        .eq("status", "working")
        .limit(1)
        .execute()
        .data
    )

    if rows:
        raise HTTPException(
            status_code=409,
            detail="This shift already has a working replacement"
        )


def insert_linked_replacement(payload):
    """Insert a linked replacement with database uniqueness protection."""
    try:
        rows = (
            supabase.table("roster_entries")
            .insert(payload)
            .execute()
            .data
        )

    except APIError as exc:
        if str(exc.code) == "23505":
            raise HTTPException(
                status_code=409,
                detail="This shift already has a working replacement"
            ) from exc

        raise

    if not rows:
        raise HTTPException(
            status_code=500,
            detail="Replacement was not inserted"
        )

    return rows[0]


def validate_replacement(entry, employee):
    """Check whether a new employee may take the shift."""

    employee_id = employee["id"]
    bp_id = entry["brand_process_id"]
    day = entry["work_date"]

    # Employee must be active.
    if not employee["active"]:
        raise HTTPException(
            status_code=409,
            detail="Employee is inactive"
        )

    # Check brand-process assignment.
    assignments = (
        supabase.table("assignments")
        .select("*")
        .eq("employee_id", employee_id)
        .eq("brand_process_id", bp_id)
        .lte("start_date", day)
        .execute()
        .data
    )

    assignments = [
        a for a in assignments
        if a["end_date"] is None
        or a["end_date"] >= day
    ]

    if not assignments:
        raise HTTPException(
            status_code=409,
            detail="Employee is not assigned to this brand-process"
        )

    # Check approved leave and comp-offs.
    absences = (
        supabase.table("time_off")
        .select("id")
        .eq("employee_id", employee_id)
        .eq("status", "approved")
        .lte("start_date", day)
        .gte("end_date", day)
        .limit(1)
        .execute()
        .data
    )

    if absences:
        raise HTTPException(
            status_code=409,
            detail="Employee has an approved absence"
        )

    # Check fixed weekly offs.
    weekday = date.fromisoformat(day).isoweekday()

    offs = (
        supabase.table("weekly_offs")
        .select("*")
        .eq("employee_id", employee_id)
        .eq("day_of_week", weekday)
        .eq("rule_type", "fixed")
        .lte("effective_from", day)
        .execute()
        .data
    )

    if any(
        off["effective_to"] is None
        or off["effective_to"] >= day
        for off in offs
    ):
        raise HTTPException(
            status_code=409,
            detail="Employee has a fixed weekly off"
        )

    # Read current working shifts for employee/date.
    existing = fetch_all(
        supabase.table("roster_entries")
        .select("*")
        .eq("roster_id", entry["roster_id"])
        .eq("employee_id", employee_id)
        .eq("work_date", day)
        .eq("status", "working")
    )

    new_start = minutes(entry["start_time"])
    new_end = minutes(entry["end_time"])
    new_duration = new_end - new_start

    if new_duration <= 0:
        raise HTTPException(
            status_code=409,
            detail="Invalid shift duration"
        )

    used_minutes = 0
    same_process_minutes = 0

    for old in existing:
        old_start = minutes(old["start_time"])
        old_end = minutes(old["end_time"])

        # Prevent overlapping shifts.
        if new_start < old_end and new_end > old_start:
            raise HTTPException(
                status_code=409,
                detail="Replacement has an overlapping shift"
            )

        used_minutes += old_end - old_start

        if old["brand_process_id"] == bp_id:
            same_process_minutes += old_end - old_start

    # Check daily maximum hours.
    daily_limit = employee["max_daily_minutes"]

    if used_minutes + new_duration > daily_limit:
        raise HTTPException(
            status_code=409,
            detail="Replacement exceeds daily working hours"
        )

    # Respect process allocation.
    allocation_percent = min(
        100,
        sum(
            float(a["allocation_percent"])
            for a in assignments
        )
    )

    allocation_limit = round(
        daily_limit * allocation_percent / 100
    )

    if same_process_minutes + new_duration > allocation_limit:
        raise HTTPException(
            status_code=409,
            detail="Replacement exceeds process allocation"
        )

    # Check active brand-process.
    bp = fetch_one("brand_processes", bp_id)

    if not bp or not bp["active"]:
        raise HTTPException(
            status_code=409,
            detail="Brand-process is inactive"
        )

    brand = fetch_one("brands", bp["brand_id"])

    if not brand or not brand["active"]:
        raise HTTPException(
            status_code=409,
            detail="Brand is inactive"
        )

    # Check operating weekdays.
    if weekday not in bp["operating_days"]:
        raise HTTPException(
            status_code=409,
            detail="Process does not operate on this date"
        )

    # Check holiday rules.
    holiday = (
        supabase.table("holidays")
        .select("id")
        .eq("holiday_date", day)
        .eq("calendar_code", bp["holiday_calendar_code"])
        .limit(1)
        .execute()
        .data
    )

    if holiday and not bp["works_on_holidays"]:
        raise HTTPException(
            status_code=409,
            detail="Process is closed for the holiday"
        )

    # Check configured shift window.
    shift = (
        fetch_one(
            "shift_templates",
            bp["shift_template_id"]
        )
        if bp["shift_template_id"]
        else None
    )

    if shift is None:
        raise HTTPException(
            status_code=409,
            detail="Shift template is missing"
        )

    if (
        new_start < minutes(shift["start_time"])
        or new_end > minutes(shift["end_time"])
    ):
        raise HTTPException(
            status_code=409,
            detail="Shift falls outside configured working hours"
        )


# -------------------------------------------------
# 1. VIEW A ROSTER'S SHIFTS
# -------------------------------------------------

@router.get("/rosters/{roster_id}/entries")
def get_roster_entries(
    roster_id: UUID,
    employee_code: str | None = None
):
    roster = fetch_one("rosters", roster_id)

    if not roster:
        raise HTTPException(
            status_code=404,
            detail="Roster not found"
        )

    query = (
        supabase.table("roster_entries")
        .select("*")
        .eq("roster_id", str(roster_id))
    )

    if employee_code:
        employees = (
            supabase.table("employees")
            .select("id")
            .eq("employee_code", employee_code)
            .limit(1)
            .execute()
            .data
        )

        if not employees:
            raise HTTPException(
                status_code=404,
                detail="Employee not found"
            )

        query = query.eq(
            "employee_id",
            employees[0]["id"]
        )

    entries = fetch_all(query)

    return {
        "roster_id": str(roster_id),
        "total": len(entries),
        "entries": entries
    }


# -------------------------------------------------
# 2. CANCEL A SAVED SHIFT
# -------------------------------------------------

@router.patch("/entries/{entry_id}/cancel")
def cancel_shift(entry_id: UUID):
    entry, roster = get_draft_entry(entry_id)

    updated = (
        supabase.table("roster_entries")
        .update({"status": "cancelled"})
        .eq("id", str(entry_id))
        .eq("status", "working")
        .execute()
        .data
    )

    if not updated:
        raise HTTPException(
            status_code=409,
            detail="Shift could not be cancelled"
        )

    validation = validate_roster(roster["id"])

    return {
        "message": "Shift cancelled successfully",
        "entry_id": str(entry_id),
        "status": "cancelled",
        "roster_validation": {
            "total_violations": validation[
                "total_violations"
            ],
            "violation_summary": validation[
                "violation_summary"
            ]
        }
    }


# -------------------------------------------------
# 3. REPLACE AN EMPLOYEE ON A WORKING SHIFT
# -------------------------------------------------

@router.post("/entries/{entry_id}/replace")
def replace_shift(
    entry_id: UUID,
    request: ReplacementRequest
):
    entry, roster = get_draft_entry(entry_id)

    # Prevent replacing a shift that is already covered.
    ensure_no_working_replacement(entry_id)

    employees = (
        supabase.table("employees")
        .select("*")
        .eq("employee_code", request.employee_code)
        .limit(1)
        .execute()
        .data
    )

    if not employees:
        raise HTTPException(
            status_code=404,
            detail="Replacement employee not found"
        )

    replacement = employees[0]

    if replacement["id"] == entry["employee_id"]:
        raise HTTPException(
            status_code=409,
            detail="Select a different employee"
        )

    # Check eligibility before making changes.
    validate_replacement(entry, replacement)

    new_entry_data = {
        "roster_id": entry["roster_id"],
        "employee_id": replacement["id"],
        "brand_process_id": entry["brand_process_id"],
        "work_date": entry["work_date"],
        "start_time": entry["start_time"],
        "end_time": entry["end_time"],
        "status": "working",
        "replaces_entry_id": entry["id"]
    }

    # Save new working replacement.
    new_entry = insert_linked_replacement(
        new_entry_data
    )

    try:
        # Cancel original shift only after successful insert.
        cancelled = (
            supabase.table("roster_entries")
            .update({"status": "cancelled"})
            .eq("id", str(entry_id))
            .eq("status", "working")
            .execute()
            .data
        )

        if not cancelled:
            raise RuntimeError(
                "Original shift could not be cancelled"
            )

    except Exception as exc:
        # Best-effort cleanup if cancellation fails.
        # A PostgreSQL transaction is needed for full
        # atomicity before production deployment.
        try:
            (
                supabase.table("roster_entries")
                .delete()
                .eq("id", new_entry["id"])
                .execute()
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=409,
            detail=(
                "Original shift could not be cancelled; "
                "verify roster state"
            )
        ) from exc

    validation = validate_roster(roster["id"])

    return {
        "message": "Shift reassigned successfully",
        "old_entry_id": str(entry_id),
        "new_entry_id": new_entry["id"],
        "replacement_employee": replacement["name"],
        "roster_validation": {
            "total_violations": validation[
                "total_violations"
            ],
            "violation_summary": validation[
                "violation_summary"
            ]
        }
    }


# -------------------------------------------------
# 4. FILL AN ALREADY-CANCELLED SHIFT
# -------------------------------------------------

@router.post("/entries/{entry_id}/fill")
def fill_cancelled_shift(
    entry_id: UUID,
    request: ReplacementRequest
):
    entry = fetch_one(
        "roster_entries",
        entry_id
    )

    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Shift not found"
        )

    roster = fetch_one(
        "rosters",
        entry["roster_id"]
    )

    if not roster or roster["status"] != "draft":
        raise HTTPException(
            status_code=409,
            detail="Only draft rosters can be edited"
        )

    if entry["status"] != "cancelled":
        raise HTTPException(
            status_code=409,
            detail="This endpoint requires a cancelled shift"
        )

    # Reject if this specific shift already has a replacement.
    # Other employees on the same brand/process slot may
    # be legitimate for multi-resource processes.
    ensure_no_working_replacement(entry_id)

    employees = (
        supabase.table("employees")
        .select("*")
        .eq("employee_code", request.employee_code)
        .limit(1)
        .execute()
        .data
    )

    if not employees:
        raise HTTPException(
            status_code=404,
            detail="Backup employee not found"
        )

    backup = employees[0]

    if backup["id"] == entry["employee_id"]:
        raise HTTPException(
            status_code=409,
            detail="Select a different employee"
        )

    # Check eligibility, leave, working hours,
    # assignments, shifts and weekly offs.
    validate_replacement(entry, backup)

    new_shift = {
        "roster_id": entry["roster_id"],
        "employee_id": backup["id"],
        "brand_process_id": entry["brand_process_id"],
        "work_date": entry["work_date"],
        "start_time": entry["start_time"],
        "end_time": entry["end_time"],
        "status": "working",
        "replaces_entry_id": entry["id"]
    }

    # Database uniqueness check protects against
    # duplicate working replacements.
    new_entry = insert_linked_replacement(
        new_shift
    )

    validation = validate_roster(roster["id"])

    return {
        "message": "Cancelled shift filled successfully",
        "original_entry_id": str(entry_id),
        "new_entry_id": new_entry["id"],
        "backup_employee": backup["name"],
        "status": "working",
        "validation": {
            "total_violations": validation[
                "total_violations"
            ],
            "violation_summary": validation[
                "violation_summary"
            ]
        }
    }
