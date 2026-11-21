
import logging
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import supabase

router = APIRouter(
    prefix="/assignment-manager",
    tags=["Assignment Management"]
)

logger = logging.getLogger(__name__)


# ------------------------------------------
# REQUEST MODELS
# ------------------------------------------

class AssignmentCreate(BaseModel):
    employee_id: str
    brand_process_id: str
    allocation_percent: float = Field(gt=0, le=100)
    is_primary: bool = False
    start_date: date
    end_date: date | None = None


class AssignmentUpdate(BaseModel):
    brand_process_id: str | None = None
    allocation_percent: float | None = Field(
        default=None, gt=0, le=100
    )
    is_primary: bool | None = None
    start_date: date | None = None
    end_date: date | None = None


class AssignmentEnd(BaseModel):
    end_date: date


# ------------------------------------------
# DATABASE HELPERS
# ------------------------------------------

def load_all(table_name):
    records = []
    start = 0
    page_size = 500

    while True:
        batch = (
            supabase.table(table_name)
            .select("*")
            .order("id")
            .range(start, start + page_size - 1)
            .execute()
            .data
        )

        records.extend(batch)

        if len(batch) < page_size:
            break

        start += page_size

    return records


def get_assignment(assignment_id):
    rows = (
        supabase.table("assignments")
        .select("*")
        .eq("id", assignment_id)
        .limit(1)
        .execute()
        .data
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found"
        )

    return rows[0]


def date_ranges_overlap(a_start, a_end, b_start, b_end):
    # None means the assignment has no end date.
    return (
        (a_end is None or a_end >= b_start)
        and (b_end is None or b_end >= a_start)
    )


def validate_assignment(payload, exclude_id=None):
    start = payload["start_date"]
    end = payload.get("end_date")

    if end is not None and end < start:
        raise HTTPException(
            status_code=400,
            detail="End date cannot precede start date"
        )

    employee_rows = (
        supabase.table("employees")
        .select("id,active")
        .eq("id", payload["employee_id"])
        .limit(1)
        .execute()
        .data
    )

    if not employee_rows:
        raise HTTPException(
            status_code=400,
            detail="Employee does not exist"
        )

    bp_rows = (
        supabase.table("brand_processes")
        .select("id,active")
        .eq("id", payload["brand_process_id"])
        .limit(1)
        .execute()
        .data
    )

    if not bp_rows:
        raise HTTPException(
            status_code=400,
            detail="Brand/process combination does not exist"
        )

    if not bp_rows[0]["active"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot assign an inactive brand/process"
        )

    if not employee_rows[0]["active"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot assign an inactive employee"
        )

    existing = (
        supabase.table("assignments")
        .select(
            "id,brand_process_id,start_date,end_date"
        )
        .eq("employee_id", payload["employee_id"])
        .execute()
        .data
    )

    for row in existing:
        if str(row["id"]) == str(exclude_id):
            continue

        if str(row["brand_process_id"]) != str(
            payload["brand_process_id"]
        ):
            continue

        if date_ranges_overlap(
            start,
            end,
            date.fromisoformat(row["start_date"]),
            (
                date.fromisoformat(row["end_date"])
                if row["end_date"]
                else None
            )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "This employee already has an overlapping "
                    "assignment for the same brand/process"
                )
            )


def as_database_payload(payload):
    result = dict(payload)

    for key in ("start_date", "end_date"):
        if isinstance(result.get(key), date):
            result[key] = result[key].isoformat()

    return result


# ------------------------------------------
# READ: OPTIONS FOR THE REACT FORM
# ------------------------------------------

@router.get("/options")
def get_assignment_options():
    try:
        employees = load_all("employees")
        pods = load_all("pods")
        brands = load_all("brands")
        processes = load_all("processes")
        brand_processes = load_all("brand_processes")

        employee_map = {
            str(e["id"]): e for e in employees
        }
        pod_map = {
            str(p["id"]): p for p in pods
        }
        brand_map = {
            str(b["id"]): b for b in brands
        }
        process_map = {
            str(p["id"]): p for p in processes
        }

        employee_options = []

        for employee in employees:
            pod = pod_map.get(str(employee.get("pod_id")), {})
            lead = employee_map.get(
                str(pod.get("lead_employee_id")), {}
            )

            employee_options.append({
                "id": employee["id"],
                "employee_code": employee["employee_code"],
                "name": employee["name"],
                "active": employee["active"],
                "pod": pod.get("name", "Unassigned"),
                "pod_lead": lead.get("name", "Unassigned")
            })

        process_options = []

        for bp in brand_processes:
            brand = brand_map.get(str(bp["brand_id"]), {})
            process = process_map.get(
                str(bp["process_id"]), {}
            )

            process_options.append({
                "id": bp["id"],
                "brand": brand.get("name", "Unknown"),
                "process": process.get("name", "Unknown"),
                "process_code": process.get("code", ""),
                "active": (
                    bool(bp["active"])
                    and bool(brand.get("active", False))
                )
            })

        employee_options.sort(
            key=lambda item: item["name"]
        )

        process_options.sort(
            key=lambda item: (
                item["brand"], item["process"]
            )
        )

        return {
            "employees": employee_options,
            "brand_processes": process_options
        }

    except Exception:
        logger.exception("Assignment options failed")
        raise HTTPException(
            status_code=502,
            detail="Could not load assignment options"
        )


# ------------------------------------------
# READ: ALL ASSIGNMENTS
# ------------------------------------------

@router.get("")
def list_assignments():
    try:
        rows = load_all("assignments")
        options = get_assignment_options()

        employees = {
            str(e["id"]): e
            for e in options["employees"]
        }

        processes = {
            str(bp["id"]): bp
            for bp in options["brand_processes"]
        }

        result = []

        for row in rows:
            employee = employees.get(
                str(row["employee_id"]), {}
            )

            bp = processes.get(
                str(row["brand_process_id"]), {}
            )

            result.append({
                **row,
                "employee_name": employee.get(
                    "name", "Unknown"
                ),
                "employee_code": employee.get(
                    "employee_code", ""
                ),
                "pod": employee.get(
                    "pod", "Unassigned"
                ),
                "pod_lead": employee.get(
                    "pod_lead", "Unassigned"
                ),
                "brand": bp.get("brand", "Unknown"),
                "process": bp.get("process", "Unknown")
            })

        result.sort(
            key=lambda item: (
                item["employee_name"],
                item["brand"],
                item["process"],
                item["start_date"]
            )
        )

        return {
            "total": len(result),
            "assignments": result
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("List assignments failed")
        raise HTTPException(
            status_code=502,
            detail="Could not load assignments"
        )


# ------------------------------------------
# CREATE: NEW ASSIGNMENT
# ------------------------------------------

@router.post("", status_code=201)
def create_assignment(request: AssignmentCreate):
    payload = request.model_dump()

    validate_assignment(payload)

    try:
        saved = (
            supabase.table("assignments")
            .insert(as_database_payload(payload))
            .execute()
            .data
        )

        if not saved:
            raise HTTPException(
                status_code=502,
                detail="Assignment was not saved"
            )

        return {
            "message": "Assignment created",
            "assignment": saved[0],
            "roster_revalidation_required": True
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Create assignment failed")
        raise HTTPException(
            status_code=502,
            detail="Could not create assignment"
        )


# ------------------------------------------
# UPDATE: EXISTING ASSIGNMENT
# ------------------------------------------

@router.patch("/{assignment_id}")
def update_assignment(
    assignment_id: str,
    request: AssignmentUpdate
):
    original = get_assignment(assignment_id)
    changes = request.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="No changes provided"
        )

    if any(
        key in changes and changes[key] is None
        for key in (
            "brand_process_id",
            "allocation_percent",
            "is_primary",
            "start_date"
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Required fields cannot be null"
        )

    merged = {
        "employee_id": original["employee_id"],
        "brand_process_id": changes.get(
            "brand_process_id",
            original["brand_process_id"]
        ),
        "allocation_percent": changes.get(
            "allocation_percent",
            original["allocation_percent"]
        ),
        "is_primary": changes.get(
            "is_primary",
            original["is_primary"]
        ),
        "start_date": changes.get(
            "start_date",
            date.fromisoformat(original["start_date"])
        ),
        "end_date": changes.get(
            "end_date",
            (
                date.fromisoformat(original["end_date"])
                if original.get("end_date")
                else None
            )
        )
    }

    validate_assignment(
        merged,
        exclude_id=assignment_id
    )

    try:
        saved = (
            supabase.table("assignments")
            .update(as_database_payload(changes))
            .eq("id", assignment_id)
            .execute()
            .data
        )

        if not saved:
            raise HTTPException(
                status_code=404,
                detail="Assignment not found during update"
            )

        return {
            "message": "Assignment updated",
            "assignment": saved[0],
            "roster_revalidation_required": True
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Update assignment failed")
        raise HTTPException(
            status_code=502,
            detail="Could not update assignment"
        )


# ------------------------------------------
# END: ASSIGNMENT WITHOUT DELETING HISTORY
# ------------------------------------------

@router.post("/{assignment_id}/end")
def end_assignment(
    assignment_id: str,
    request: AssignmentEnd
):
    original = get_assignment(assignment_id)

    start = date.fromisoformat(
        original["start_date"]
    )

    if request.end_date < start:
        raise HTTPException(
            status_code=400,
            detail="End date cannot precede start date"
        )

    if original.get("end_date"):
        existing_end = date.fromisoformat(
            original["end_date"]
        )

        if request.end_date > existing_end:
            raise HTTPException(
                status_code=400,
                detail=(
                    "This assignment already ends earlier. "
                    "Use Edit to change its dates."
                )
            )

    try:
        saved = (
            supabase.table("assignments")
            .update({
                "end_date": request.end_date.isoformat()
            })
            .eq("id", assignment_id)
            .execute()
            .data
        )

        if not saved:
            raise HTTPException(
                status_code=404,
                detail="Assignment not found during update"
            )

        return {
            "message": "Assignment ended",
            "assignment": saved[0],
            "roster_revalidation_required": True
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("End assignment failed")
        raise HTTPException(
            status_code=502,
            detail="Could not end assignment"
        )
