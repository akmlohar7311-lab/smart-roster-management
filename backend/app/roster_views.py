
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.database import supabase


router = APIRouter(
    prefix="/roster-view",
    tags=["Roster Views"]
)


# -------------------------------------------------
# 1. LOAD ALL RECORDS FROM A TABLE
# -------------------------------------------------

def load_all(table_name):
    """
    Load records from Supabase using pagination.
    This avoids the default 1000-row limit.
    """
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


# -------------------------------------------------
# 2. LOAD ALL ENTRIES FOR A SPECIFIC ROSTER
# -------------------------------------------------

def load_roster_entries(roster_id):
    """
    Fetch every shift belonging to one roster.
    """
    records = []
    start = 0
    page_size = 500

    while True:
        batch = (
            supabase.table("roster_entries")
            .select("*")
            .eq("roster_id", str(roster_id))
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


# -------------------------------------------------
# 3. GET MONTHLY ROSTER
# -------------------------------------------------

@router.get("/monthly")
def get_monthly_roster(
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    version: int | None = Query(default=None, ge=1)
):
    """
    Return a readable monthly roster with:

    - Employee details
    - Pod name
    - Brand name
    - Process name and code
    - Shift date and time
    - Working/cancelled status
    - Original shift ID for replacements

    If version is not supplied, the latest
    saved roster version is returned.
    """

    roster_month = date(year, month, 1).isoformat()

    # ---------------------------------------------
    # Find the requested roster.
    # ---------------------------------------------

    query = (
        supabase.table("rosters")
        .select("id,roster_month,version,status")
        .eq("roster_month", roster_month)
    )

    if version is not None:
        query = query.eq("version", version)

    rosters = (
        query.order("version", desc=True)
        .limit(1)
        .execute()
        .data
    )

    if not rosters:
        raise HTTPException(
            status_code=404,
            detail="No roster found for this month/version"
        )

    roster = rosters[0]
    roster_id = roster["id"]

    # ---------------------------------------------
    # Load all related database records.
    # ---------------------------------------------

    entries = load_roster_entries(roster_id)
    employees = load_all("employees")
    pods = load_all("pods")
    brands = load_all("brands")
    processes = load_all("processes")
    brand_processes = load_all("brand_processes")

    # ---------------------------------------------
    # Create lookup dictionaries for fast joins.
    # ---------------------------------------------

    employee_map = {
        employee["id"]: employee
        for employee in employees
    }

    pod_map = {
        pod["id"]: pod
        for pod in pods
    }

    brand_map = {
        brand["id"]: brand
        for brand in brands
    }

    process_map = {
        process["id"]: process
        for process in processes
    }

    bp_map = {
        bp["id"]: bp
        for bp in brand_processes
    }

    # ---------------------------------------------
    # Convert UUID-based records into readable rows.
    # ---------------------------------------------

    result = []

    for entry in entries:

        employee = employee_map.get(
            entry["employee_id"], {}
        )

        bp = bp_map.get(
            entry["brand_process_id"], {}
        )

        brand = brand_map.get(
            bp.get("brand_id"), {}
        )

        process = process_map.get(
            bp.get("process_id"), {}
        )

        pod = pod_map.get(
            employee.get("pod_id"), {}
        )

        result.append({
            "entry_id": entry["id"],

            # IMPORTANT:
            # Connect a replacement to its original shift.
            "replaces_entry_id": entry.get(
                "replaces_entry_id"
            ),

            "employee_code": employee.get(
                "employee_code", "Unknown"
            ),

            "employee_name": employee.get(
                "name", "Unknown"
            ),

            "pod": pod.get(
                "name", "Unassigned"
            ),

            "brand": brand.get(
                "name", "Unknown"
            ),

            "process": process.get(
                "name", "Unknown"
            ),

            "process_code": process.get(
                "code", ""
            ),

            "work_date": entry["work_date"],

            "start_time": entry["start_time"],

            "end_time": entry["end_time"],

            "status": entry["status"]
        })

    # ---------------------------------------------
    # Sort by date, start time and employee code.
    # ---------------------------------------------

    result.sort(
        key=lambda item: (
            item["work_date"],
            item["start_time"],
            item["employee_code"]
        )
    )

    # ---------------------------------------------
    # Calculate roster statistics.
    # ---------------------------------------------

    total_entries = len(result)

    working_shifts = sum(
        item["status"] == "working"
        for item in result
    )

    cancelled_shifts = sum(
        item["status"] == "cancelled"
        for item in result
    )

    linked_replacements = sum(
        item["status"] == "working"
        and item["replaces_entry_id"] is not None
        for item in result
    )

    # ---------------------------------------------
    # Return the monthly roster to React.
    # ---------------------------------------------

    return {
        "roster_id": roster_id,
        "roster_month": roster["roster_month"],
        "version": roster["version"],
        "status": roster["status"],
        "total_entries": total_entries,
        "working_shifts": working_shifts,
        "cancelled_shifts": cancelled_shifts,
        "linked_replacements": linked_replacements,
        "entries": result
    }
