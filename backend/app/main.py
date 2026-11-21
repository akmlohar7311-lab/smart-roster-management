
from uuid import UUID

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware

from app.auth import require_authenticated_user
from app.database import supabase

from app.missing_shifts import router as missing_shifts_router
from app.assignment_manager import router as assignment_manager_router
from app.roster_views import router as roster_view_router
from app.backup_finder import router as backup_router
from app.roster_editor import router as roster_editor_router
from app.leaves import router as leave_router
from app.ai_copilot import router as ai_copilot_router

from app.validator import validate_roster
from app.scheduler import generate_roster


app = FastAPI(title="Datastraw Smart Roster API")


# ==========================================
# CORS CONFIGURATION
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://smart-roster-management-ceqa.onrender.com",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# AUTHENTICATION PROTECTION FOR ALL ROUTERS
# ==========================================

protected_dependencies = [
    Depends(require_authenticated_user)
]

app.include_router(
    missing_shifts_router,
    dependencies=protected_dependencies
)

app.include_router(
    ai_copilot_router,
    dependencies=protected_dependencies
)

app.include_router(
    roster_view_router,
    dependencies=protected_dependencies
)

app.include_router(
    backup_router,
    dependencies=protected_dependencies
)

app.include_router(
    roster_editor_router,
    dependencies=protected_dependencies
)

app.include_router(
    leave_router,
    dependencies=protected_dependencies
)

app.include_router(
    assignment_manager_router,
    dependencies=protected_dependencies
)


# ==========================================
# PUBLIC HEALTH CHECK
# ==========================================

@app.get("/")
def home():
    return {
        "message": "Datastraw Smart Roster API is running!"
    }


# ==========================================
# EMPLOYEE MANAGEMENT
# ==========================================

@app.get("/employees")
def get_employees(
    current_user=Depends(require_authenticated_user)
):
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
            detail="Database request failed. Check backend logs."
        )


# ==========================================
# MONTHLY ROSTER GENERATION
# ==========================================

@app.post("/rosters/generate")
def create_monthly_roster(
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    current_user=Depends(require_authenticated_user)
):
    try:
        return generate_roster(year, month)

    except Exception as error:
        print("ROSTER GENERATION ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Roster generation failed. Check backend logs."
        )


# ==========================================
# ROSTER VALIDATION
# ==========================================

@app.get("/rosters/{roster_id}/validate")
def check_roster(
    roster_id: UUID,
    current_user=Depends(require_authenticated_user)
):
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
            detail="Roster validation failed."
        )
