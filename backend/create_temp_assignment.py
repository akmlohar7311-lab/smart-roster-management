from app.database import supabase

EMPLOYEE_CODE = "EMP031"
BRAND_PROCESS_ID = "89bf85ff-4c96-44f6-a4f3-954a57636ebf"
DAY = "2026-12-16"

employee = (
    supabase.table("employees")
    .select("id,name")
    .eq("employee_code", EMPLOYEE_CODE)
    .single()
    .execute()
    .data
)

employee_id = employee["id"]

existing = (
    supabase.table("assignments")
    .select("*")
    .eq("employee_id", employee_id)
    .eq("brand_process_id", BRAND_PROCESS_ID)
    .lte("start_date", DAY)
    .execute()
    .data
)

existing = [
    a for a in existing
    if a["end_date"] is None or a["end_date"] >= DAY
]

if existing:
    print("Assignment already exists:", existing)
else:
    assignment = {
        "employee_id": employee_id,
        "brand_process_id": BRAND_PROCESS_ID,
        "allocation_percent": 50.0,
        "is_primary": False,
        "start_date": DAY,
        "end_date": DAY,
    }

    result = (
        supabase.table("assignments")
        .insert(assignment)
        .execute()
    )

    print("Temporary assignment created:", result.data)
