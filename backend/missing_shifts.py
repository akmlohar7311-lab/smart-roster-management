
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
    """
    Create a new shift for an uncovered roster requirement.

    Reuses existing employee eligibility validation.
    Does not modify or cancel existing shifts.
    """

    roster_id_str = str(roster_id)
    bp_id = str(request.brand_process_id)

    day = request.work_date.isoformat()

    start = request.start_time.isoformat(
        timespec="seconds"
    )

    end = request.end_time.isoformat(
        timespec="seconds"
    )

    # --------------------------------------------
    # 1. Check roster exists and is editable
    # --------------------------------------------

    rosters = (
        supabase.table("rosters")
        .select("*")
        .eq("id", roster_id_str)
        .limit(1)
        .execute()
        .data
    )

    if not rosters:
        raise HTTPException(
            status_code=404,
            detail="Roster not found"
        )

    roster = rosters[0]

    if roster["status"] != "draft":
        raise HTTPException(
            status_code=409,
            detail="Only draft rosters can be edited"
        )

    if str(roster["roster_month"])[:7] != day[:7]:
        raise HTTPException(
            status_code=409,
            detail="Shift date does not belong to roster month"
        )

    # --------------------------------------------
    # 2. Check employee exists
    # --------------------------------------------

    employees = (
        supabase.table("employees")
        .select("*")
        .eq(
            "employee_code",
            request.employee_code.strip()
        )
        .limit(1)
        .execute()
        .data
    )

    if not employees:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    employee = employees[0]

    # --------------------------------------------
    # 3. Check brand-process exists
    # --------------------------------------------

    brand_processes = (
        supabase.table("brand_processes")
        .select("*")
        .eq("id", bp_id)
        .limit(1)
        .execute()
        .data
    )

    if not brand_processes:
        raise HTTPException(
            status_code=404,
            detail="Brand-process not found"
        )

    bp = brand_processes[0]

    # --------------------------------------------
    # 4. Check shift length
    # --------------------------------------------

    def to_minutes(value):
        parts = value.split(":")
        return (
            int(parts[0]) * 60
            + int(parts[1])
        )

    duration = to_minutes(end) - to_minutes(start)

    if duration <= 0:
        raise HTTPException(
            status_code=409,
            detail="End time must be after start time"
        )

    required_minutes = bp.get("daily_minutes")

    if required_minutes is not None:
        if duration != int(required_minutes):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Shift duration must equal the "
                    "configured daily process minutes"
                )
            )

    # --------------------------------------------
    # 5. Confirm a coverage gap exists
    # --------------------------------------------

    existing_coverage = fetch_all(
        supabase.table("roster_entries")
        .select("*")
        .eq("roster_id", roster_id_str)
        .eq("brand_process_id", bp_id)
        .eq("work_date", day)
        .eq("status", "working")
    )

    minimum_staff = int(bp.get("min_staff") or 1)

    if len(existing_coverage) >= minimum_staff:
        raise HTTPException(
            status_code=409,
            detail=(
                "Required staffing coverage already exists "
                "for this brand-process and date"
            )
        )

    # --------------------------------------------
    # 6. Reuse existing replacement validation
    # --------------------------------------------

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

    # --------------------------------------------
    # 7. Check coverage again before inserting
    # --------------------------------------------

    latest_coverage = fetch_all(
        supabase.table("roster_entries")
        .select("*")
        .eq("roster_id", roster_id_str)
        .eq("brand_process_id", bp_id)
        .eq("work_date", day)
        .eq("status", "working")
    )

    if len(latest_coverage) >= minimum_staff:
        raise HTTPException(
            status_code=409,
            detail="Coverage was filled by another request"
        )

    # --------------------------------------------
    # 8. Create working shift
    # --------------------------------------------

    payload = {
        **candidate,
        "replaces_entry_id": None
    }

    result = (
        supabase.table("roster_entries")
        .insert(payload)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=500,
            detail="Shift could not be created"
        )

    created = result.data[0]

    return {
        "message": "Missing shift created successfully",
        "entry_id": created["id"],
        "roster_id": roster_id_str,
        "employee_code": request.employee_code,
        "brand_process_id": bp_id,
        "work_date": day,
        "start_time": start,
        "end_time": end,
        "status": "working"
    }
