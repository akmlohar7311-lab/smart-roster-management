
from datetime import date, time
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import supabase
from app.roster_editor import validate_replacement, fetch_all


router = APIRouter(
    prefix="/roster-editor",
    tags=["Roster Editor"]
)


class CreateShiftRequest(BaseModel):
    employee_code: str = Field(min_length=1)
    brand_process_id: UUID
    work_date: date
    start_time: time
    end_time: time


@router.post("/rosters/{roster_id}/shifts", status_code=201)
def create_missing_shift(
    roster_id: UUID,
    request: CreateShiftRequest
):
    """Create a shift for a missing staffing requirement."""

    roster_id_str = str(roster_id)
    bp_id = str(request.brand_process_id)

    day = request.work_date.isoformat()
    start = request.start_time.isoformat(timespec="seconds")
    end = request.end_time.isoformat(timespec="seconds")

    # 1. Verify the roster exists and is editable.
    rosters = (
        supabase.table("rosters")
        .select("*")
        .eq("id", roster_id_str)
        .limit(1)
        .execute()
        .data
    )

    if not rosters:
        raise HTTPException(404, "Roster not found")

    roster = rosters[0]

    if roster["status"] != "draft":
        raise HTTPException(
            409, "Only draft rosters can be edited"
        )

    if str(roster["roster_month"])[:7] != day[:7]:
        raise HTTPException(
            409, "Date does not belong to roster month"
        )

    # 2. Find employee.
    employees = (
        supabase.table("employees")
        .select("*")
        .eq("employee_code", request.employee_code.strip())
        .limit(1)
        .execute()
        .data
    )

    if not employees:
        raise HTTPException(404, "Employee not found")

    employee = employees[0]

    # 3. Find brand-process.
    processes = (
        supabase.table("brand_processes")
        .select("*")
        .eq("id", bp_id)
        .limit(1)
        .execute()
        .data
    )

    if not processes:
        raise HTTPException(404, "Brand-process not found")

    bp = processes[0]

    # 4. Validate shift duration.
    def to_minutes(value):
        h, m, *_ = map(int, value.split(":"))
        return h * 60 + m

    duration = to_minutes(end) - to_minutes(start)

    if duration <= 0:
        raise HTTPException(
            409, "Invalid shift duration"
        )

    if duration != int(bp["daily_minutes"]):
        raise HTTPException(
            409, "Shift duration must equal process daily minutes"
        )

    # 5. Check if staffing requirement is already met.
    def current_coverage():
        return fetch_all(
            supabase.table("roster_entries")
            .select("*")
            .eq("roster_id", roster_id_str)
            .eq("brand_process_id", bp_id)
            .eq("work_date", day)
            .eq("status", "working")
        )

    min_staff = int(bp.get("min_staff") or 1)

    if len(current_coverage()) >= min_staff:
        raise HTTPException(
            409, "Staffing requirement already covered"
        )

    # 6. Reuse existing eligibility validation.
    candidate = {
        "roster_id": roster_id_str,
        "employee_id": employee["id"],
        "brand_process_id": bp_id,
        "work_date": day,
        "start_time": start,
        "end_time": end,
        "status": "working"
    }

    validate_replacement(candidate, employee)

    # 7. Recheck coverage immediately before inserting.
    if len(current_coverage()) >= min_staff:
        raise HTTPException(
            409, "Coverage already filled by another request"
        )

    # 8. Insert new working shift.
    result = (
        supabase.table("roster_entries")
        .insert({
            **candidate,
            "replaces_entry_id": None
        })
        .execute()
    )

    if not result.data:
        raise HTTPException(
            500, "Failed to create shift"
        )

    return {
        "message": "Missing shift created successfully",
        "entry_id": result.data[0]["id"],
        "employee_code": request.employee_code,
        "roster_id": roster_id_str,
        "brand_process_id": bp_id,
        "work_date": day,
        "start_time": start,
        "end_time": end,
        "status": "working"
    }
