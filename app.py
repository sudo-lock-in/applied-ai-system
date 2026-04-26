import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pawpal_system import CareTask, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to **PawPal+** – Your intelligent pet care planning assistant!

This app helps you organize and optimize pet care tasks based on time availability, priority, and pet needs.
"""
)

st.divider()

st.subheader("👤 Owner & Pet Setup")

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

# Owner configuration
col1, col2 = st.columns(2)
with col1:
    owner.name = st.text_input("Owner name", value=owner.name)
with col2:
    owner.available_minutes = st.number_input("Available minutes", value=owner.available_minutes, min_value=15, max_value=480)

st.markdown("### Add Pet")
col1, col2 = st.columns(2)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "other"])

col1, col2 = st.columns(2)
with col1:
    breed = st.text_input("Breed", value="Mixed")
with col2:
    age = st.number_input("Age (years)", value=2, min_value=0, max_value=25)

if st.button("Add Pet"):
    new_pet = Pet(name=pet_name, species=species, breed=breed, age=age)
    st.session_state.pets.append(new_pet)
    owner.add_pet(new_pet)
    st.session_state.schedulers[pet_name] = Scheduler(owner, new_pet)
    st.success(f"✓ {pet_name} added!")
    st.rerun()

if st.session_state.pets:
    st.write(f"**Pets ({len(st.session_state.pets)}):**")
    for pet in st.session_state.pets:
        st.write(f"• {pet.name} ({pet.species}, {pet.age} years old)")

st.markdown("### Add Task to Pet")

if st.session_state.pets:
    selected_pet = st.selectbox("Select pet", [p.name for p in st.session_state.pets])
    
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
    
    description = st.text_area("Description", value="")
    
    if st.button("Add Task"):
        try:
            new_task = CareTask(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                category=category,
                frequency=frequency,
                description=description
            )
            
            # Add task to selected pet and scheduler
            pet = owner.find_pet_by_name(selected_pet)
            if pet:
                scheduler = st.session_state.schedulers[selected_pet]
                scheduler.add_task(new_task)
                st.success(f"✓ Task '{task_title}' added to {selected_pet}!")
                st.rerun()
        except ValueError as e:
            st.error(f"✗ Error: {e}")
else:
    st.info("Add a pet first to create tasks.")

st.divider()

st.subheader("📅 Build & View Schedule")

if st.session_state.pets:
    selected_pet_for_schedule = st.selectbox("View schedule for:", [p.name for p in st.session_state.pets], key="schedule_selector")
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 Priority Plan", "⏱️ Duration Sort", "📊 Analytics", "🔄 Recurring", "⚠️ Conflicts"])
    
    pet = owner.find_pet_by_name(selected_pet_for_schedule)
    scheduler = st.session_state.schedulers[selected_pet_for_schedule]
    
    with tab1:
        st.markdown("#### Tasks Sorted by Priority")
        
        if scheduler.get_tasks():
            # Sort by priority (high → low)
            priority_sorted = scheduler.sort_tasks(by="priority")
            
            # Create table data
            table_data = []
            for i, task in enumerate(priority_sorted, 1):
                status = "✅ Completed" if task.is_completed else "⏳ Pending"
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
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📋 Total Tasks", len(scheduler.get_tasks()))
            with col2:
                st.metric("⏳ Pending", len(scheduler.get_pending_tasks()))
            with col3:
                st.metric("✅ Completed", len(scheduler.get_completed_tasks()))
            with col4:
                st.metric("⏱️ Total Duration", f"{scheduler.calculate_total_duration()} min")
        else:
            st.info(f"ℹ️ No tasks yet for {selected_pet_for_schedule}. Add a task to get started!")
    
    with tab2:
        st.markdown("#### Tasks Sorted by Duration (Shortest First)")
        
        if scheduler.get_tasks():
            # Sort by duration
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
            
            # Time efficiency chart
            st.markdown("**⏱️ Time Breakdown**")
            chart_data = {}
            for task in duration_sorted:
                category = task.category
                if category not in chart_data:
                    chart_data[category] = 0
                chart_data[category] += task.duration_minutes
            
            if chart_data:
                st.bar_chart(pd.Series(chart_data))
        else:
            st.info(f"ℹ️ No tasks yet for {selected_pet_for_schedule}.")
    
    with tab3:
        st.markdown("#### 📊 Schedule Analytics")
        
        if scheduler.get_tasks():
            col1, col2, col3 = st.columns(3)
            
            # Priority breakdown
            with col1:
                st.markdown("**Priority Distribution**")
                high = len(scheduler.filter_tasks(priority="high"))
                medium = len(scheduler.filter_tasks(priority="medium"))
                low = len(scheduler.filter_tasks(priority="low"))
                
                priority_counts = pd.Series({
                    "🔴 High": high,
                    "🟡 Medium": medium,
                    "🟢 Low": low
                })
                st.bar_chart(priority_counts)
            
            # Status breakdown
            with col2:
                st.markdown("**Task Status**")
                pending = len(scheduler.get_pending_tasks())
                completed = len(scheduler.get_completed_tasks())
                
                status_counts = pd.Series({
                    "⏳ Pending": pending,
                    "✅ Completed": completed
                })
                st.bar_chart(status_counts)
            
            # Category breakdown
            with col3:
                st.markdown("**Category Distribution**")
                categories = {}
                for task in scheduler.get_tasks():
                    if task.category not in categories:
                        categories[task.category] = 0
                    categories[task.category] += 1
                
                if categories:
                    st.bar_chart(pd.Series(categories))
            
            # Frequency analysis
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
            st.info(f"ℹ️ Add tasks to see analytics.")
    
    with tab4:
        st.markdown("#### 🔄 Recurring Tasks")
        
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
                
                # Task expansion preview
                with st.expander("📈 7-Day Expansion Preview"):
                    try:
                        expanded = scheduler.expand_recurring_tasks(days=7)
                        if expanded:
                            st.success(f"✅ {len(expanded)} task occurrences over 7 days")
                            expansion_data = []
                            for task, day_offset in expanded[:10]:  # Show first 10
                                expansion_data.append({
                                    "Day": f"Day {day_offset}",
                                    "Task": task.title,
                                    "Frequency": task.frequency.upper()
                                })
                            st.dataframe(pd.DataFrame(expansion_data), use_container_width=True, hide_index=True)
                            if len(expanded) > 10:
                                st.caption(f"... and {len(expanded) - 10} more occurrences")
                    except Exception as e:
                        st.warning(f"⚠️ Could not expand tasks: {e}")
            else:
                st.info("ℹ️ No recurring tasks. All tasks are one-time.")
        else:
            st.info(f"ℹ️ Add tasks to manage recurring schedules.")
    
    with tab5:
        st.markdown("#### ⚠️ Schedule Conflicts")
        
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
                
                # Show available time slots
                if scheduler.get_tasks():
                    with st.expander("💡 Available Time Slots"):
                        try:
                            suggested_time = scheduler.suggest_next_available_time(duration_minutes=30, start_from="08:00")
                            if suggested_time:
                                st.success(f"✅ Next available slot for 30-min task: **{suggested_time}**")
                        except Exception as e:
                            st.info(f"ℹ️ Time slot suggestion unavailable")
else:
    st.info("👆 Add a pet and tasks to build a schedule!")

st.divider()

st.subheader("✏️ Manage Tasks")

if st.session_state.pets:
    manage_pet = st.selectbox("Select pet to manage tasks:", [p.name for p in st.session_state.pets], key="manage_selector")
    manage_scheduler = st.session_state.schedulers[manage_pet]
    
    if manage_scheduler.get_tasks():
        st.markdown("### Complete, Edit, Schedule, or Delete Tasks")
        
        # Display all tasks
        tasks = manage_scheduler.get_tasks()
        
        for i, task in enumerate(tasks):
            task_col1, task_col2, task_col3, task_col4, task_col5 = st.columns([2, 1, 1, 1, 1])
            
            with task_col1:
                status_emoji = "✅" if task.is_completed else "⏳"
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪")
                time_info = f" @ {task.scheduled_time}" if task.scheduled_time else ""
                st.write(f"{status_emoji} {priority_emoji} **{task.title}** ({task.duration_minutes}m){time_info}")
            
            with task_col2:
                if not task.is_completed:
                    if st.button("✓ Complete", key=f"manage_complete_{i}"):
                        task.mark_completed()
                        st.success(f"✅ {task.title} marked complete!")
                        st.rerun()
                else:
                    if st.button("↩ Undo", key=f"manage_undo_{i}"):
                        task.mark_incomplete()
                        st.info(f"↩ {task.title} marked incomplete!")
                        st.rerun()
            
            with task_col3:
                if st.button("⏰ Schedule", key=f"manage_schedule_{i}"):
                    st.session_state[f"scheduling_task_{i}"] = True
                    st.rerun()
            
            with task_col4:
                if st.button("📝 Edit", key=f"manage_edit_{i}"):
                    st.session_state[f"editing_task_{i}"] = True
                    st.rerun()
            
            with task_col5:
                if st.button("🗑 Delete", key=f"manage_delete_{i}"):
                    manage_scheduler.remove_task(task)
                    st.success(f"🗑 {task.title} deleted!")
                    st.rerun()
            
            # Schedule time slot form
            if st.session_state.get(f"scheduling_task_{i}", False):
                with st.expander(f"⏰ Schedule: {task.title}", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        scheduled_time = st.time_input(
                            "Pick a start time",
                            value=datetime.strptime(task.scheduled_time, "%H:%M").time() if task.scheduled_time else datetime.strptime("09:00", "%H:%M").time(),
                            key=f"manage_time_input_{i}"
                        )
                        time_str = scheduled_time.strftime("%H:%M")
                    
                    with col2:
                        st.info(f"⏱️ Duration: {task.duration_minutes} min\n✅ End time: {(datetime.strptime(time_str, '%H:%M') + timedelta(minutes=task.duration_minutes)).strftime('%H:%M')}")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("💾 Confirm Schedule", key=f"manage_confirm_schedule_{i}"):
                            success = manage_scheduler.schedule_task_at_time(task, time_str)
                            if success:
                                st.session_state[f"scheduling_task_{i}"] = False
                                st.success(f"✅ {task.title} scheduled at {time_str}")
                                st.rerun()
                            else:
                                st.error(f"❌ Cannot schedule at {time_str} - conflict detected!")
                    
                    with col2:
                        pass
                    
                    with col3:
                        if st.button("❌ Cancel", key=f"manage_cancel_schedule_{i}"):
                            st.session_state[f"scheduling_task_{i}"] = False
                            st.rerun()
            
            # Edit form
            if st.session_state.get(f"editing_task_{i}", False):
                with st.expander(f"📝 Edit: {task.title}", expanded=True):
                    edit_col1, edit_col2 = st.columns(2)
                    
                    with edit_col1:
                        new_title = st.text_input("Task title", value=task.title, key=f"manage_edit_title_{i}")
                        new_duration = st.number_input("Duration (minutes)", value=task.duration_minutes, min_value=1, max_value=240, key=f"manage_edit_duration_{i}")
                        new_priority = st.selectbox("Priority", ["low", "medium", "high"], index=["low", "medium", "high"].index(task.priority), key=f"manage_edit_priority_{i}")
                    
                    with edit_col2:
                        new_category = st.text_input("Category", value=task.category, key=f"manage_edit_category_{i}")
                        new_frequency = st.selectbox("Frequency", ["one-time", "daily", "weekly", "monthly"], index=["one-time", "daily", "weekly", "monthly"].index(task.frequency), key=f"manage_edit_frequency_{i}")
                        new_description = st.text_area("Description", value=task.description or "", key=f"manage_edit_description_{i}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("💾 Save Changes", key=f"manage_save_edit_{i}"):
                            try:
                                # Check if new duration would exceed limit across ALL pets
                                total_all_pets = 0
                                for owned_pet in manage_scheduler.owner.pets:
                                    for pet_task in owned_pet.get_tasks():
                                        if pet_task != task:  # Don't count the old version of this task
                                            total_all_pets += pet_task.duration_minutes
                                
                                new_total = total_all_pets + new_duration
                                
                                if new_total > manage_scheduler.owner.available_minutes:
                                    st.error(f"❌ New duration would exceed limit! Total across all pets: {total_all_pets}m, New total: {new_total}m, Limit: {manage_scheduler.owner.available_minutes}m")
                                else:
                                    task.title = new_title
                                    task.duration_minutes = new_duration
                                    task.priority = new_priority
                                    task.category = new_category
                                    task.frequency = new_frequency
                                    task.description = new_description
                                    
                                    st.session_state[f"editing_task_{i}"] = False
                                    st.success(f"✅ {new_title} updated!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    
                    with col2:
                        if st.button("❌ Cancel", key=f"manage_cancel_edit_{i}"):
                            st.session_state[f"editing_task_{i}"] = False
                            st.rerun()
        
        # Summary
        st.markdown("---")
        st.markdown("### Task Summary")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("📋 Total", len(manage_scheduler.get_tasks()))
        with col2:
            st.metric("⏳ Pending", len(manage_scheduler.get_pending_tasks()))
        with col3:
            st.metric("✅ Completed", len(manage_scheduler.get_completed_tasks()))
        with col4:
            scheduled_count = len([t for t in manage_scheduler.get_tasks() if t.scheduled_time])
            st.metric("⏰ Scheduled", scheduled_count)
        with col5:
            completion_rate = (len(manage_scheduler.get_completed_tasks()) / len(manage_scheduler.get_tasks()) * 100) if manage_scheduler.get_tasks() else 0
            st.metric("📊 Completion", f"{completion_rate:.0f}%")
        
        # Show capacity - aggregate across ALL owner's pets
        st.markdown("---")
        st.markdown("### Time Capacity")
        
        # Calculate total duration across ALL owner's pets
        total_all_pets = 0
        for owned_pet in manage_scheduler.owner.pets:
            for pet_task in owned_pet.get_tasks():
                total_all_pets += pet_task.duration_minutes
        
        available = manage_scheduler.owner.available_minutes
        percentage = (total_all_pets / available * 100) if available > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⏱️ Total Scheduled (All Pets)", f"{total_all_pets} min")
        with col2:
            st.metric("📊 Available", f"{available} min")
        with col3:
            if total_all_pets > available:
                st.error(f"🚨 OVERBOOKED: {percentage:.0f}%")
            else:
                st.success(f"✅ Usage: {percentage:.0f}%")
    else:
        st.info(f"ℹ️ No tasks for {manage_pet} yet. Add a task to get started!")
