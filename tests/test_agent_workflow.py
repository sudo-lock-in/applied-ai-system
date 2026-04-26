"""
Comprehensive test suite for PawPal+ Agentic Workflow and Reliability System

Tests cover:
1. Agent scheduling logic
2. Plan validation
3. Conflict detection
4. Audit logging
5. Integration tests
"""

import pytest
from datetime import datetime, timedelta
from pawpal_system import CareTask, Pet, Owner, Scheduler
from agent import SchedulingAgent, SchedulePlan
from reliability import PlanValidator, ValidationResult, AuditLogger, HumanReviewCheckpoint


class TestSchedulingAgent:
    """Test suite for SchedulingAgent."""

    @pytest.fixture
    def setup(self):
        """Setup common test objects."""
        owner = Owner(name="Alice", available_minutes=120, preferred_start_time="08:00")
        pet = Pet(name="Max", species="dog", age=3, breed="Golden Retriever")
        owner.add_pet(pet)
        
        scheduler = Scheduler(owner, pet)
        
        # Add test tasks
        task1 = CareTask(
            title="Morning Walk",
            duration_minutes=30,
            priority="high",
            frequency="daily",
            category="Exercise"
        )
        task2 = CareTask(
            title="Feeding",
            duration_minutes=15,
            priority="high",
            frequency="daily",
            category="Feeding"
        )
        task3 = CareTask(
            title="Play Session",
            duration_minutes=20,
            priority="medium",
            frequency="daily",
            category="Exercise"
        )
        
        scheduler.add_task(task1)
        scheduler.add_task(task2)
        scheduler.add_task(task3)
        
        return owner, pet, scheduler, [task1, task2, task3]

    def test_agent_initialization(self):
        """Test agent can be initialized."""
        agent = SchedulingAgent(llm_client=None)
        assert agent is not None
        assert agent.use_llm is False

    def test_deterministic_schedule_generation(self, setup):
        """Test deterministic schedule generation without LLM."""
        owner, pet, scheduler, tasks = setup
        agent = SchedulingAgent(llm_client=None)
        
        plan = agent.generate_schedule(owner, pet, scheduler)
        
        assert plan is not None
        assert plan.owner_name == "Alice"
        assert plan.pet_name == "Max"
        assert len(plan.scheduled_tasks) > 0
        assert plan.total_duration > 0
        assert isinstance(plan.scheduled_tasks, list)

    def test_schedule_respects_available_time(self, setup):
        """Test schedule doesn't exceed owner's available time."""
        owner, pet, scheduler, tasks = setup
        agent = SchedulingAgent(llm_client=None)
        
        plan = agent.generate_schedule(owner, pet, scheduler)
        
        assert plan.total_duration <= owner.available_minutes

    def test_schedule_includes_high_priority_tasks(self, setup):
        """Test schedule prioritizes high-priority tasks."""
        owner, pet, scheduler, tasks = setup
        agent = SchedulingAgent(llm_client=None)
        
        plan = agent.generate_schedule(owner, pet, scheduler)
        scheduled_titles = [t['title'] for t in plan.scheduled_tasks]
        
        # High priority tasks should be scheduled
        assert "Morning Walk" in scheduled_titles
        assert "Feeding" in scheduled_titles

    def test_time_conversion(self):
        """Test time conversion utilities."""
        agent = SchedulingAgent()
        
        # Test minutes to time
        assert agent._minutes_to_time(0) == "00:00"
        assert agent._minutes_to_time(480) == "08:00"
        assert agent._minutes_to_time(720) == "12:00"
        assert agent._minutes_to_time(1020) == "17:00"
        
        # Test time to minutes
        assert agent._time_to_minutes("00:00") == 0
        assert agent._time_to_minutes("08:00") == 480
        assert agent._time_to_minutes("12:00") == 720
        assert agent._time_to_minutes("17:00") == 1020

    def test_plan_explanation_generation(self, setup):
        """Test that plan includes explanation."""
        owner, pet, scheduler, tasks = setup
        agent = SchedulingAgent()
        
        plan = agent.generate_schedule(owner, pet, scheduler)
        
        assert plan.explanation is not None
        assert len(plan.explanation) > 0
        assert "schedule" in plan.explanation.lower() or "plan" in plan.explanation.lower()

    def test_plan_insights_generation(self, setup):
        """Test plan insights generation."""
        owner, pet, scheduler, tasks = setup
        agent = SchedulingAgent()
        
        plan = agent.generate_schedule(owner, pet, scheduler)
        insights = agent.get_plan_insights(plan, scheduler)
        
        assert "most_challenging_task" in insights
        assert "best_fitting_task" in insights
        assert "time_efficiency" in insights
        assert "recommendation" in insights


class TestPlanValidation:
    """Test suite for PlanValidator."""

    @pytest.fixture
    def setup(self):
        """Setup validation test objects."""
        owner = Owner(name="Bob", available_minutes=120, preferred_start_time="08:00")
        pet = Pet(name="Bella", species="cat", age=5, breed="Siamese")
        owner.add_pet(pet)
        scheduler = Scheduler(owner, pet)
        
        # Create tasks
        task1 = CareTask(
            title="Feed Cat",
            duration_minutes=10,
            priority="high",
            frequency="daily",
            category="Feeding"
        )
        task2 = CareTask(
            title="Play",
            duration_minutes=15,
            priority="medium",
            frequency="daily",
            category="Exercise"
        )
        scheduler.add_task(task1)
        scheduler.add_task(task2)
        
        # Create valid plan
        plan = SchedulePlan(
            owner_name="Bob",
            pet_name="Bella",
            scheduled_tasks=[
                {"title": "Feed Cat", "start_time": "08:00", "end_time": "08:10", "duration": 10, "priority": "high", "frequency": "daily"},
                {"title": "Play", "start_time": "08:15", "end_time": "08:30", "duration": 15, "priority": "medium", "frequency": "daily"}
            ],
            total_duration=25,
            conflicts_detected=[],
            explanation="Simple daily schedule",
            timestamp=datetime.now()
        )
        
        return owner, pet, scheduler, plan

    def test_validator_initialization(self):
        """Test validator can be initialized."""
        validator = PlanValidator()
        assert validator is not None

    def test_valid_plan_passes_validation(self, setup):
        """Test that a valid plan passes all checks."""
        owner, pet, scheduler, plan = setup
        validator = PlanValidator()
        
        result = validator.validate_plan(plan, owner, scheduler)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.checks_passed == result.checks_total

    def test_time_constraint_violation_detected(self, setup):
        """Test detection of time constraint violations."""
        owner, pet, scheduler, plan = setup
        owner.available_minutes = 20  # Less than plan duration
        validator = PlanValidator()
        
        result = validator.validate_plan(plan, owner, scheduler)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "exceeds" in result.errors[0].lower()

    def test_time_conflict_detection(self, setup):
        """Test detection of overlapping time slots."""
        owner, pet, scheduler, plan = setup
        
        # Create overlapping tasks
        plan.scheduled_tasks[1]["start_time"] = "08:05"
        plan.scheduled_tasks[1]["end_time"] = "08:20"
        
        validator = PlanValidator()
        result = validator.validate_plan(plan, owner, scheduler)
        
        assert not result.is_valid
        assert any("conflict" in error.lower() for error in result.errors)

    def test_priority_coverage_check(self, setup):
        """Test check for high-priority task coverage."""
        owner, pet, scheduler, plan = setup
        
        # Create plan without high-priority task
        plan.scheduled_tasks = [
            {"title": "Play", "start_time": "08:00", "end_time": "08:15", "duration": 15, "priority": "medium", "frequency": "daily"}
        ]
        
        validator = PlanValidator()
        result = validator.validate_plan(plan, owner, scheduler)
        
        # Should have warning about missing high-priority task
        assert any("high" in w.lower() for w in result.warnings)

    def test_buffer_time_check(self, setup):
        """Test detection of insufficient buffer time between tasks."""
        owner, pet, scheduler, plan = setup
        
        # Create back-to-back tasks with no buffer
        plan.scheduled_tasks = [
            {"title": "Task 1", "start_time": "08:00", "end_time": "08:10", "duration": 10, "priority": "high", "frequency": "daily"},
            {"title": "Task 2", "start_time": "08:10", "end_time": "08:25", "duration": 15, "priority": "medium", "frequency": "daily"}
        ]
        
        validator = PlanValidator()
        result = validator.validate_plan(plan, owner, scheduler)
        
        # Should have warning about tight schedule
        assert len(result.warnings) > 0

    def test_validation_result_summary(self, setup):
        """Test validation result summary generation."""
        owner, pet, scheduler, plan = setup
        validator = PlanValidator()
        
        result = validator.validate_plan(plan, owner, scheduler)
        summary = result.summary()
        
        assert "Validation:" in summary
        assert "Checks:" in summary


class TestAuditLogging:
    """Test suite for AuditLogger."""

    @pytest.fixture
    def setup(self):
        """Setup audit logging test objects."""
        import tempfile
        log_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False).name
        
        owner = Owner(name="Charlie", available_minutes=120)
        pet = Pet(name="Rex", species="dog", age=4, breed="Labrador")
        owner.add_pet(pet)
        
        plan = SchedulePlan(
            owner_name="Charlie",
            pet_name="Rex",
            scheduled_tasks=[],
            total_duration=0,
            conflicts_detected=[],
            explanation="Test plan",
            timestamp=datetime.now()
        )
        
        logger = AuditLogger(log_file)
        
        return owner, pet, plan, logger, log_file

    def test_logger_creation(self, setup):
        """Test that logger can be created."""
        owner, pet, plan, logger, _ = setup
        assert logger is not None

    def test_log_plan_generated(self, setup):
        """Test logging plan generation."""
        owner, pet, plan, logger, _ = setup
        
        logger.log_plan_generated(owner, pet, plan, method="deterministic")
        
        trail = logger.get_audit_trail()
        assert len(trail) > 0
        assert trail[-1]['event'] == 'plan_generated'
        assert trail[-1]['owner'] == 'Charlie'

    def test_log_plan_approved(self, setup):
        """Test logging plan approval."""
        owner, pet, plan, logger, _ = setup
        
        logger.log_plan_approved(owner, pet, plan)
        
        trail = logger.get_audit_trail()
        assert len(trail) > 0
        assert trail[-1]['event'] == 'plan_approved'

    def test_audit_summary(self, setup):
        """Test audit log summary generation."""
        owner, pet, plan, logger, _ = setup
        
        logger.log_plan_generated(owner, pet, plan)
        logger.log_plan_approved(owner, pet, plan)
        logger.log_plan_rejected(owner, pet, "Schedule too tight")
        
        summary = logger.get_summary()
        
        assert summary['plans_generated'] == 1
        assert summary['plans_approved'] == 1
        assert summary['plans_rejected'] == 1

    def test_filter_audit_by_owner(self, setup):
        """Test filtering audit trail by owner name."""
        owner, pet, plan, logger, _ = setup
        
        logger.log_plan_generated(owner, pet, plan)
        
        trail_all = logger.get_audit_trail()
        trail_charlie = logger.get_audit_trail(owner_name="Charlie")
        
        assert len(trail_charlie) > 0
        assert all(e['owner'] == 'Charlie' for e in trail_charlie)


class TestHumanReviewCheckpoint:
    """Test suite for HumanReviewCheckpoint."""

    @pytest.fixture
    def setup(self):
        """Setup human review test objects."""
        owner = Owner(name="David", available_minutes=120)
        pet = Pet(name="Buddy", species="dog", age=2, breed="Beagle")
        owner.add_pet(pet)
        
        plan = SchedulePlan(
            owner_name="David",
            pet_name="Buddy",
            scheduled_tasks=[
                {"title": "Walk", "start_time": "08:00", "end_time": "08:30", "duration": 30, "priority": "high"}
            ],
            total_duration=30,
            conflicts_detected=[],
            explanation="Morning walk scheduled",
            timestamp=datetime.now()
        )
        
        validation = ValidationResult(
            is_valid=True,
            severity="info",
            errors=[],
            warnings=[],
            checks_passed=6,
            checks_total=6,
            timestamp=datetime.now()
        )
        
        checkpoint = HumanReviewCheckpoint()
        
        return owner, pet, plan, validation, checkpoint

    def test_review_prompt_generation(self, setup):
        """Test that review prompt is generated."""
        owner, pet, plan, validation, checkpoint = setup
        
        prompt = checkpoint.create_review_prompt(plan, validation)
        
        assert prompt is not None
        assert "Validation Status" in prompt
        assert "Questions" in prompt
        assert "APPROVE" in prompt

    def test_feedback_recording(self, setup):
        """Test recording user feedback."""
        owner, pet, plan, validation, checkpoint = setup
        
        checkpoint.record_feedback(owner, pet, plan, "approve", "Good schedule!")
        
        assert len(checkpoint.feedback_history) == 1
        assert checkpoint.feedback_history[0]['decision'] == 'approve'

    def test_feedback_summary(self, setup):
        """Test feedback summary generation."""
        owner, pet, plan, validation, checkpoint = setup
        
        checkpoint.record_feedback(owner, pet, plan, "approve")
        checkpoint.record_feedback(owner, pet, plan, "approve")
        checkpoint.record_feedback(owner, pet, plan, "reject", "Too tight")
        
        summary = checkpoint.get_feedback_summary()
        
        assert summary['total_plans_reviewed'] == 3
        assert summary['approved'] == 2
        assert summary['rejected'] == 1


class TestIntegration:
    """Integration tests combining agent, validation, and logging."""

    @pytest.fixture
    def setup(self):
        """Setup for integration tests."""
        owner = Owner(name="Emily", available_minutes=180, preferred_start_time="07:00")
        pet = Pet(name="Daisy", species="dog", age=4, breed="Corgi")
        owner.add_pet(pet)
        
        scheduler = Scheduler(owner, pet)
        tasks = [
            CareTask("Breakfast", 10, "high", "daily", "Feeding"),
            CareTask("Morning Run", 40, "high", "daily", "Exercise"),
            CareTask("Training", 30, "medium", "daily", "Training"),
            CareTask("Afternoon Walk", 20, "medium", "daily", "Exercise"),
        ]
        
        for task in tasks:
            scheduler.add_task(task)
        
        agent = SchedulingAgent()
        validator = PlanValidator()
        logger = AuditLogger()
        checkpoint = HumanReviewCheckpoint()
        
        return owner, pet, scheduler, agent, validator, logger, checkpoint

    def test_full_workflow(self, setup):
        """Test complete workflow: generate → validate → log → review."""
        owner, pet, scheduler, agent, validator, logger, checkpoint = setup
        
        # Step 1: Generate plan
        plan = agent.generate_schedule(owner, pet, scheduler)
        logger.log_plan_generated(owner, pet, plan)
        
        assert plan is not None
        assert plan.total_duration > 0
        
        # Step 2: Validate
        validation = validator.validate_plan(plan, owner, scheduler)
        logger.log_plan_validated(owner, pet, validation)
        
        assert isinstance(validation, ValidationResult)
        
        # Step 3: Create review prompt
        review_prompt = checkpoint.create_review_prompt(plan, validation)
        assert review_prompt is not None
        
        # Step 4: Simulate user approval
        checkpoint.record_feedback(owner, pet, plan, "approve")
        logger.log_plan_approved(owner, pet, plan)
        
        # Step 5: Check audit trail
        summary = logger.get_summary()
        assert summary['plans_generated'] >= 1
        assert summary['plans_validated'] >= 1
        assert summary['plans_approved'] >= 1

    def test_workflow_with_rejection_and_retry(self, setup):
        """Test workflow when user rejects and retries."""
        owner, pet, scheduler, agent, validator, logger, checkpoint = setup
        
        # First attempt
        plan1 = agent.generate_schedule(owner, pet, scheduler, start_time="08:00", end_time="18:00")
        logger.log_plan_generated(owner, pet, plan1)
        checkpoint.record_feedback(owner, pet, plan1, "reject", "Start time too late")
        logger.log_plan_rejected(owner, pet, "Start time too late")
        
        # Second attempt
        plan2 = agent.generate_schedule(owner, pet, scheduler, start_time="07:00", end_time="17:00")
        logger.log_plan_generated(owner, pet, plan2)
        checkpoint.record_feedback(owner, pet, plan2, "approve", "Better timing")
        logger.log_plan_approved(owner, pet, plan2)
        
        # Verify audit trail
        summary = logger.get_summary()
        assert summary['plans_generated'] >= 2
        assert summary['plans_rejected'] >= 1
        assert summary['plans_approved'] >= 1


# Run tests with: pytest tests/test_pawpal.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
