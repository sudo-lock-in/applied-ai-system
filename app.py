import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pawpal_system import CareTask, Pet, Owner, Scheduler
from agent import SchedulingAgent, SchedulePlan
from reliability import PlanValidator, AuditLogger, HumanReviewCheckpoint

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to **PawPal+** – Your intelligent pet care planning assistant!

This app helps you organize and optimize pet care tasks based on time availability, priority, and pet needs.
"""
)


# Initialize session state for owner
if "owner" not in st.session_state:
    st.session_state.owner = Owner(
        name="Jordan",
        available_minutes=120,
        preferred_start_time="08:00"
    )

if "pets" not in st.session_state:
    st.session_state.pets = []

if "schedulers" not in st.session_state:
    st.session_state.schedulers = {}

owner = st.session_state.owner

# Create main navigation tabs
main_tabs = st.tabs(["⚙️ Setup", " Generate AI Plan"])

# ===================== TAB 1: SETUP =====================
with main_tabs[0]:
    st.header("⚙️ Setup Owner & Pets")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👤 Owner Configuration")
        owner.name = st.text_input("Owner name", value=owner.name)
        owner.available_minutes = st.number_input("Available minutes", value=owner.available_minutes, min_value=15, max_value=480)
        preferred_time = st.time_input("Preferred start time", value=datetime.strptime(owner.preferred_start_time, "%H:%M").time())
        owner.preferred_start_time = preferred_time.strftime("%H:%M")
    
    with col2:
        st.subheader("🐾 Your Pets")
        if st.session_state.pets:
            for i, pet in enumerate(st.session_state.pets, 1):
                st.write(f"**{i}. {pet.name}**")
                st.caption(f"🐶 {pet.species.capitalize()} • {pet.breed} • {pet.age} years old")
        else:
            st.info("No pets added yet. Add one below!")
    
    st.divider()
    
    st.subheader("➕ Add New Pet")
    col1, col2 = st.columns(2)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
        breed = st.text_input("Breed", value="Mixed")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "other"])
        age = st.number_input("Age (years)", value=2, min_value=0, max_value=25)
    
    if st.button("✅ Add Pet", use_container_width=True):
        new_pet = Pet(name=pet_name, species=species, breed=breed, age=age)
        st.session_state.pets.append(new_pet)
        owner.add_pet(new_pet)
        st.session_state.schedulers[pet_name] = Scheduler(owner, new_pet)
        st.success(f"✓ {pet_name} added!")
        st.rerun()
    
    st.divider()
    
    st.subheader("➕ Add Task to Pet")
    if st.session_state.pets:
        selected_pet = st.selectbox("Select pet", [p.name for p in st.session_state.pets], key="add_task_pet_selector")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with col3:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.text_input("Category", value="Exercise")
        with col2:
            frequency = st.selectbox("Frequency", ["one-time", "daily", "weekly", "monthly"], index=0)
        
        description = st.text_area("Description", value="", height=80)
        
        if st.button("✅ Add Task", use_container_width=True):
            try:
                new_task = CareTask(
                    title=task_title,
                    duration_minutes=int(duration),
                    priority=priority,
                    category=category,
                    frequency=frequency,
                    description=description
                )
                
                pet = owner.find_pet_by_name(selected_pet)
                if pet:
                    scheduler = st.session_state.schedulers[selected_pet]
                    scheduler.add_task(new_task)
                    st.success(f"✅ Task '{task_title}' successfully added to {selected_pet}!")
                    import time
                    time.sleep(0.5)
                    st.rerun()
            except ValueError as e:
                st.error(f"✗ Error: {e}")
    else:
        st.info("👆 Add a pet first to create tasks.")

# ===================== TAB 2: GENERATE AI PLAN =====================
with main_tabs[1]:
    st.header("🚀 Generate AI-Powered Schedule")
    
    if st.session_state.pets:
        # Mode selector
        st.subheader("⚙️ Scheduling Mode")
        mode = st.radio(
            "Choose scheduling mode:",
            ["Deterministic", "Ollama (Agentic Loop)"],
            index=0,
            help="Deterministic: Fast, predictable (no LLM)\nOllama (Agentic): Local LLM with plan-act-check-refine loop"
        )
        
        st.divider()
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_pet_ai = st.selectbox(
                "Generate AI schedule for:",
                [p.name for p in st.session_state.pets],
                key="ai_schedule_selector"
            )
        
        with col2:
            st.write("")
            st.write("")
            if st.button("🚀 Generate Schedule", use_container_width=True):
                pet_for_ai = owner.find_pet_by_name(selected_pet_ai)
                scheduler_ai = st.session_state.schedulers[selected_pet_ai]
                
                if scheduler_ai.get_tasks():
                    use_ollama = (mode == "Ollama (Agentic Loop)")
                    agent = SchedulingAgent(use_ollama=use_ollama, max_iterations=3)
                    start_time = owner.preferred_start_time
                    end_time_minutes = (datetime.strptime(start_time, "%H:%M") + timedelta(minutes=owner.available_minutes)).time()
                    end_time = end_time_minutes.strftime("%H:%M")
                    
                    with st.spinner(f"⏳ Generating schedule ({mode})..."):
                        plan = agent.generate_schedule(owner, pet_for_ai, scheduler_ai, start_time=start_time, end_time=end_time)
                    
                    st.session_state.current_plan = plan
                    st.session_state.current_scheduler_ai = scheduler_ai
                    st.session_state.current_pet_ai = pet_for_ai
                    
                    if use_ollama and not agent.ollama_available:
                        st.warning(f"⚠️ Ollama not available. Used deterministic mode instead.\nStart Ollama: ollama serve")
                    
                    st.success(f"✅ Schedule generated! (Method: {plan.generation_method}, Iterations: {plan.iterations})")
                else:
                    st.warning("⚠️ Add tasks to the pet first!")
        
        if "current_plan" in st.session_state:
            plan = st.session_state.current_plan
            scheduler_ai = st.session_state.current_scheduler_ai
            pet_for_ai = st.session_state.current_pet_ai
            
            st.divider()
            st.markdown("## 📋 Generated Schedule")
            
            # Show generation details
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Method", plan.generation_method)
            with col2:
                st.metric("Iterations", plan.iterations)
            with col3:
                status = "✅ Valid" if plan.is_validated else "⚠️ Unvalidated"
                st.metric("Status", status)
            with col4:
                st.metric("Tasks", len(plan.scheduled_tasks))
            
            with st.expander("💭 AI Reasoning", expanded=True):
                st.markdown(plan.explanation)
            
            if plan.refinement_history and plan.iterations > 1:
                with st.expander(f"🔄 Refinement History ({len(plan.refinement_history)} feedback items)"):
                    for i, feedback in enumerate(plan.refinement_history, 1):
                        st.text(f"{i}. {feedback}")
            
            if plan.scheduled_tasks:
                st.markdown("**Scheduled Tasks:**")
                task_df = pd.DataFrame(plan.scheduled_tasks)
                st.dataframe(task_df, use_container_width=True, hide_index=True)
                st.metric("⏱️ Total Duration", f"{plan.total_duration} min / {owner.available_minutes} min")
            
            st.divider()
            st.markdown("## ✅ Plan Validation")
            
            validator = PlanValidator()
            validation = validator.validate_plan(plan, owner, scheduler_ai)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if validation.is_valid:
                    st.success("✅ Valid Plan")
                else:
                    st.error("❌ Invalid Plan")
            with col2:
                st.info(f"Checks: {validation.checks_passed}/{validation.checks_total}")
            with col3:
                st.write("")
            
            with st.expander("📊 Validation Details"):
                st.markdown(validation.summary())
                
                if validation.errors:
                    st.markdown("**Critical Issues:**")
                    for error in validation.errors:
                        st.error(f"🚨 {error}")
                
                if validation.warnings:
                    st.markdown("**Warnings:**")
                    for warning in validation.warnings:
                        st.warning(f"⚠️ {warning}")
            
            st.divider()
            st.markdown("## 👤 Human Review & Approval")
            
            checkpoint = HumanReviewCheckpoint()
            
            with st.expander("📝 Review Checklist"):
                st.markdown("""
## ❓ Questions for You:
1. Does this schedule work for your lifestyle?
2. Are the start times realistic?
3. Any tasks you'd like to reorder or adjust?
4. Any concerns about pet welfare?
""")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✅ Approve Plan", use_container_width=True, key="approve_plan"):
                    try:
                        if "audit_logger" not in st.session_state:
                            st.session_state.audit_logger = AuditLogger()
                        
                        logger = st.session_state.audit_logger
                        logger.log_plan_generated(owner, pet_for_ai, plan, method="ai_agent")
                        logger.log_plan_validated(owner, pet_for_ai, validation)
                        checkpoint.record_feedback(owner, pet_for_ai, plan, "approve", "Approved by user")
                        logger.log_plan_approved(owner, pet_for_ai, plan)
                        
                        # Update tasks with scheduled times from the plan
                        if plan.scheduled_tasks and len(plan.scheduled_tasks) > 0:
                            for scheduled_task_info in plan.scheduled_tasks:
                                task_title = scheduled_task_info.get("Task")
                                scheduled_time = scheduled_task_info.get("Time")
                                
                                # Find and update the actual task object in the scheduler
                                for task in scheduler_ai.get_tasks():
                                    if task.title == task_title and scheduled_time:
                                        task.scheduled_time = scheduled_time
                                        break
                        
                        st.success("✅ Plan approved! Tasks have been scheduled and saved.")
                        st.balloons()
                        import time
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error approving plan: {str(e)}")
            
            with col2:
                if st.button("❌ Reject Plan", use_container_width=True, key="reject_plan"):
                    if "audit_logger" not in st.session_state:
                        st.session_state.audit_logger = AuditLogger()
                    
                    logger = st.session_state.audit_logger
                    checkpoint.record_feedback(owner, pet_for_ai, plan, "reject", "Rejected by user")
                    logger.log_plan_rejected(owner, pet_for_ai, "Rejected by user")
                    
                    st.info("↩️ Plan rejected. Adjust constraints and try again.")
                    del st.session_state.current_plan
                    st.rerun()
            
            with col3:
                if st.button("🔄 Regenerate", use_container_width=True, key="regenerate_plan"):
                    del st.session_state.current_plan
                    st.rerun()
        
        st.divider()
        st.subheader("✏️ Manage Tasks")
        
        manage_pet = st.selectbox("Select pet to manage:", [p.name for p in st.session_state.pets], key="manage_pet_selector")
        manage_scheduler = st.session_state.schedulers[manage_pet]
        
        if manage_scheduler.get_tasks():
            tasks = manage_scheduler.get_tasks()
            
            for i, task in enumerate(tasks):
                col1, col2, col3_edit, col4_delete = st.columns([2, 1, 1, 1])
                
                with col1:
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪")
                    completion_emoji = "✅" if task.is_completed else "⏳"
                    st.write(f"{completion_emoji} {priority_emoji} **{task.title}** ({task.duration_minutes}m) - {task.category}")
                
                with col2:
                    if not task.is_completed:
                        if st.button("✓ Complete", key=f"complete_{i}", use_container_width=True):
                            task.mark_completed()
                            st.rerun()
                    else:
                        if st.button("↩ Undo", key=f"undo_{i}", use_container_width=True):
                            task.mark_incomplete()
                            st.rerun()
                
                with col3_edit:
                    if st.button("✏️ Edit", key=f"edit_{i}", use_container_width=True):
                        st.session_state[f"editing_{i}"] = True
                        st.rerun()
                
                with col4_delete:
                    if st.button("🗑️ Delete", key=f"delete_{i}", use_container_width=True):
                        manage_scheduler.remove_task(task)
                        st.rerun()
                
                if st.session_state.get(f"editing_{i}", False):
                    with st.expander(f"✏️ Edit {task.title}"):
                        new_title = st.text_input("Title", value=task.title, key=f"edit_title_{i}")
                        new_duration = st.number_input("Duration (minutes)", value=task.duration_minutes, key=f"edit_duration_{i}")
                        new_priority = st.selectbox("Priority", ["low", "medium", "high"], index=["low", "medium", "high"].index(task.priority), key=f"edit_priority_{i}")
                        new_category = st.text_input("Category", value=task.category, key=f"edit_category_{i}")
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("✅ Save", key=f"save_edit_{i}"):
                                task.title = new_title
                                task.duration_minutes = new_duration
                                task.priority = new_priority
                                task.category = new_category
                                st.session_state[f"editing_{i}"] = False
                                st.rerun()
                        with col_cancel:
                            if st.button("❌ Cancel", key=f"cancel_edit_{i}"):
                                st.session_state[f"editing_{i}"] = False
                                st.rerun()
        else:
            st.info("No tasks yet. Add tasks in the Setup tab first.")
    else:
        st.info("👆 Add a pet and tasks first to generate a schedule.")
