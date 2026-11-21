
from app.database import supabase

EMPLOYEE_CODE = "EMP031"

PLANS = [
    {
        "name": "MegaMart ACC",
        "brand_process_id": "0ee87929-23ef-4bc2-9caa-13a9ab6f9d60",
        "start_date": "2026-12-15",
        "end_date": "2026-12-15",
    },
    {
        "name": "PrimeNest NDR",
        "brand_process_id": "be6fb375-2646-42ef-9bb2-5a0a68401a06",
        "start_date": "2026-12-22",
        "end_date": "2026-12-23",
    },
]


def main():
    rows = (
        supabase.table("employees")
        .select("id,name,active,max_daily_minutes")
        .eq("employee_code", EMPLOYEE_CODE)
        .execute()
        .data
    )

    if not rows or not rows[0]["active"]:
        print("STOP: Employee missing or inactive")
        return

    employee = rows[0]
    employee_id = employee["id"]

    if employee["max_daily_minutes"] < 480:
        print("STOP: Employee daily limit below 480 minutes")
        return

    # Preflight both assignments before any insert.
    existing = (
        supabase.table("assignments")
        .select("*")
        .eq("employee_id", employee_id)
        .lte("start_date", "2026-12-23")
        .execute()
        .data
    )

    pending = []

    for plan in PLANS:
        overlapping = [
            a for a in existing
            if a["start_date"] <= plan["end_date"]
            and (
                a["end_date"] is None
                or a["end_date"] >= plan["start_date"]
            )
        ]

        exact = [
            a for a in overlapping
            if a["brand_process_id"] == plan["brand_process_id"]
            and a["start_date"] <= plan["start_date"]
            and (
                a["end_date"] is None
                or a["end_date"] >= plan["end_date"]
            )
            and float(a["allocation_percent"]) == 100.0
        ]

        if len(overlapping) == 1 and len(exact) == 1:
            print("ALREADY EXISTS:", plan["name"])
            continue

        if overlapping:
            print(
                "STOP: Conflicting assignments for",
                plan["name"]
            )
            print(overlapping)
            return

        pending.append(plan)

    # Check approved leave and fixed weekly offs.
    for plan in pending:
        for day in (
            [plan["start_date"]]
            if plan["start_date"] == plan["end_date"]
            else ["2026-12-22", "2026-12-23"]
        ):
            leave = (
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

            if leave:
                print("STOP: Approved leave on", day)
                return

    for plan in pending:
        payload = {
            "employee_id": employee_id,
            "brand_process_id": plan["brand_process_id"],
            "allocation_percent": 100.0,
            "is_primary": False,
            "start_date": plan["start_date"],
            "end_date": plan["end_date"],
        }

        result = (
            supabase.table("assignments")
            .insert(payload)
            .execute()
        )

        print("CREATED:", plan["name"])
        print("Assignment ID:", result.data[0]["id"])

    print("Assignment setup complete.")


if __name__ == "__main__":
    main()
