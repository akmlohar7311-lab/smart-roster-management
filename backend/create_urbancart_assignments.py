
from app.database import supabase


EMPLOYEE_CODE = "EMP031"

START_DATE = "2026-12-10"
END_DATE = "2026-12-12"

ASSIGNMENTS = {
    "UrbanCart Customer Support":
        "2abad4cc-02fa-4ab5-ab80-3b1d61e3e42d",

    "UrbanCart Abandoned Cart Conversions":
        "3e0ff8f9-15a0-42e8-95f4-aff70c572bc2"
}


def main():

    employee_rows = (
        supabase.table("employees")
        .select("id,name,active")
        .eq("employee_code", EMPLOYEE_CODE)
        .execute()
        .data
    )

    if not employee_rows:
        print("ERROR: EMP031 not found")
        return

    employee = employee_rows[0]

    if not employee["active"]:
        print("ERROR: EMP031 is inactive")
        return

    employee_id = employee["id"]

    # Verify all existing assignments that overlap
    # the proposed December 10-12 period.
    existing_all = (
        supabase.table("assignments")
        .select("*")
        .eq("employee_id", employee_id)
        .lte("start_date", END_DATE)
        .execute()
        .data
    )

    overlapping = [
        a for a in existing_all
        if a["end_date"] is None
        or a["end_date"] >= START_DATE
    ]

    desired_ids = set(ASSIGNMENTS.values())

    # Allow this script to be run again without
    # inserting the same assignments twice.
    correct_existing = [
        a for a in overlapping
        if a["brand_process_id"] in desired_ids
        and a["start_date"] <= START_DATE
        and (
            a["end_date"] is None
            or a["end_date"] >= END_DATE
        )
        and float(a["allocation_percent"]) == 50.0
    ]

    correct_ids = {
        a["brand_process_id"]
        for a in correct_existing
    }

    unexpected = [
        a for a in overlapping
        if a not in correct_existing
    ]

    if unexpected:
        print("STOP: Conflicting existing assignments found:")
        for a in unexpected:
            print(a)
        print("Review allocation before proceeding.")
        return

    print("Employee:", employee["name"])
    print("Period:", START_DATE, "to", END_DATE)

    for process_name, bp_id in ASSIGNMENTS.items():

        if bp_id in correct_ids:
            print("ALREADY EXISTS:", process_name)
            continue

        payload = {
            "employee_id": employee_id,
            "brand_process_id": bp_id,
            "allocation_percent": 50.0,
            "is_primary": False,
            "start_date": START_DATE,
            "end_date": END_DATE
        }

        result = (
            supabase.table("assignments")
            .insert(payload)
            .execute()
        )

        print("CREATED:", process_name)
        print("Assignment ID:", result.data[0]["id"])

    print("\nAssignment setup complete.")


if __name__ == "__main__":
    main()
