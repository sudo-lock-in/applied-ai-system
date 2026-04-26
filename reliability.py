"""
Reliability and Validation System for PawPal+

This module provides:
1. Plan validation - check schedules against constraints
2. Conflict detection - find scheduling conflicts
3. Testing utilities - unit tests for scheduling logic
4. Audit logging - track all schedule changes and decisions
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from pawpal_system import CareTask, Pet, Owner, Scheduler
from agent import SchedulePlan


@dataclass
class ValidationResult:
    """Result of validating a schedule plan."""
    is_valid: bool
    severity: str  # "critical", "warning", "info"
    errors: list[str]  # Critical issues that prevent execution
    warnings: list[str]  # Issues that should be addressed
    checks_passed: int
    checks_total: int
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "severity": self.severity,
            "errors": self.errors,
            "warnings": self.warnings,
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "timestamp": self.timestamp.isoformat()
        }

    def summary(self) -> str:
        """Return a human-readable summary."""
        summary = f"Validation: {'✅ PASSED' if self.is_valid else '❌ FAILED'}\n"
        summary += f"Checks: {self.checks_passed}/{self.checks_total} passed\n"
        
        if self.errors:
            summary += f"\n🚨 Critical Errors ({len(self.errors)}):\n"
            for error in self.errors:
                summary += f"  - {error}\n"
        
        if self.warnings:
            summary += f"\n⚠️ Warnings ({len(self.warnings)}):\n"
            for warning in self.warnings:
                summary += f"  - {warning}\n"
        
        return summary


class PlanValidator:
    """
    Comprehensive validation system for schedule plans.
    
    Checks:
    1. Time constraints - respects owner's available time
    2. Conflict detection - no overlapping tasks
    3. Priority coverage - all high-priority tasks included
    4. Frequency coverage - recurring tasks properly scheduled
    5. Pet welfare - ensures adequate care
    6. Feasibility - can actually be executed
    """

    def __init__(self):
        self.checks_performed = []
        self.issues_found = []

    def validate_plan(
        self,
        plan: SchedulePlan,
        owner: Owner,
        scheduler: Scheduler
    ) -> ValidationResult:
        """
        Perform comprehensive validation of a plan.
        
        Args:
            plan: SchedulePlan to validate
            owner: Owner with constraints
            scheduler: Scheduler with tasks
        
        Returns:
            ValidationResult with all checks and issues
        """
        
        errors = []
        warnings = []
        checks_passed = 0
        checks_total = 0

        # Check 1: Time constraints
        checks_total += 1
        check1 = self._check_time_constraints(plan, owner)
        if check1["passed"]:
            checks_passed += 1
        else:
            errors.extend(check1["errors"])
            warnings.extend(check1["warnings"])

        # Check 2: No time conflicts
        checks_total += 1
        check2 = self._check_time_conflicts(plan)
        if check2["passed"]:
            checks_passed += 1
        else:
            errors.extend(check2["errors"])
            warnings.extend(check2["warnings"])

        # Check 3: High-priority coverage
        checks_total += 1
        check3 = self._check_priority_coverage(plan, scheduler)
        if check3["passed"]:
            checks_passed += 1
        else:
            errors.extend(check3["errors"])
            warnings.extend(check3["warnings"])

        # Check 4: Daily recurring tasks
        checks_total += 1
        check4 = self._check_recurring_coverage(plan, scheduler)
        if check4["passed"]:
            checks_passed += 1
        else:
            errors.extend(check4["errors"])
            warnings.extend(check4["warnings"])

        # Check 5: Pet welfare
        checks_total += 1
        check5 = self._check_pet_welfare(plan, scheduler)
        if check5["passed"]:
            checks_passed += 1
        else:
            errors.extend(check5["errors"])
            warnings.extend(check5["warnings"])

        # Check 6: Feasibility
        checks_total += 1
        check6 = self._check_feasibility(plan, owner)
        if check6["passed"]:
            checks_passed += 1
        else:
            errors.extend(check6["errors"])
            warnings.extend(check6["warnings"])

        is_valid = len(errors) == 0
        severity = "critical" if errors else ("warning" if warnings else "info")

        return ValidationResult(
            is_valid=is_valid,
            severity=severity,
            errors=errors,
            warnings=warnings,
            checks_passed=checks_passed,
            checks_total=checks_total,
            timestamp=datetime.now()
        )

    def _check_time_constraints(self, plan: SchedulePlan, owner: Owner) -> dict:
        """Check if total duration respects owner's available time."""
        errors = []
        warnings = []
        passed = True

        if plan.total_duration > owner.available_minutes:
            errors.append(
                f"Total duration {plan.total_duration}m exceeds available time {owner.available_minutes}m"
            )
            passed = False
        elif plan.total_duration > owner.available_minutes * 0.95:
            warnings.append(
                f"Schedule uses {plan.total_duration/owner.available_minutes*100:.0f}% of available time (very tight)"
            )

        return {"passed": passed, "errors": errors, "warnings": warnings}

    def _check_time_conflicts(self, plan: SchedulePlan) -> dict:
        """Check for overlapping time slots."""
        errors = []
        warnings = []
        passed = True

        for i, task1 in enumerate(plan.scheduled_tasks):
            for task2 in plan.scheduled_tasks[i+1:]:
                if self._times_overlap(
                    task1['start_time'], task1['end_time'],
                    task2['start_time'], task2['end_time']
                ):
                    errors.append(
                        f"Time conflict: '{task1['title']}' ({task1['start_time']}-{task1['end_time']}) "
                        f"overlaps with '{task2['title']}' ({task2['start_time']}-{task2['end_time']})"
                    )
                    passed = False

        return {"passed": passed, "errors": errors, "warnings": warnings}

    def _check_priority_coverage(self, plan: SchedulePlan, scheduler: Scheduler) -> dict:
        """Check that high-priority tasks are included."""
        errors = []
        warnings = []
        passed = True

        high_priority_tasks = [t for t in scheduler.get_tasks() if t.priority == "high"]
        scheduled_high = [t for t in plan.scheduled_tasks if t.get('priority') == 'high']

        if len(scheduled_high) < len(high_priority_tasks):
            unscheduled = len(high_priority_tasks) - len(scheduled_high)
            warnings.append(
                f"Not all high-priority tasks scheduled: {unscheduled}/{len(high_priority_tasks)} missing"
            )

        return {"passed": passed, "errors": errors, "warnings": warnings}

    def _check_recurring_coverage(self, plan: SchedulePlan, scheduler: Scheduler) -> dict:
        """Check that daily recurring tasks are included."""
        errors = []
        warnings = []
        passed = True

        daily_tasks = [t for t in scheduler.get_tasks() if t.frequency == "daily"]
        scheduled_daily = [t for t in plan.scheduled_tasks if t.get('frequency') == 'daily']

        if len(scheduled_daily) < len(daily_tasks):
            unscheduled = len(daily_tasks) - len(scheduled_daily)
            warnings.append(
                f"Not all daily tasks scheduled: {unscheduled}/{len(daily_tasks)} missing"
            )

        return {"passed": passed, "errors": errors, "warnings": warnings}

    def _check_pet_welfare(self, plan: SchedulePlan, scheduler: Scheduler) -> dict:
        """Check that pet welfare tasks (feeding, water) are included."""
        errors = []
        warnings = []
        passed = True

        # Check for basic care categories
        welfare_categories = ["feeding", "water", "exercise", "bathroom"]
        scheduled_categories = [t.get('category', '').lower() for t in plan.scheduled_tasks]

        for category in welfare_categories:
            required_tasks = [t for t in scheduler.get_tasks() if category in t.category.lower()]
            if required_tasks and not any(category in cat for cat in scheduled_categories):
                warnings.append(f"No '{category}' tasks scheduled - pet welfare concern")

        return {"passed": passed, "errors": errors, "warnings": warnings}

    def _check_feasibility(self, plan: SchedulePlan, owner: Owner) -> dict:
        """Check if plan is actually feasible to execute."""
        errors = []
        warnings = []
        passed = True

        # Check for unrealistic back-to-back tasks
        if len(plan.scheduled_tasks) > 1:
            for i, task in enumerate(plan.scheduled_tasks[:-1]):
                next_task = plan.scheduled_tasks[i+1]
                end_time = self._time_to_minutes(task['end_time'])
                next_start = self._time_to_minutes(next_task['start_time'])

                if next_start - end_time < 5:  # Less than 5 minutes between tasks
                    warnings.append(
                        f"No buffer between '{task['title']}' and '{next_task['title']}' "
                        f"(only {next_start - end_time} minutes)"
                    )

        return {"passed": passed, "errors": errors, "warnings": warnings}

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM to minutes since midnight."""
        try:
            hours, minutes = map(int, time_str.split(':'))
            return hours * 60 + minutes
        except:
            return 0

    def _times_overlap(self, start1: str, end1: str, start2: str, end2: str) -> bool:
        """Check if two time ranges overlap."""
        s1 = self._time_to_minutes(start1)
        e1 = self._time_to_minutes(end1)
        s2 = self._time_to_minutes(start2)
        e2 = self._time_to_minutes(end2)

        return not (e1 <= s2 or e2 <= s1)


class AuditLogger:
    """
    Audit logging system to track all scheduling decisions and changes.
    
    Logs:
    - Plan generation with parameters
    - Validation results
    - User approvals/rejections
    - Manual edits
    - Execution status
    """

    def __init__(self, log_file: str = "schedule_audit.jsonl"):
        self.log_file = Path(log_file)
        self._ensure_log_file_exists()

    def _ensure_log_file_exists(self):
        """Create log file if it doesn't exist."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            self.log_file.touch()

    def log_plan_generated(
        self,
        owner: Owner,
        pet: Pet,
        plan: SchedulePlan,
        method: str = "deterministic"
    ):
        """Log when a plan is generated."""
        entry = {
            "event": "plan_generated",
            "timestamp": datetime.now().isoformat(),
            "owner": owner.name,
            "pet": pet.name,
            "method": method,
            "plan_summary": {
                "total_duration": plan.total_duration,
                "task_count": len(plan.scheduled_tasks),
                "conflicts": len(plan.conflicts_detected)
            }
        }
        self._write_log(entry)

    def log_plan_validated(
        self,
        owner: Owner,
        pet: Pet,
        validation_result: ValidationResult
    ):
        """Log validation result."""
        entry = {
            "event": "plan_validated",
            "timestamp": datetime.now().isoformat(),
            "owner": owner.name,
            "pet": pet.name,
            "validation": validation_result.to_dict()
        }
        self._write_log(entry)

    def log_plan_approved(self, owner: Owner, pet: Pet, plan: SchedulePlan):
        """Log when user approves a plan."""
        entry = {
            "event": "plan_approved",
            "timestamp": datetime.now().isoformat(),
            "owner": owner.name,
            "pet": pet.name,
            "plan_id": self._generate_plan_id(plan)
        }
        self._write_log(entry)

    def log_plan_rejected(self, owner: Owner, pet: Pet, reason: str):
        """Log when user rejects a plan."""
        entry = {
            "event": "plan_rejected",
            "timestamp": datetime.now().isoformat(),
            "owner": owner.name,
            "pet": pet.name,
            "reason": reason
        }
        self._write_log(entry)

    def log_manual_edit(
        self,
        owner: Owner,
        pet: Pet,
        task_title: str,
        change_description: str
    ):
        """Log manual edits to a schedule."""
        entry = {
            "event": "manual_edit",
            "timestamp": datetime.now().isoformat(),
            "owner": owner.name,
            "pet": pet.name,
            "task": task_title,
            "change": change_description
        }
        self._write_log(entry)

    def log_execution_status(
        self,
        owner: Owner,
        pet: Pet,
        task_title: str,
        status: str,
        notes: str = ""
    ):
        """Log when a task is executed (started, completed, skipped)."""
        entry = {
            "event": "execution_status",
            "timestamp": datetime.now().isoformat(),
            "owner": owner.name,
            "pet": pet.name,
            "task": task_title,
            "status": status,  # "started", "completed", "skipped"
            "notes": notes
        }
        self._write_log(entry)

    def _write_log(self, entry: dict):
        """Write a single log entry as JSON line."""
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def _generate_plan_id(self, plan: SchedulePlan) -> str:
        """Generate a unique ID for a plan."""
        import hashlib
        content = f"{plan.owner_name}_{plan.pet_name}_{plan.timestamp.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def get_audit_trail(self, owner_name: str = None, limit: int = 100) -> list[dict]:
        """
        Retrieve audit trail entries.
        
        Args:
            owner_name: Filter by owner name (None = all owners)
            limit: Maximum number of entries to return
        
        Returns:
            List of log entries
        """
        entries = []

        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if owner_name is None or entry.get('owner') == owner_name:
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue

        return entries[-limit:] if limit else entries

    def get_summary(self, owner_name: str = None) -> dict:
        """Get summary statistics from audit log."""
        entries = self.get_audit_trail(owner_name, limit=None)

        summary = {
            "total_entries": len(entries),
            "plans_generated": len([e for e in entries if e['event'] == 'plan_generated']),
            "plans_validated": len([e for e in entries if e['event'] == 'plan_validated']),
            "plans_approved": len([e for e in entries if e['event'] == 'plan_approved']),
            "plans_rejected": len([e for e in entries if e['event'] == 'plan_rejected']),
            "manual_edits": len([e for e in entries if e['event'] == 'manual_edit']),
            "tasks_executed": len([e for e in entries if e['event'] == 'execution_status'])
        }

        return summary


class HumanReviewCheckpoint:
    """
    Interactive human review system for AI-generated plans.
    
    Allows users to:
    1. Review AI reasoning before applying schedule
    2. Provide feedback on plan quality
    3. Request modifications
    4. Approve or reject
    """

    def __init__(self):
        self.feedback_history = []

    def create_review_prompt(self, plan: SchedulePlan, validation: ValidationResult) -> str:
        """
        Create a review prompt showing the plan and asking for approval.
        
        Returns:
            Formatted review prompt for user
        """
        prompt = f"""
{plan.to_markdown()}

## ✅ Validation Status
{validation.summary()}

## ❓ Questions for You:
1. Does this schedule work for your lifestyle?
2. Are the start times realistic?
3. Any tasks you'd like to reorder or adjust?
4. Any concerns about pet welfare?

**Options:**
- ✅ APPROVE: Use this schedule
- 📝 MODIFY: Request specific changes
- ❌ REJECT: Try a different approach
"""
        return prompt

    def record_feedback(
        self,
        owner: Owner,
        pet: Pet,
        plan: SchedulePlan,
        decision: str,  # "approve", "modify", "reject"
        feedback_text: str = ""
    ):
        """Record user feedback on a plan."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "owner": owner.name,
            "pet": pet.name,
            "decision": decision,
            "feedback": feedback_text
        }
        self.feedback_history.append(entry)

    def get_feedback_summary(self) -> dict:
        """Get summary of all feedback."""
        if not self.feedback_history:
            return {"message": "No feedback recorded yet"}

        decisions = [f['decision'] for f in self.feedback_history]

        return {
            "total_plans_reviewed": len(decisions),
            "approved": decisions.count("approve"),
            "modified": decisions.count("modify"),
            "rejected": decisions.count("reject"),
            "approval_rate": f"{decisions.count('approve')/len(decisions)*100:.0f}%"
        }
