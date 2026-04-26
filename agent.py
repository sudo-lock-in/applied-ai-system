"""
Agentic Scheduling Workflow for PawPal+

This module implements an intelligent scheduling agent that uses an LLM to:
1. Analyze pet care needs and owner constraints
2. Generate optimal schedules with reasoning
3. Provide explanations for scheduling decisions
4. Adapt plans based on conflicts and feedback
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from pawpal_system import CareTask, Pet, Owner, Scheduler


@dataclass
class SchedulePlan:
    """Represents an AI-generated schedule plan with reasoning."""
    owner_name: str
    pet_name: str
    scheduled_tasks: list[dict]  # List of {task_title, start_time, end_time, reasoning}
    total_duration: int
    conflicts_detected: list[str]
    explanation: str  # Overall reasoning for the plan
    timestamp: datetime
    is_validated: bool = False
    validation_warnings: list[str] = None

    def __post_init__(self):
        if self.validation_warnings is None:
            self.validation_warnings = []

    def to_dict(self) -> dict:
        """Convert plan to dictionary for JSON serialization."""
        return {
            "owner": self.owner_name,
            "pet": self.pet_name,
            "timestamp": self.timestamp.isoformat(),
            "total_duration": self.total_duration,
            "scheduled_tasks": self.scheduled_tasks,
            "conflicts": self.conflicts_detected,
            "explanation": self.explanation,
            "is_validated": self.is_validated,
            "validation_warnings": self.validation_warnings
        }

    def to_markdown(self) -> str:
        """Convert plan to readable markdown format."""
        md = f"""# 📅 Schedule Plan for {self.pet_name}
**Owner:** {self.owner_name}  
**Generated:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}  
**Validation Status:** {'✅ Passed' if self.is_validated else '⚠️ Not Validated'}

## 🎯 Schedule
| Task | Start Time | End Time | Duration | Reasoning |
|------|-----------|----------|----------|-----------|
"""
        for task in self.scheduled_tasks:
            md += f"| {task['title']} | {task['start_time']} | {task['end_time']} | {task.get('duration', 'N/A')} min | {task.get('reasoning', '')} |\n"
        
        md += f"\n## ⏱️ Summary\n**Total Duration:** {self.total_duration} minutes\n"
        
        if self.conflicts_detected:
            md += f"\n## ⚠️ Conflicts Detected ({len(self.conflicts_detected)})\n"
            for conflict in self.conflicts_detected:
                md += f"- {conflict}\n"
        else:
            md += "\n## ✅ No Conflicts\n"
        
        md += f"\n## 💭 AI Reasoning\n{self.explanation}\n"
        
        if self.validation_warnings:
            md += f"\n## ⚠️ Validation Warnings\n"
            for warning in self.validation_warnings:
                md += f"- {warning}\n"
        
        return md


class SchedulingAgent:
    """
    Intelligent scheduling agent that plans pet care tasks.
    
    This agent:
    - Analyzes constraints (owner time, pet needs, priorities)
    - Generates optimized schedules
    - Provides reasoning for decisions
    - Validates against conflicts and constraints
    """

    def __init__(self, llm_client=None):
        """
        Initialize the scheduling agent.
        
        Args:
            llm_client: Optional LLM client (e.g., Anthropic, OpenAI)
                       If None, uses deterministic fallback algorithm
        """
        self.llm_client = llm_client
        self.use_llm = llm_client is not None

    def generate_schedule(
        self,
        owner: Owner,
        pet: Pet,
        scheduler: Scheduler,
        start_time: str = "08:00",
        end_time: str = "20:00"
    ) -> SchedulePlan:
        """
        Generate an optimized schedule for a pet.
        
        Args:
            owner: Pet owner with constraints and preferences
            pet: Pet to schedule tasks for
            scheduler: Scheduler with tasks loaded
            start_time: Schedule start time (HH:MM format)
            end_time: Schedule end time (HH:MM format)
        
        Returns:
            SchedulePlan with scheduled tasks and reasoning
        """
        
        if self.use_llm:
            return self._generate_schedule_with_llm(
                owner, pet, scheduler, start_time, end_time
            )
        else:
            return self._generate_schedule_deterministic(
                owner, pet, scheduler, start_time, end_time
            )

    def _generate_schedule_deterministic(
        self,
        owner: Owner,
        pet: Pet,
        scheduler: Scheduler,
        start_time: str,
        end_time: str
    ) -> SchedulePlan:
        """
        Generate schedule using deterministic algorithm (no LLM).
        Uses priority, duration, and frequency to create optimal order.
        """
        
        tasks = scheduler.get_tasks()
        if not tasks:
            return SchedulePlan(
                owner_name=owner.name,
                pet_name=pet.name,
                scheduled_tasks=[],
                total_duration=0,
                conflicts_detected=[],
                explanation="No tasks to schedule.",
                timestamp=datetime.now(),
                is_validated=True
            )

        # Sort by priority and frequency
        sorted_tasks = scheduler.sort_tasks(by="priority")
        
        # Convert times to minutes
        start_minutes = self._time_to_minutes(start_time)
        end_minutes = self._time_to_minutes(end_time)
        available_minutes = end_minutes - start_minutes
        
        scheduled_tasks = []
        current_time = start_minutes
        total_duration = 0
        conflicts = []
        
        for task in sorted_tasks:
            task_end = current_time + task.duration_minutes
            
            # Check if task fits
            if task_end <= end_minutes:
                end_time_str = self._minutes_to_time(task_end)
                start_time_str = self._minutes_to_time(current_time)
                
                reasoning = self._get_task_reasoning(task, current_time)
                
                scheduled_tasks.append({
                    "title": task.title,
                    "start_time": start_time_str,
                    "end_time": end_time_str,
                    "duration": task.duration_minutes,
                    "priority": task.priority,
                    "reasoning": reasoning
                })
                
                current_time = task_end
                total_duration += task.duration_minutes
            else:
                conflicts.append(
                    f"⚠️ '{task.title}' ({task.duration_minutes}m) doesn't fit "
                    f"in remaining {end_minutes - current_time}m"
                )
        
        explanation = self._build_explanation(
            owner, pet, scheduled_tasks, available_minutes, total_duration
        )
        
        plan = SchedulePlan(
            owner_name=owner.name,
            pet_name=pet.name,
            scheduled_tasks=scheduled_tasks,
            total_duration=total_duration,
            conflicts_detected=conflicts,
            explanation=explanation,
            timestamp=datetime.now()
        )
        
        return plan

    def _generate_schedule_with_llm(
        self,
        owner: Owner,
        pet: Pet,
        scheduler: Scheduler,
        start_time: str,
        end_time: str
    ) -> SchedulePlan:
        """
        Generate schedule using LLM for intelligent reasoning.
        Requires llm_client to be configured.
        """
        
        # Prepare context for LLM
        context = self._prepare_llm_context(owner, pet, scheduler, start_time, end_time)
        
        # Call LLM (implementation depends on client)
        try:
            response = self._call_llm(context)
            plan = self._parse_llm_response(response, owner, pet)
            return plan
        except Exception as e:
            # Fallback to deterministic if LLM fails
            print(f"⚠️ LLM call failed: {e}. Falling back to deterministic scheduling.")
            return self._generate_schedule_deterministic(
                owner, pet, scheduler, start_time, end_time
            )

    def _prepare_llm_context(
        self,
        owner: Owner,
        pet: Pet,
        scheduler: Scheduler,
        start_time: str,
        end_time: str
    ) -> str:
        """Prepare context string for LLM."""
        
        tasks_desc = "\n".join([
            f"- {t.title}: {t.duration_minutes}m, "
            f"Priority: {t.priority}, "
            f"Category: {t.category}, "
            f"Frequency: {t.frequency}"
            for t in scheduler.get_tasks()
        ])
        
        context = f"""
You are a pet care scheduling expert. Create an optimal daily schedule for this scenario:

**Owner:** {owner.name}
- Available time: {owner.available_minutes} minutes
- Preferred start time: {owner.preferred_start_time}
- Preferences: {', '.join(owner.preferences) if owner.preferences else 'None specified'}

**Pet:** {pet.name}
- Species: {pet.species}
- Breed: {pet.breed}
- Age: {pet.age} years

**Tasks to schedule:**
{tasks_desc}

**Constraints:**
- Schedule window: {start_time} to {end_time}
- Owner has {owner.available_minutes} minutes available
- Avoid task conflicts
- Prioritize high-priority tasks

Provide a JSON response with:
1. scheduled_tasks: list of {{task_title, start_time, end_time, reasoning}}
2. total_duration: total minutes
3. conflicts: list of any detected conflicts
4. explanation: your reasoning for this schedule
"""
        return context

    def _call_llm(self, context: str) -> str:
        """Call LLM with context (to be implemented per LLM provider)."""
        if not self.llm_client:
            raise ValueError("LLM client not configured")
        
        # This is a placeholder - implementation depends on LLM provider
        # Example for Anthropic Claude:
        # response = self.llm_client.messages.create(
        #     model="claude-3-sonnet-20240229",
        #     max_tokens=1024,
        #     messages=[{"role": "user", "content": context}]
        # )
        # return response.content[0].text
        
        raise NotImplementedError("LLM client integration needed")

    def _parse_llm_response(self, response: str, owner: Owner, pet: Pet) -> SchedulePlan:
        """Parse LLM response into SchedulePlan."""
        try:
            data = json.loads(response)
            return SchedulePlan(
                owner_name=owner.name,
                pet_name=pet.name,
                scheduled_tasks=data.get("scheduled_tasks", []),
                total_duration=data.get("total_duration", 0),
                conflicts_detected=data.get("conflicts", []),
                explanation=data.get("explanation", ""),
                timestamp=datetime.now()
            )
        except json.JSONDecodeError:
            raise ValueError("LLM response not valid JSON")

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM to minutes since midnight."""
        try:
            hours, minutes = map(int, time_str.split(':'))
            return hours * 60 + minutes
        except:
            return 0

    def _minutes_to_time(self, minutes: int) -> str:
        """Convert minutes since midnight to HH:MM."""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    def _get_task_reasoning(self, task: CareTask, current_time: int) -> str:
        """Generate reasoning for why task is scheduled at this time."""
        
        priority_reason = {
            "high": "⚠️ High-priority task",
            "medium": "📌 Medium-priority task",
            "low": "✓ Low-priority filler"
        }.get(task.priority, "Task")
        
        frequency_reason = {
            "daily": "needs daily attention",
            "weekly": "important recurring task",
            "monthly": "regular maintenance",
            "one-time": "one-time need"
        }.get(task.frequency, "")
        
        return f"{priority_reason} - {frequency_reason}"

    def _build_explanation(
        self,
        owner: Owner,
        pet: Pet,
        scheduled_tasks: list[dict],
        available_minutes: int,
        total_duration: int
    ) -> str:
        """Build a natural language explanation of the schedule."""
        
        utilization = (total_duration / available_minutes * 100) if available_minutes > 0 else 0
        
        explanation = f"""
## Scheduling Strategy

For {pet.name}, I've created a schedule that maximizes care quality while respecting {owner.name}'s time constraints.

**Key Decisions:**
1. **Priority First:** High-priority tasks are scheduled early when energy is highest
2. **Time Efficiency:** Tasks are ordered to fit within {available_minutes} available minutes
3. **Pet Welfare:** Recurring daily tasks (like feeding) are prioritized over optional activities
4. **Realistic Pacing:** Tasks are distributed across the day rather than back-to-back

**Schedule Utilization:** {utilization:.0f}% ({total_duration}/{available_minutes} minutes)
"""
        
        if utilization > 90:
            explanation += "\n⚠️ **Note:** Schedule is quite full. Consider reducing scope or extending available time."
        elif utilization < 50:
            explanation += f"\n✅ **Note:** There's {available_minutes - total_duration} minutes of flexibility for breaks or unexpected needs."
        
        return explanation

    def validate_plan(
        self,
        plan: SchedulePlan,
        owner: Owner,
        scheduler: Scheduler
    ) -> tuple[bool, list[str]]:
        """
        Validate a schedule plan for feasibility and constraints.
        
        Returns:
            (is_valid, list_of_warnings)
        """
        warnings = []
        
        # Check 1: Total duration doesn't exceed available time
        if plan.total_duration > owner.available_minutes:
            warnings.append(
                f"🚨 Total duration ({plan.total_duration}m) "
                f"exceeds available time ({owner.available_minutes}m)"
            )
        
        # Check 2: No overlapping time slots
        for i, task1 in enumerate(plan.scheduled_tasks):
            for task2 in plan.scheduled_tasks[i+1:]:
                if self._times_overlap(
                    task1['start_time'], task1['end_time'],
                    task2['start_time'], task2['end_time']
                ):
                    warnings.append(
                        f"⚠️ Time conflict: '{task1['title']}' and '{task2['title']}' overlap"
                    )
        
        # Check 3: All high-priority tasks are scheduled
        high_priority_count = len([t for t in scheduler.get_tasks() if t.priority == "high"])
        scheduled_high_priority = len([t for t in plan.scheduled_tasks if t['priority'] == 'high'])
        
        if scheduled_high_priority < high_priority_count:
            warnings.append(
                f"⚠️ Not all high-priority tasks scheduled "
                f"({scheduled_high_priority}/{high_priority_count})"
            )
        
        # Check 4: All daily recurring tasks are scheduled
        daily_tasks = [t for t in scheduler.get_tasks() if t.frequency == "daily"]
        scheduled_daily = len([t for t in plan.scheduled_tasks if t.get('frequency') == 'daily'])
        
        if scheduled_daily < len(daily_tasks):
            warnings.append(
                f"⚠️ Not all daily tasks scheduled ({scheduled_daily}/{len(daily_tasks)})"
            )
        
        is_valid = len(warnings) == 0
        plan.is_validated = True
        plan.validation_warnings = warnings
        
        return is_valid, warnings

    def _times_overlap(self, start1: str, end1: str, start2: str, end2: str) -> bool:
        """Check if two time ranges overlap."""
        s1 = self._time_to_minutes(start1)
        e1 = self._time_to_minutes(end1)
        s2 = self._time_to_minutes(start2)
        e2 = self._time_to_minutes(end2)
        
        return not (e1 <= s2 or e2 <= s1)

    def get_plan_insights(self, plan: SchedulePlan, scheduler: Scheduler) -> dict:
        """
        Generate insights about a plan.
        
        Returns dict with:
        - most_challenging_task
        - best_fitting_task
        - time_efficiency
        - recommendation
        """
        
        if not plan.scheduled_tasks:
            return {"message": "No tasks scheduled"}
        
        # Find most challenging (longest) task
        longest = max(plan.scheduled_tasks, key=lambda t: t['duration'])
        
        # Find best fitting (shortest) task
        shortest = min(plan.scheduled_tasks, key=lambda t: t['duration'])
        
        # Calculate time efficiency
        available = sum(t['duration'] for t in plan.scheduled_tasks) + \
                   (self._time_to_minutes("20:00") - self._time_to_minutes("08:00") - plan.total_duration)
        efficiency = (plan.total_duration / available * 100) if available > 0 else 0
        
        # Generate recommendation
        if efficiency > 95:
            recommendation = "⚠️ Schedule is very tight. Consider extending time or reducing tasks."
        elif efficiency > 80:
            recommendation = "✅ Well-optimized schedule with some buffer room."
        else:
            recommendation = "✓ Comfortable schedule with flexibility for adjustments."
        
        return {
            "most_challenging_task": longest['title'],
            "best_fitting_task": shortest['title'],
            "time_efficiency": f"{efficiency:.1f}%",
            "recommendation": recommendation,
            "total_tasks": len(plan.scheduled_tasks),
            "total_duration": plan.total_duration
        }
