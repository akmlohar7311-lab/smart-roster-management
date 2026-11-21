
# Datastraw Smart Roster Management System

A workforce scheduling application developed for the
Datastraw AI Internship Assessment.

## Overview

The system manages employees, pods, brands, processes,
workforce assignments, leaves, monthly rosters, and
scheduling conflicts.

It provides tools to generate monthly rosters, identify
coverage shortages, manage employee assignments, edit
scheduled shifts, and review roster validation results.

## Technology Stack

- Frontend: React, Vite, JavaScript, CSS
- Backend: Python, FastAPI
- Database: Supabase (PostgreSQL)
- AI Assistant: Google Gemini
- Version Control: Git and GitHub

## Implemented Features

- Employee directory with 31 sample employees
- Brand, process, and pod relationships
- Employee assignment management
- Monthly roster generation
- Company-wide, employee, brand, process, and pod filters
- Leave request and approval functionality
- Roster validation and conflict detection
- Backup employee eligibility checking
- Roster editing and shift replacement
- Gemini-powered AI Copilot

## Local Setup

### Backend

Create a Python virtual environment and install the
backend dependencies.

Configure the following variables in `backend/.env`:

SUPABASE_URL
SUPABASE_SECRET_KEY
GEMINI_API_KEY
GEMINI_MODEL

Use `backend/.env.example` as a reference.

Start the backend from the `backend` directory:

    python -m uvicorn app.main:app --host 127.0.0.1 --port 8011

### Frontend

From the `frontend` directory:

    npm install
    npm run dev

Open the local URL provided by Vite.

## How the System Works

1. Employees are associated with pods.
2. Brands contain operational processes.
3. Assignments connect employees to brand/process combinations.
4. Operational calendars and minimum staffing requirements
   determine expected coverage.
5. The scheduler generates monthly roster entries.
6. The validator checks schedules against staffing and
   availability constraints.
7. Managers review conflicts and modify assignments
   or shifts when appropriate.

## Tell Us How You Think

### 1. How did you model the relationships?

Employees belong to pods, which can have designated leads.
Brands and processes are linked through the
`brand_processes` table.

The `assignments` table connects employees to specific
brand/process combinations and records allocation,
primary status, and effective dates.

Roster entries represent scheduled employee work.

### 2. How are rosters generated and validated?

The scheduler uses configured assignments, operational
calendars, staffing requirements, and employee availability
to generate monthly roster entries.

The validator checks staffing coverage, employee
unavailability, and scheduling constraints.

Any detected violations are reported for manager review.

### 3. How are single-resource and multi-resource brands handled?

Both use the same assignment model.

A single-resource brand may rely on one employee for
multiple processes. Multi-resource brands can distribute
work across several assigned employees.

Minimum staffing requirements are configured per
brand/process combination.

### 4. What happens when the only assigned employee is unavailable?

The system checks whether another eligible employee
can provide coverage.

If no eligible employee is found, it reports the
coverage shortage rather than silently assigning
an unsuitable replacement.

A manager must then intervene.

### 5. How are conflicting or insufficient staffing situations handled?

The roster validator identifies problems such as
insufficient coverage, leave conflicts, weekly-off
violations, and overlapping assignments.

The Roster Editor provides tools for reviewing and
modifying scheduled shifts.

After changes, the roster should be revalidated.

### 6. What is automated, and what requires human judgment?

Automated:
- Roster generation
- Constraint validation
- Coverage shortage detection
- Backup eligibility checking

Human decisions:
- Approving leave requests
- Changing workforce assignments
- Choosing acceptable staffing compromises
- Reviewing and resolving unresolved conflicts
- Approving rosters for operational use

### 7. How would the system handle twice the scale?

The database model separates employees, pods, brands,
processes, assignments, and roster entries.

To scale further, I would add database indexes,
pagination, background roster-generation jobs,
and performance monitoring.

The scheduler and validator could be optimized to
process larger workloads incrementally.

### 8. What would you prioritize with one extra week?

I would prioritize:
1. Authentication and role-based access control
2. Improved roster-change impact previews
3. Better automated backup recommendations
4. Automated tests for scheduling constraints
5. Roster export and manager approval workflows

## Demonstrated Validation Scenario

A December 2026 roster contains 1,261 saved entries.

The validator identifies four insufficient-coverage
violations on December 16, 2026, affecting FitFuel
and GlowNest.

For one affected shift, the backup finder returns
zero eligible replacements, making the unresolved
staffing requirement visible to the manager.

## Current Limitations

- Some roster conflicts require manual intervention.
- Assignment changes require roster revalidation.
- Authentication and role-based access control have
  not yet been implemented.
- Public deployment requires appropriate protection
  for privileged database operations.

## Security

Real environment variables are excluded from Git.
Only placeholder values are included in `.env.example`.

Never commit Supabase secret keys or Gemini API keys.
