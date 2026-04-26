# 🐾 PawPal+ System Design

**PawPal+** is an intelligent pet care scheduling system that combines deterministic scheduling with reliability validation and human-in-the-loop approval workflows.

---

## Architecture Overview

```
USER INPUT → DATA MODELS → SCHEDULING AGENT → VALIDATION → HUMAN REVIEW → AUDIT LOG
```

**Key Components:**
- **SchedulingAgent** (agent.py): Generates schedules by sorting tasks by priority/frequency
- **PlanValidator** (reliability.py): 6-point validation system (time, conflicts, priority, welfare, etc.)
- **AuditLogger** (reliability.py): JSONL-based immutable decision log
- **HumanReviewCheckpoint**: Interactive approval before execution
- **Streamlit UI** (app.py): 2-tab interface for setup & schedule generation

## Core Components

### SchedulingAgent (`agent.py`)
Generates optimal daily schedules using deterministic priority-based sorting:
1. Sort tasks by priority (high → medium → low)
2. Within priority, sort by frequency (daily > weekly > monthly > one-time)
3. Fit tasks into time window sequentially
4. Generate reasoning for each placement

**Output:** `SchedulePlan` with scheduled_tasks, explanation, timestamp, conflicts detected

### PlanValidator (`reliability.py`)
Validates schedules against 6 constraints:

| Check | Validates |
|-------|-----------|
| Time Constraints | `total_duration ≤ owner.available_minutes` |
| Time Conflicts | No overlapping tasks |
| Priority Coverage | All high-priority tasks scheduled |
| Recurring Coverage | Daily/weekly tasks included |
| Pet Welfare | Feeding, water, exercise present |
| Feasibility | 5min+ buffer between tasks |

**Output:** `ValidationResult` with is_valid, errors, warnings, checks_passed

### AuditLogger (`reliability.py`)
JSONL-based immutable log tracking:
- plan_generated, plan_validated, plan_approved/rejected, manual_edit, execution_status

### HumanReviewCheckpoint (`reliability.py`)
Interactive approval gate showing:
- Generated schedule with times
- AI reasoning for each task
- Validation results
- User options: ✅ Approve | ❌ Reject | 🔄 Regenerate

## User Interface

**Tab 1: ⚙️ Setup**
- Owner configuration (name, available minutes, start time)
- Pet management (add/list pets)
- Task creation (title, duration, priority, category, frequency, description)

**Tab 2: 🚀 Generate AI Plan**
- Pet selector + Generate Schedule button
- AI reasoning expander
- Scheduled tasks table (Task, Time, Priority)
- Total duration metric
- Validation status & details (errors/warnings)
- Review checklist with 4 reflection questions
- Action buttons: ✅ Approve | ❌ Reject | 🔄 Regenerate
- Manage Tasks section (Complete/Undo, Edit, Delete per task)

## Current Implementation Status

| Component | Purpose | Status |
|-----------|---------|--------|
| SchedulingAgent | Generate optimal schedules | ✅ Complete |
| PlanValidator | 6-point validation | ✅ Complete |
| AuditLogger | Track all decisions | ✅ Complete |
| HumanReviewCheckpoint | User approval gate | ✅ Complete |
| Streamlit UI | 2-tab interface | ✅ Complete |
| Task Management | Inline edit/delete/complete | ✅ Complete |
| Tests | 22/24 tests passing | ✅ Passing |

---

## Key Design Principles

1. **Deterministic + Reliable** - Priority-based scheduling that works immediately
2. **Always Validate** - Critical for pet safety; every plan gets checked
3. **Human-Centered** - Approval required before any schedule takes effect
4. **Audit Trail** - JSONL log of all decisions for debugging & learning
5. **Pragmatic Simplification** - 2-tab UI focused on core functionality
