
from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from app.database import supabase
from app.validator import validate_roster


router = APIRouter(
    prefix="/leaves",
    tags=["Leave Management"]
)


# ----------------------------------------
# 1. LEAVE REQUEST MODEL
# ----------------------------------------

class LeaveRequest(BaseModel):
    employee_code: str
    start_date: date
    end_date: date
    type: Literal["leave", "comp_off", "unavailable"]
    reason: str = ""

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError(
                "End date cannot be before start date"
            )
        return self


# ----------------------------------------
# 2. REQUEST LEAVE
# ----------------------------------------

@router.post("/request", status_code=201)
def request_leave(request: LeaveRequest):

    employees = (
        supabase.table("employees")
        .select("id,name,active")
        .eq("employee_code", request.employee_code)
        .execute()
        .data
    )

    if not employees:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    employee = employees[0]

    if not employee["active"]:
        raise HTTPException(
            status_code=400,
            detail="Employee is inactive"
        )

    # Prevent overlapping pending or approved leaves.
    existing = (
        supabase.table("time_off")
        .select("id")
        .eq("employee_id", employee["id"])
        .in_("status", ["pending", "approved"])
        .lte(
            "start_date",
            request.end_date.isoformat()
        )
        .gte(
            "end_date",
            request.start_date.isoformat()
        )
        .limit(1)
        .execute()
        .data
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Overlapping leave request already exists"
        )

    new_leave = {
        "employee_id": employee["id"],
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "type": request.type,
        "status": "pending",
        "reason": request.reason
    }

    saved = (
        supabase.table("time_off")
        .insert(new_leave)
        .execute()
        .data
    )

    return {
        "message": "Leave requested successfully",
        "employee": employee["name"],
        "leave": saved[0]
    }


# ----------------------------------------
# 3. VIEW LEAVE REQUESTS
# ----------------------------------------


@router.get("")
def list_leaves():
    leaves = (
        supabase.table("time_off")
        .select("*")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
    )

    employees = (
        supabase.table("employees")
        .select("id,employee_code,name")
        .execute()
        .data
    )

    employee_lookup = {
        e["id"]: e for e in employees
    }

    detailed_leaves = []

    for leave in leaves:
        employee = employee_lookup.get(
            leave["employee_id"], {}
        )

        detailed_leaves.append({
            **leave,
            "employee_code": employee.get(
                "employee_code", "Unknown"
            ),
            "employee_name": employee.get(
                "name", "Unknown"
            )
        })

    return {
        "total_returned": len(detailed_leaves),
        "leaves": detailed_leaves
    }


    leaves = (
        supabase.table("time_off")
        .select("*")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
    )

    return {
        "total_returned": len(leaves),
        "leaves": leaves
    }


# ----------------------------------------
# 4. HELPER: FIND AFFECTED ROSTERS
# ----------------------------------------

def find_affected_rosters(leave):
    """
    Find saved rosters containing this employee's
    shifts during the approved leave period.
    """

    employee_id = leave["employee_id"]
    start_date = leave["start_date"]
    end_date = leave["end_date"]

    # Roster months are stored as YYYY-MM-01.
    first_month = start_date[:7] + "-01"
    last_month = end_date[:7] + "-01"

    possible_rosters = (
        supabase.table("rosters")
        .select("id,roster_month,version,status")
        .gte("roster_month", first_month)
        .lte("roster_month", last_month)
        .order("roster_month")
        .order("version")
        .execute()
        .data
    )

    affected = []

    for roster in possible_rosters:

        # Check whether this employee has a working shift
        # overlapping the new leave dates in this roster.
        matching_entries = (
            supabase.table("roster_entries")
            .select("id")
            .eq("roster_id", roster["id"])
            .eq("employee_id", employee_id)
            .eq("status", "working")
            .gte("work_date", start_date)
            .lte("work_date", end_date)
            .limit(1)
            .execute()
            .data
        )

        if matching_entries:
            affected.append(roster)

    return affected


# ----------------------------------------
# 5. APPROVE LEAVE + AUTO VALIDATE
# ----------------------------------------

@router.patch("/{leave_id}/approve")
def approve_leave(leave_id: UUID):

    leave_id = str(leave_id)

    # Find the pending leave request.
    existing = (
        supabase.table("time_off")
        .select("*")
        .eq("id", leave_id)
        .execute()
        .data
    )

    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Leave request not found"
        )

    leave = existing[0]

    if leave["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail="Only pending leave can be approved"
        )

    # Approve only if still pending.
    updated = (
        supabase.table("time_off")
        .update({"status": "approved"})
        .eq("id", leave_id)
        .eq("status", "pending")
        .execute()
        .data
    )

    if not updated:
        raise HTTPException(
            status_code=409,
            detail="Leave status changed before approval"
        )

    approved_leave = updated[0]

    # ------------------------------------
    # AUTO VALIDATE AFFECTED ROSTERS
    # ------------------------------------

    validation_results = []
    validation_errors = []

    try:
        affected_rosters = find_affected_rosters(
            approved_leave
        )

        for roster in affected_rosters:

            try:
                result = validate_roster(roster["id"])

                validation_results.append({
                    "roster_id": roster["id"],
                    "roster_month": roster["roster_month"],
                    "version": roster["version"],
                    "total_shifts": result["total_shifts"],
                    "total_violations": (
                        result["total_violations"]
                    ),
                    "violation_summary": (
                        result["violation_summary"]
                    )
                })

            except Exception as error:
                print(
                    "ROSTER VALIDATION ERROR:",
                    repr(error)
                )

                validation_errors.append({
                    "roster_id": roster["id"],
                    "message": "Validation failed"
                })

    except Exception as error:
        print(
            "AFFECTED ROSTER LOOKUP ERROR:",
            repr(error)
        )

        validation_errors.append({
            "message": "Could not find affected rosters"
        })

    # The approval has already been saved.
    # Report validation errors separately.
    validation_status = (
        "complete"
        if not validation_errors
        else "incomplete"
    )

    return {
        "message": "Leave approved successfully",
        "leave_id": leave_id,
        "status": "approved",
        "validation_status": validation_status,
        "affected_rosters": validation_results,
        "validation_errors": validation_errors
    }
