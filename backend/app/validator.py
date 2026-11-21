
from collections import defaultdict
from calendar import monthrange
from datetime import date

from app.database import supabase


# ============================================
# 1. DATABASE HELPERS
# ============================================

def load_table(table_name):
    """
    Load all records using pagination.
    Supabase may limit the number of rows
    returned in a single request.
    """
    all_rows = []
    page_size = 500
    start = 0

    while True:
        batch = (
            supabase.table(table_name)
            .select("*")
            .order("id")
            .range(start, start + page_size - 1)
            .execute()
            .data
        )

        all_rows.extend(batch)

        if len(batch) < page_size:
            break

        start += page_size

    return all_rows


def load_roster_entries(roster_id):
    """Load ALL entries belonging to one roster."""
    entries = []
    page_size = 500
    start = 0

    while True:
        batch = (
            supabase.table("roster_entries")
            .select("*")
            .eq("roster_id", roster_id)
            .order("id")
            .range(start, start + page_size - 1)
            .execute()
            .data
        )

        entries.extend(batch)

        if len(batch) < page_size:
            break

        start += page_size

    return entries


def time_to_minutes(value):
    """Convert PostgreSQL TIME to minutes."""
    hour, minute = map(
        int, str(value).split(":")[:2]
    )

    return hour * 60 + minute


def rule_active(rule, day):
    """Check whether a weekly-off rule is active."""
    return (
        rule["effective_from"] <= day
        and (
            rule["effective_to"] is None
            or rule["effective_to"] >= day
        )
    )


# ============================================
# 2. MAIN VALIDATOR
# ============================================

def validate_roster(roster_id):
    """
    Independently validate an existing roster.

    Returns all detected violations without
    modifying the saved roster.
    """

    # STEP 1: Find the roster.
    roster_rows = (
        supabase.table("rosters")
        .select("*")
        .eq("id", roster_id)
        .execute()
        .data
    )

    if not roster_rows:
        raise ValueError("Roster not found")

    roster = roster_rows[0]

    # STEP 2: Load complete scheduling data.
    entries = load_roster_entries(roster_id)

    employees = load_table("employees")
    brands = load_table("brands")
    processes = load_table("processes")
    brand_processes = load_table("brand_processes")
    assignments = load_table("assignments")
    weekly_offs = load_table("weekly_offs")
    leaves = load_table("time_off")
    holidays = load_table("holidays")
    overrides = load_table("coverage_overrides")
    shifts = load_table("shift_templates")

    # Create lookup dictionaries.
    employee_map = {
        employee["id"]: employee
        for employee in employees
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

    shift_map = {
        shift["id"]: shift
        for shift in shifts
    }

    # Group records for faster lookup.
    assignments_by_pair = defaultdict(list)

    for assignment in assignments:
        key = (
            assignment["employee_id"],
            assignment["brand_process_id"]
        )
        assignments_by_pair[key].append(assignment)

    leaves_by_employee = defaultdict(list)

    for leave in leaves:
        leaves_by_employee[
            leave["employee_id"]
        ].append(leave)

    offs_by_employee = defaultdict(list)

    for off in weekly_offs:
        offs_by_employee[
            off["employee_id"]
        ].append(off)

    holiday_set = {
        (
            holiday["holiday_date"],
            holiday["calendar_code"]
        )
        for holiday in holidays
    }

    override_map = {
        (
            override["brand_process_id"],
            override["work_date"]
        ): override["required_staff"]
        for override in overrides
    }

    # Store validation results.
    violations = []

    # Tracks shifts for each employee on each day.
    employee_days = defaultdict(list)

    # Tracks distinct staff covering each process/day.
    coverage = defaultdict(set)

    # Tracks assigned time for each employee/process/day.
    process_minutes = defaultdict(int)

    # STEP 3: Check all saved working shifts.
    for entry in entries:

        if entry["status"] != "working":
            continue

        employee_id = entry["employee_id"]
        bp_id = entry["brand_process_id"]
        day = entry["work_date"]

        employee = employee_map.get(employee_id)
        bp = bp_map.get(bp_id)

        if employee is None or bp is None:
            violations.append({
                "type": "missing_reference",
                "date": day,
                "employee_id": employee_id,
                "message": (
                    "Referenced employee or process "
                    "could not be found"
                )
            })
            continue

        employee_name = employee["name"]

        employee_days[
            (employee_id, day)
        ].append(entry)

        coverage[
            (bp_id, day)
        ].add(employee_id)

        start = time_to_minutes(entry["start_time"])
        end = time_to_minutes(entry["end_time"])

        duration = end - start

        process_minutes[
            (employee_id, bp_id, day)
        ] += duration

        # CHECK A: Shift times.
        if duration <= 0:
            violations.append({
                "type": "invalid_shift",
                "date": day,
                "employee": employee_name,
                "message": "Shift end must be after start"
            })

        # CHECK B: Approved leave and comp-offs.
        on_leave = any(
            leave["status"] == "approved"
            and leave["start_date"] <= day
            and leave["end_date"] >= day
            for leave in leaves_by_employee[employee_id]
        )

        if on_leave:
            violations.append({
                "type": "leave_violation",
                "date": day,
                "employee": employee_name,
                "message": (
                    "Employee scheduled during an "
                    "approved absence"
                )
            })

        # CHECK C: Fixed weekly offs.
        weekday = date.fromisoformat(day).isoweekday()

        fixed_off = any(
            off["day_of_week"] == weekday
            and off["rule_type"] == "fixed"
            and rule_active(off, day)
            for off in offs_by_employee[employee_id]
        )

        if fixed_off:
            violations.append({
                "type": "fixed_off_violation",
                "date": day,
                "employee": employee_name,
                "message": (
                    "Employee scheduled on a fixed "
                    "weekly-off day"
                )
            })

        # CHECK D: Active employee.
        if not employee["active"]:
            violations.append({
                "type": "inactive_employee",
                "date": day,
                "employee": employee_name,
                "message": "Inactive employee scheduled"
            })

        # CHECK E: Valid assignment.
        matching_assignments = [
            assignment
            for assignment in assignments_by_pair[
                (employee_id, bp_id)
            ]
            if assignment["start_date"] <= day
            and (
                assignment["end_date"] is None
                or assignment["end_date"] >= day
            )
        ]

        if not matching_assignments:
            violations.append({
                "type": "invalid_assignment",
                "date": day,
                "employee": employee_name,
                "message": (
                    "Employee has no active assignment "
                    "for this process"
                )
            })
        else:
            # Check total duration against allocation.
            allocation_limit = max(
                round(
                    employee["max_daily_minutes"]
                    * float(
                        assignment["allocation_percent"]
                    ) / 100
                )
                for assignment in matching_assignments
            )

            allocated_minutes = process_minutes[
                (employee_id, bp_id, day)
            ]

            if allocated_minutes > allocation_limit:
                violations.append({
                    "type": "allocation_exceeded",
                    "date": day,
                    "employee": employee_name,
                    "message": (
                        f"Assigned {allocated_minutes} "
                        f"minutes, allocation limit "
                        f"{allocation_limit}"
                    )
                })

        # CHECK F: Process operating day.
        if weekday not in bp["operating_days"]:
            violations.append({
                "type": "non_operating_day",
                "date": day,
                "employee": employee_name,
                "message": (
                    "Employee scheduled on a day "
                    "when process is closed"
                )
            })

        # CHECK G: Process holiday.
        holiday_key = (
            day,
            bp["holiday_calendar_code"]
        )

        if (
            holiday_key in holiday_set
            and not bp["works_on_holidays"]
        ):
            violations.append({
                "type": "holiday_violation",
                "date": day,
                "employee": employee_name,
                "message": (
                    "Employee scheduled on a "
                    "non-working process holiday"
                )
            })

        # CHECK H: Configured shift window.
        shift = shift_map.get(
            bp["shift_template_id"]
        )

        if shift is not None:
            allowed_start = time_to_minutes(
                shift["start_time"]
            )
            allowed_end = time_to_minutes(
                shift["end_time"]
            )

            if start < allowed_start or end > allowed_end:
                violations.append({
                    "type": "outside_shift_window",
                    "date": day,
                    "employee": employee_name,
                    "message": (
                        "Scheduled hours fall outside "
                        "the configured shift window"
                    )
                })

    # ============================================
    # STEP 4: DAILY WORKING-HOUR CHECKS
    # ============================================

    for key, daily_entries in employee_days.items():
        employee_id, day = key

        employee = employee_map[employee_id]

        periods = sorted(
            (
                time_to_minutes(e["start_time"]),
                time_to_minutes(e["end_time"])
            )
            for e in daily_entries
        )

        total_minutes = sum(
            end - start
            for start, end in periods
        )

        # CHECK I: Daily work limit.
        if total_minutes > employee["max_daily_minutes"]:
            violations.append({
                "type": "daily_hours_exceeded",
                "date": day,
                "employee": employee["name"],
                "message": (
                    f"Scheduled {total_minutes} minutes; "
                    f"limit {employee['max_daily_minutes']}"
                )
            })

        # CHECK J: Overlapping shifts.
        latest_end = -1

        for start, end in periods:
            if start < latest_end:
                violations.append({
                    "type": "overlapping_shifts",
                    "date": day,
                    "employee": employee["name"],
                    "message": (
                        "Employee has overlapping shifts"
                    )
                })

            latest_end = max(latest_end, end)

    # ============================================
    # STEP 5: MINIMUM STAFFING COVERAGE
    # ============================================

    first_day = date.fromisoformat(
        roster["roster_month"]
    )

    year = first_day.year
    month = first_day.month

    total_days = monthrange(year, month)[1]

    for day_number in range(1, total_days + 1):
        current_date = date(
            year, month, day_number
        )

        day = current_date.isoformat()
        weekday = current_date.isoweekday()

        for bp in brand_processes:
            brand = brand_map.get(
                bp["brand_id"]
            )

            if brand is None:
                continue

            if not brand["active"] or not bp["active"]:
                continue

            if weekday not in bp["operating_days"]:
                continue

            holiday_key = (
                day,
                bp["holiday_calendar_code"]
            )

            if (
                holiday_key in holiday_set
                and not bp["works_on_holidays"]
            ):
                continue

            required_staff = override_map.get(
                (bp["id"], day),
                bp["min_staff"]
            )

            scheduled_staff = len(
                coverage[(bp["id"], day)]
            )

            if scheduled_staff < required_staff:
                violations.append({
                    "type": "insufficient_coverage",
                    "date": day,
                    "brand": brand["name"],
                    "process": process_map.get(
                        bp["process_id"], {}
                    ).get("name", "Unknown"),
                    "message": (
                        f"Required {required_staff}, "
                        f"scheduled {scheduled_staff}"
                    )
                })

    # ============================================
    # STEP 6: SUMMARIZE VALIDATION RESULTS
    # ============================================

    violation_counts = defaultdict(int)

    for violation in violations:
        violation_counts[violation["type"]] += 1

    return {
        "roster_id": roster_id,
        "roster_month": roster["roster_month"],
        "version": roster["version"],
        "total_shifts": len(entries),
        "total_violations": len(violations),
        "violation_summary": dict(violation_counts),
        "violations": violations
    }
