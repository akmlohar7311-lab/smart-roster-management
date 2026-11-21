
from calendar import monthrange
from datetime import date

from app.database import supabase


# ---------------------------------------
# 1. DATABASE HELPERS
# ---------------------------------------

def load_table(table_name):
    """Read every row, including beyond Supabase's page limit."""
    rows = []
    page_size = 500
    start = 0

    while True:
        batch = (
            supabase.table(table_name)
            .select("*")
            .range(start, start + page_size - 1)
            .execute()
            .data
        )

        rows.extend(batch)

        if len(batch) < page_size:
            break

        start += page_size

    return rows


def save_batches(table_name, records, batch_size=100):
    """Save records in small groups."""
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]

        supabase.table(table_name).insert(batch).execute()


# ---------------------------------------
# 2. DATE AND TIME HELPERS
# ---------------------------------------

def to_minutes(time_value):
    """Convert '10:30:00' into minutes from midnight."""
    hour, minute = map(int, str(time_value).split(":")[:2])
    return hour * 60 + minute


def to_clock(total_minutes):
    """Convert minutes into 'HH:MM:SS'."""
    hours = total_minutes // 60
    minutes = total_minutes % 60

    return f"{hours:02d}:{minutes:02d}:00"


def is_active_assignment(assignment, day):
    """Check whether an employee's assignment is active."""
    return (
        assignment["start_date"] <= day
        and (
            assignment["end_date"] is None
            or assignment["end_date"] >= day
        )
    )


def is_on_leave(employee_id, day, leaves):
    """Check approved leave, comp-off, or unavailability."""
    for leave in leaves:
        if leave["employee_id"] != employee_id:
            continue

        if leave["status"] != "approved":
            continue

        if leave["start_date"] <= day <= leave["end_date"]:
            return True

    return False


def get_weekly_off(employee_id, day, weekday, weekly_offs):
    """Return 'fixed', 'preferred', or None."""
    preferred = False

    for off in weekly_offs:
        if off["employee_id"] != employee_id:
            continue

        if off["day_of_week"] != weekday:
            continue

        if off["effective_from"] > day:
            continue

        if (
            off["effective_to"] is not None
            and off["effective_to"] < day
        ):
            continue

        if off["rule_type"] == "fixed":
            return "fixed"

        if off["rule_type"] == "preferred":
            preferred = True

    return "preferred" if preferred else None


def find_free_slot(existing, start, end, duration):
    """Find available time without overlapping shifts."""

    if duration <= 0 or end - start < duration:
        return None

    for candidate in range(start, end - duration + 1, 15):
        finish = candidate + duration

        overlaps = any(
            candidate < old_end
            and finish > old_start
            for old_start, old_end in existing
        )

        if not overlaps:
            return candidate, finish

    return None


# ---------------------------------------
# 3. MAIN ROSTER GENERATOR
# ---------------------------------------

def generate_roster(year, month):
    """
    Generate and save a monthly draft roster.
    """

    # STEP 1: Validate inputs
    if not 2000 <= year <= 2100:
        raise ValueError("Invalid year")

    if not 1 <= month <= 12:
        raise ValueError("Month must be between 1 and 12")

    roster_month = f"{year:04d}-{month:02d}-01"

    print(f"Generating roster for {roster_month}")

    # STEP 2: Fetch database records
    employees = load_table("employees")
    brands = load_table("brands")
    processes = load_table("processes")
    brand_processes = load_table("brand_processes")
    assignments = load_table("assignments")
    shift_templates = load_table("shift_templates")
    weekly_offs = load_table("weekly_offs")
    holidays = load_table("holidays")
    leaves = load_table("time_off")
    coverage_overrides = load_table("coverage_overrides")

    # Create lookup dictionaries
    employee_map = {e["id"]: e for e in employees}
    brand_map = {b["id"]: b for b in brands}
    process_map = {p["id"]: p for p in processes}
    shift_map = {s["id"]: s for s in shift_templates}

    if not employees or not brand_processes:
        raise ValueError(
            "Missing employees or brand-process configuration"
        )

    # Group assignments by brand-process
    assignments_by_process = {}

    for assignment in assignments:
        process_id = assignment["brand_process_id"]

        assignments_by_process.setdefault(
            process_id, []
        ).append(assignment)

    # Group absences by employee
    leaves_by_employee = {}

    for leave in leaves:
        leaves_by_employee.setdefault(
            leave["employee_id"], []
        ).append(leave)

    # Group weekly-off rules by employee
    offs_by_employee = {}

    for off in weekly_offs:
        offs_by_employee.setdefault(
            off["employee_id"], []
        ).append(off)

    holiday_set = {
        (h["holiday_date"], h["calendar_code"])
        for h in holidays
    }

    override_map = {
        (o["brand_process_id"], o["work_date"]):
            o["required_staff"]
        for o in coverage_overrides
    }

    entries = []
    conflicts = []

    # Key: (employee_id, date)
    # Value: list of scheduled time intervals
    employee_busy = {}

    # Total minutes assigned to employee on a date
    employee_minutes = {}

    # Track minutes assigned to each particular assignment
    assignment_minutes = {}

    total_days = monthrange(year, month)[1]

    # STEP 3: Loop through every day
    for day_number in range(1, total_days + 1):
        current_date = date(year, month, day_number)

        day = current_date.isoformat()
        weekday = current_date.isoweekday()

        # STEP 4: Loop through every brand-process
        for bp in sorted(
            brand_processes,
            key=lambda item: (
                brand_map[item["brand_id"]]["name"],
                process_map[item["process_id"]]["code"]
            )
        ):
            brand = brand_map[bp["brand_id"]]
            process = process_map[bp["process_id"]]

            # Skip inactive configurations
            if not bp["active"] or not brand["active"]:
                continue

            # Skip non-operating days
            if weekday not in bp["operating_days"]:
                continue

            # Check holidays
            is_holiday = (
                day,
                bp["holiday_calendar_code"]
            ) in holiday_set

            if is_holiday and not bp["works_on_holidays"]:
                continue

            # Determine required staffing
            required_staff = override_map.get(
                (bp["id"], day),
                bp["min_staff"]
            )

            if required_staff == 0:
                continue

            # Check shift template
            shift = shift_map.get(bp["shift_template_id"])

            if shift is None:
                conflicts.append({
                    "work_date": day,
                    "brand_process_id": bp["id"],
                    "employee_id": None,
                    "conflict_type": "missing_shift",
                    "severity": "error",
                    "message": (
                        f"{brand['name']} / {process['code']}: "
                        "No shift template configured"
                    )
                })
                continue

            shift_start = to_minutes(shift["start_time"])
            shift_end = to_minutes(shift["end_time"])

            required_duration = bp["daily_minutes"]

            if shift_end - shift_start < required_duration:
                conflicts.append({
                    "work_date": day,
                    "brand_process_id": bp["id"],
                    "employee_id": None,
                    "conflict_type": "invalid_shift_duration",
                    "severity": "error",
                    "message": (
                        f"{brand['name']} / {process['code']}: "
                        "Shift window is too short"
                    )
                })
                continue

            # STEP 5: Find eligible employees
            candidates = []

            process_assignments = (
                assignments_by_process.get(bp["id"], [])
            )

            for assignment in process_assignments:
                if not is_active_assignment(assignment, day):
                    continue

                employee = employee_map.get(
                    assignment["employee_id"]
                )

                if employee is None or not employee["active"]:
                    continue

                employee_id = employee["id"]

                if is_on_leave(
                    employee_id,
                    day,
                    leaves_by_employee.get(employee_id, [])
                ):
                    continue

                off_type = get_weekly_off(
                    employee_id,
                    day,
                    weekday,
                    offs_by_employee.get(employee_id, [])
                )

                if off_type == "fixed":
                    continue

                candidates.append({
                    "employee": employee,
                    "assignment": assignment,
                    "off_type": off_type
                })

            # Prefer staff without an off preference
            candidates.sort(
                key=lambda candidate: (
                    candidate["off_type"] == "preferred",
                    candidate["employee"]["employee_code"]
                )
            )

            # STEP 6: Schedule available employees
            scheduled_count = 0
            scheduled_ids = set()

            for candidate in candidates:
                if scheduled_count >= required_staff:
                    break

                employee = candidate["employee"]
                assignment = candidate["assignment"]

                employee_id = employee["id"]

                # Don't count the same employee twice
                # for the same brand-process on one day.
                if employee_id in scheduled_ids:
                    continue

                day_key = (employee_id, day)

                busy_slots = employee_busy.setdefault(
                    day_key, []
                )

                used_minutes = employee_minutes.get(
                    day_key, 0
                )

                daily_limit = employee["max_daily_minutes"]

                allocation_percent = float(
                    assignment["allocation_percent"]
                )

                # Daily allocation limit for this assignment
                allocation_limit = round(
                    daily_limit * allocation_percent / 100
                )

                allocation_key = (assignment["id"], day)

                already_allocated = assignment_minutes.get(
                    allocation_key, 0
                )

                # Initial scheduler: one employee must cover
                # the full configured process duration.
                duration = required_duration

                if already_allocated + duration > allocation_limit:
                    continue

                if used_minutes + duration > daily_limit:
                    continue

                # Find a free time interval
                slot = find_free_slot(
                    busy_slots,
                    shift_start,
                    shift_end,
                    duration
                )

                if slot is None:
                    continue

                start, finish = slot

                # Create roster entry
                entries.append({
                    "employee_id": employee_id,
                    "brand_process_id": bp["id"],
                    "work_date": day,
                    "start_time": to_clock(start),
                    "end_time": to_clock(finish),
                    "status": "working"
                })

                busy_slots.append((start, finish))

                employee_minutes[day_key] = (
                    used_minutes + duration
                )

                assignment_minutes[allocation_key] = (
                    already_allocated + duration
                )

                scheduled_ids.add(employee_id)
                scheduled_count += 1

                # Warn if a preferred off is used
                if candidate["off_type"] == "preferred":
                    conflicts.append({
                        "work_date": day,
                        "brand_process_id": bp["id"],
                        "employee_id": employee_id,
                        "conflict_type": "preferred_off_used",
                        "severity": "warning",
                        "message": (
                            f"{employee['name']} scheduled on "
                            "a preferred weekly-off day"
                        )
                    })

            # STEP 7: Record missing coverage
            if scheduled_count < required_staff:
                shortage = required_staff - scheduled_count

                conflicts.append({
                    "work_date": day,
                    "brand_process_id": bp["id"],
                    "employee_id": None,
                    "conflict_type": "insufficient_coverage",
                    "severity": "error",
                    "message": (
                        f"{brand['name']} / {process['code']}: "
                        f"Required {required_staff}, "
                        f"scheduled {scheduled_count}, "
                        f"shortage {shortage}"
                    )
                })

    # ---------------------------------------
    # 4. SAVE THE GENERATED ROSTER
    # ---------------------------------------

    # Determine next roster version
    existing_rosters = (
        supabase.table("rosters")
        .select("version")
        .eq("roster_month", roster_month)
        .order("version", desc=True)
        .limit(1)
        .execute()
        .data
    )

    version = (
        existing_rosters[0]["version"] + 1
        if existing_rosters else 1
    )

    # Create roster header
    created = (
        supabase.table("rosters")
        .insert({
            "roster_month": roster_month,
            "version": version,
            "status": "draft"
        })
        .execute()
        .data
    )

    if not created:
        raise RuntimeError("Could not create roster record")

    roster_id = created[0]["id"]

    try:
        # Save working shifts
        entry_records = [
            {"roster_id": roster_id, **entry}
            for entry in entries
        ]

        save_batches("roster_entries", entry_records)

        # Save conflicts
        conflict_records = [
            {"roster_id": roster_id, **conflict}
            for conflict in conflicts
        ]

        save_batches("conflicts", conflict_records)

    except Exception:
        # Remove incomplete roster, including entries
        # and conflicts via ON DELETE CASCADE.
        supabase.table("rosters").delete().eq(
            "id", roster_id
        ).execute()

        raise

    # ---------------------------------------
    # 5. RETURN THE API RESULT
    # ---------------------------------------

    result = {
        "message": "Roster generated successfully",
        "roster_id": roster_id,
        "month": roster_month,
        "version": version,
        "status": "draft",
        "total_shifts": len(entries),
        "total_conflicts": len(conflicts),
        "errors": sum(
            c["severity"] == "error"
            for c in conflicts
        ),
        "warnings": sum(
            c["severity"] == "warning"
            for c in conflicts
        )
    }

    print("Roster generation finished:", result)

    return result
