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
main_tabs = st.tabs(["⚙️ Setup", "📅 View Schedule", "🚀 Generate AI Plan", "✏️ Manage Tasks"])

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
                    st.success(f"✓ Task '{task_title}' added to {selected_pet}!")
                    st.rerun()
            except ValueError as e:
                st.error(f"✗ Error: {e}")
    else:
        st.info("👆 Add a pet first to create tasks.")

# ===================== TAB 2: VIEW SCHEDULE =====================
with main_tabs[1]:
    st.header("📅 View Schedule")
    
    if st.session_state.pets:
        selected_pet_for_schedule = st.selectbox("View schedule for:", [p.name for p in st.session_state.pets], key="view_schedule_selector")
        
        pet = owner.find_pet_by_name(selected_pet_for_schedule)
        scheduler = st.session_state.schedulers[selected_pet_for_schedule]
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 Priority Plan", "⏱️ Duration Sort", "📊 Analytics", "🔄 Recurring", "⚠️ Conflicts"])
        
        with tab1:
            st.subheader("Tasks Sorted by Priority")
            
            if scheduler.get_tasks():
                priority_sorted = scheduler.sort_tasks(by="priority")
                
                table_data = []
                for i, task in enumerate(priority_sorted, 1):
                    if task.is_completed:
                        status = "✅ Completed"
                    elif task.scheduled_time:
                        status = f"📅 Scheduled @ {task.scheduled_time}"
                    else:
                        status = "⏳ Pending"
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪")
                    table_data.append({
                        "#": i,
                        "Priority": f"{priority_emoji} {task.priority.upper()}",
                        "Task": task.title,
                        "Duration": f"{task.duration_minutes} min",
                        "Category": task.category,
                        "Status": status
                    })
                
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📋 Total", len(scheduler.get_tasks()))
                with col2:
                    st.metric("⏳ Pending", len(scheduler.get_pending_tasks()))
                with col3:
                    st.metric("✅ Completed", len(scheduler.get_completed_tasks()))
                with col4:
                    st.metric("⏱️ Duration", f"{scheduler.calculate_total_duration()} min")
            else:
                st.info("No tasks yet. Add a task to get started!")
        
        with tab2:
            st.subheader("Tasks Sorted by Duration")
            
            if scheduler.get_tasks():
                duration_sorted = scheduler.sort_tasks(by="duration")
                
                table_data = []
                for i, task in enumerate(duration_sorted, 1):
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪")
                    table_data.append({
                        "#": i,
                        "Duration": f"{task.duration_minutes} min",
                        "Task": task.title,
                        "Priority": f"{priority_emoji} {task.priority.upper()}",
                        "Category": task.category,
                        "Frequency": task.frequency.upper()
                    })
                
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                st.markdown("**⏱️ Time Breakdown by Category**")
                chart_data = {}
                for task in duration_sorted:
                    category = task.category
                    if category not in chart_data:
                        chart_data[category] = 0
                    chart_data[category] += task.duration_minutes
                
                if chart_data:
                    st.bar_chart(pd.Series(chart_data))
            else:
                st.info("No tasks yet.")
        
        with tab3:
            st.subheader("Schedule Analytics")
            
            if scheduler.get_tasks():
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Priority Distribution**")
                    high = len(scheduler.filter_tasks(priority="high"))
                    medium = len(scheduler.filter_tasks(priority="medium"))
                    low = len(scheduler.filter_tasks(priority="low"))
                    priority_counts = pd.Series({"🔴 High": high, "🟡 Medium": medium, "🟢 Low": low})
                    st.bar_chart(priority_counts)
                
                with col2:
                    st.markdown("**Task Status**")
                    pending = len(scheduler.get_pending_tasks())
                    completed = len(scheduler.get_completed_tasks())
                    status_counts = pd.Series({"⏳ Pending": pending, "✅ Completed": completed})
                    st.bar_chart(status_counts)
                
                with col3:
                    st.markdown("**Category Distribution**")
                    categories = {}
                    for task in scheduler.get_tasks():
                        if task.category not in categories:
                            categories[task.category] = 0
                        categories[task.category] += 1
                    if categories:
                        st.bar_chart(pd.Series(categories))
                
                st.markdown("---")
                st.markdown("**Frequency Analysis**")
                col1, col2, col3, col4 = st.columns(4)
                
                one_time = len(scheduler.filter_tasks(frequency="one-time"))
                daily = len(scheduler.filter_tasks(frequency="daily"))
                weekly = len(scheduler.filter_tasks(frequency="weekly"))
                monthly = len(scheduler.filter_tasks(frequency="monthly"))
                
                with col1:
                    st.metric("🎯 One-Time", one_time)
                with col2:
                    st.metric("📅 Daily", daily)
                with col3:
                    st.metric("📆 Weekly", weekly)
                with col4:
                    st.metric("📋 Monthly", monthly)
            else:
                st.info("Add tasks to see analytics.")
        
        with tab4:
            st.subheader("Recurring Tasks")
            
            if scheduler.get_tasks():
                recurring_tasks = [t for t in scheduler.get_tasks() if t.frequency != "one-time"]
                
                if recurring_tasks:
                    st.markdown(f"**Found {len(recurring_tasks)} recurring task(s)**")
                    
                    table_data = []
                    for task in recurring_tasks:
                        next_occ = task.create_next_occurrence()
                        next_due = next_occ.due_date.strftime("%Y-%m-%d") if next_occ and next_occ.due_date else "N/A"
                        
                        table_data.append({
                            "Task": task.title,
                            "Frequency": task.frequency.upper(),
                            "Duration": f"{task.duration_minutes} min",
                            "Next Occurrence": next_due,
                            "Category": task.category
                        })
                    
                    df = pd.DataFrame(table_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    with st.expander("📈 7-Day Expansion Preview"):
                        try:
                            expanded = scheduler.expand_recurring_tasks(days=7)
                            if expanded:
                                st.success(f"✅ {len(expanded)} task occurrences over 7 days")
                                expansion_data = []
                                for task, day_offset in expanded[:10]:
                                    expansion_data.append({
                                        "Day": f"Day {day_offset}",
                                        "Task": task.title,
                                        "Frequency": task.frequency.upper()
                                    })
                                st.dataframe(pd.DataFrame(expansion_data), use_container_width=True, hide_index=True)
                                if len(expanded) > 10:
                                    st.caption(f"... and {len(expanded) - 10} more occurrences")
                        except Exception as e:
                            st.warning(f"Could not expand tasks: {e}")
                else:
                    st.info("No recurring tasks. All tasks are one-time.")
            else:
                st.info("Add tasks to see recurring schedules.")
        
        with tab5:
            st.subheader("Schedule Conflicts")
            
            if scheduler.get_tasks():
                has_conflicts = scheduler.has_scheduling_conflicts()
                
                if has_conflicts:
                    st.error("🚨 **Scheduling conflicts detected!**")
                    
                    conflicts = scheduler.detect_time_conflicts()
                    if conflicts:
                        st.markdown(f"Found {len(conflicts)} conflict(s):")
                        
                        for i, (task1, task2) in enumerate(conflicts, 1):
                            with st.expander(f"Conflict {i}: {task1.title} ↔ {task2.title}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**{task1.title}**")
                                    st.write(f"• Duration: {task1.duration_minutes} min")
                                    st.write(f"• Time: {task1.scheduled_time}")
                                    st.write(f"• Priority: {task1.priority}")
                                with col2:
                                    st.write(f"**{task2.title}**")
                                    st.write(f"• Duration: {task2.duration_minutes} min")
                                    st.write(f"• Time: {task2.scheduled_time}")
                                    st.write(f"• Priority: {task2.priority}")
                    
                    warnings = scheduler.get_conflict_warnings()
                    if warnings:
                        st.markdown("**Conflict Warnings:**")
                        for warning in warnings:
                            st.warning(warning)
                else:
                    st.success("✅ **No scheduling conflicts!** Your schedule looks good.")
            else:
                st.info("No tasks to check for conflicts.")
    else:
        st.info("👆 Add a pet and tasks first to view schedule.")

# ===================== TAB 3: GENERATE AI PLAN =====================
with main_tabs[2]:
    st.header("🚀 Generate AI-Powered Schedule")
    
    if st.session_state.pets:
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
                    agent = SchedulingAgent()
                    start_time = owner.preferred_start_time
                    end_time_minutes = (datetime.strptime(start_time, "%H:%M") + timedelta(minutes=owner.available_minutes)).time()
                    end_time = end_time_minutes.strftime("%H:%M")
                    
                    plan = agent.generate_schedule(owner, pet_for_ai, scheduler_ai, start_time=start_time, end_time=end_time)
                    
                    st.session_state.current_plan = plan
                    st.session_state.current_scheduler_ai = scheduler_ai
                    st.session_state.current_pet_ai = pet_for_ai
                    st.success("✅ Schedule generated!")
                else:
                    st.warning("⚠️ Add tasks to the pet first!")
        
        if "current_plan" in st.session_state:
            plan = st.session_state.current_plan
            scheduler_ai = st.session_state.current_scheduler_ai
            pet_for_ai = st.session_state.current_pet_ai
            
            st.divider()
            st.markdown("## 📋 Generated Schedule")
            
            with st.expander("💭 AI Reasoning", expanded=True):
                st.markdown(plan.explanation)
            
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
                st.write(f"Severity: {validation.severity.upper()}")
            
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
            review_prompt = checkpoint.create_review_prompt(plan, validation)
            
            with st.expander("📝 Review Checklist"):
                st.markdown(review_prompt)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✅ Approve Plan", use_container_width=True, key="approve_plan"):
                    if "audit_logger" not in st.session_state:
                        st.session_state.audit_logger = AuditLogger()
                    
                    logger = st.session_state.audit_logger
                    logger.log_plan_generated(owner, pet_for_ai, plan, method="ai_agent")
                    logger.log_plan_validated(owner, pet_for_ai, validation)
                    checkpoint.record_feedback(owner, pet_for_ai, plan, "approve", "Approved by user")
                    logger.log_plan_approved(owner, pet_for_ai, plan)
                    
                    # Update tasks with scheduled times from the plan
                    for scheduled_task_info in plan.scheduled_tasks:
                        task_title = scheduled_task_info.get("Task")
                        scheduled_time = scheduled_task_info.get("Time")
                        
                        # Find and update the actual task object
                        for task in scheduler_ai.get_tasks():
                            if task.title == task_title and scheduled_time:
                                task.scheduled_time = scheduled_time
                    
                    st.success("✅ Plan approved! Schedule saved.")
                    st.balloons()
            
            with col2:
                if st.button("❌ Reject Plan", use_container_width=True, key="reject_plan"):
                    if "audit_logger" not in st.session_state:
                        st.session_state.audit_logger = AuditLogger()
                    
                    logger = st.session_state.audit_logger
                    checkpoint.record_feedback(owner, pet_for_ai, plan, "reject", "Rejected by user")
                    logger.log_plan_rejected(owner, pet_for_ai, "Rejected by user")
                    
                    st.info("↩️ Plan rejected. Adjust constraints and try again.")
                    del st.session_state.current_plan
            
            with col3:
                if st.button("🔄 Regenerate", use_container_width=True, key="regenerate_plan"):
                    del st.session_state.current_plan
                    st.rerun()
    else:
        st.info("👆 Add a pet and tasks first to generate a schedule.")

# ===================== TAB 4: MANAGE TASKS =====================
with main_tabs[3]:
    st.header("✏️ Manage Tasks")
    
    if st.session_state.pets:
        manage_pet = st.selectbox("Select pet to manage:", [p.name for p in st.session_state.pets], key="manage_pet_selector")
        manage_scheduler = st.session_state.schedulers[manage_pet]
        
        if manage_scheduler.get_tasks():
            st.subheader("Tasks for " + manage_pet)
            
            tasks = manage_scheduler.get_tasks()
            
            for i, task in enumerate(tasks):
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                
                with col1:
                    if task.is_completed:
                        status_emoji = "✅"
                    elif task.scheduled_time:
                        status_emoji = "📅"
                    else:
                        status_emoji = "⏳"
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪")
                    time_info = f" @ {task.scheduled_time}" if task.scheduled_time else ""
                    st.write(f"{status_emoji} {priority_emoji} **{task.title}** ({task.duration_minutes}m){time_info}")
                
                with col2:
                    if not task.is_completed:
                        if st.button("✓ Complete", key=f"complete_{i}", use_container_width=True):
                            task.mark_completed()
                            st.rerun()
                    else:
                        if st.button("↩ Undo", key=f"undo_{i}", use_container_width=True):
                            task.mark_incomplete()
                            st.rerun()
                
                with col3:
                    if st.button("⏰ Schedule", key=f"schedule_{i}", use_container_width=True):
                        st.session_state[f"scheduling_{i}"] = True
                        st.rerun()
                
                with col4:
                    if st.button("✏️ Edit", key=f"edit_{i}", use_container_width=True):
                        st.session_state[f"editing_{i}"] = True
                        st.rerun()
                
                with col5:
                    if st.button("🗑️ Delete", key=f"delete_{i}", use_container_width=True):
                        manage_scheduler.remove_task(task)
                        st.rerun()
                
                if st.session_state.get(f"scheduling_{i}", False):
                    with st.expander(f"⏰ Schedule {task.title}"):
                        scheduled_time = st.time_input("Start time", key=f"time_{i}")
                        time_str = scheduled_time.strftime("%H:%M")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Confirm", key=f"confirm_schedule_{i}"):
                                success = manage_scheduler.schedule_task_at_time(task, time_str)
                                if success:
                                    st.session_state[f"scheduling_{i}"] = False
                                    st.rerun()
                                else:
                                    st.error("Conflict detected!")
                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_schedule_{i}"):
                                st.session_state[f"scheduling_{i}"] = False
                                st.rerun()
                
                if st.session_state.get(f"editing_{i}", False):
                    with st.expander(f"✏️ Edit {task.title}"):
                        new_title = st.text_input("Title", value=task.title, key=f"edit_title_{i}")
                        new_duration = st.number_input("Duration", value=task.duration_minutes, key=f"edit_duration_{i}")
                        new_priority = st.selectbox("Priority", ["low", "medium", "high"], index=["low", "medium", "high"].index(task.priority), key=f"edit_priority_{i}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Save", key=f"save_edit_{i}"):
                                task.title = new_title
                                task.duration_minutes = new_duration
                                task.priority = new_priority
                                st.session_state[f"editing_{i}"] = False
                                st.rerun()
                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_edit_{i}"):
                                st.session_state[f"editing_{i}"] = False
                                st.rerun()
            
            st.divider()
            st.subheader("Summary")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("📋 Total", len(manage_scheduler.get_tasks()))
            with col2:
                pending_count = len([t for t in manage_scheduler.get_tasks() if not t.is_completed and not t.scheduled_time])
                st.metric("⏳ Pending", pending_count)
            with col3:
                st.metric("✅ Completed", len(manage_scheduler.get_completed_tasks()))
            with col4:
                st.metric("⏰ Scheduled", len([t for t in manage_scheduler.get_tasks() if t.scheduled_time]))
            with col5:
                rate = (len(manage_scheduler.get_completed_tasks()) / len(manage_scheduler.get_tasks()) * 100) if manage_scheduler.get_tasks() else 0
                st.metric("📊 Completion", f"{rate:.0f}%")
            
            st.divider()
            st.subheader("Time Capacity")
            
            total_all_pets = sum(t.duration_minutes for pet in owner.pets for t in pet.get_tasks())
            available = owner.available_minutes
            percentage = (total_all_pets / available * 100) if available > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("⏱️ Scheduled", f"{total_all_pets} min")
            with col2:
                st.metric("📊 Available", f"{available} min")
            with col3:
                if total_all_pets > available:
                    st.error(f"🚨 OVERBOOKED: {percentage:.0f}%")
                else:
                    st.success(f"✅ Usage: {percentage:.0f}%")
        else:
            st.info("No tasks for this pet yet.")
    else:
        st.info("Add a pet first.")
