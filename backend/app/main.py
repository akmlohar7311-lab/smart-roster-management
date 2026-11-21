
from app.missing_shifts import router as missing_shifts_router

from app.assignment_manager import router as assignment_manager_router


from app.roster_views import router as roster_view_router

from app.backup_finder import router as backup_router

from app.roster_editor import router as roster_editor_router

from app.leaves import router as leave_router

from app.ai_copilot import router as ai_copilot_router
from uuid import UUID
from app.validator import validate_roster

from fastapi import Query
from app.scheduler import generate_roster

from fastapi import FastAPI, HTTPException
from app.database import supabase


app = FastAPI(title="Datastraw Smart Roster API")

app.include_router(missing_shifts_router)
app.include_router(ai_copilot_router)
app.include_router(roster_view_router)
app.include_router(backup_router)
app.include_router(roster_editor_router)
app.include_router(leave_router)

app.include_router(assignment_manager_router)




@app.get("/")
def home():
    return {"message": "Backend is running!"}


@app.get("/employees")
def get_employees():
    try:
        response = (
            supabase.table("employees")
            .select("employee_code,name,email,active")
            .order("employee_code")
            .execute()
        )

        return {
            "total": len(response.data),
            "employees": response.data
        }


    except Exception as error:
        print("SUPABASE ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Database request failed. Check PyCharm terminal."
        )


@app.post("/rosters/generate")
def create_monthly_roster(
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12)
):
    try:
        result = generate_roster(year, month)
        return result

    except Exception as error:
        print("ROSTER GENERATION ERROR:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Roster generation failed. Check PyCharm terminal."
        )


@app.get("/rosters/{roster_id}/validate")
def check_roster(roster_id: UUID):
    try:
        return validate_roster(str(roster_id))

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except Exception as error:
        print("VALIDATION ERROR:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Roster validation failed"
        )
