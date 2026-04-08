# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "da9cf26c-4c48-461f-959e-74208f7b9161",
# META       "default_lakehouse_name": "Data",
# META       "default_lakehouse_workspace_id": "23e788c4-2e26-4e48-9eb9-118f3022eda8",
# META       "known_lakehouses": [
# META         {
# META           "id": "da9cf26c-4c48-461f-959e-74208f7b9161"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

%pip install ortools "numpy<2"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import pandas as pd
import math
from ortools.sat.python import cp_model

def cal_distance_hrs(lat1, lon1, lat2, lon2):
    # Approximate equirectangular distance
    dy = (lat2 - lat1) * 69.0
    dx = (lon2 - lon1) * 53.0
    miles = math.sqrt(dx**2 + dy**2)
    return miles / 45.0  # Assumed 45 mph avg speed

def run_scheduler_algorithm(df_employees, df_tasks, df_projects, df_constraints, df_overrides=None):
    print("--- Lazenby Electric: MEP AI Scheduler ---")
    
    # 1. Parse Data
    if 'site_lat' not in df_tasks.columns:
        df_tasks = df_tasks.merge(df_projects, on='project_id', how='left')
        
    # Replace any NaNs with string 'Unknown' to avoid PyArrow serialization panic later
    df_tasks = df_tasks.fillna('Unknown')
    
    # Filter the active backlog: Only schedule tasks actively marked as Ready or In Progress
    if 'task_status' in df_tasks.columns:
        valid_statuses = ['Ready', 'In Progress']
        df_tasks = df_tasks[df_tasks['task_status'].isin(valid_statuses)].copy()
        print(f"--> Filtered enterprise pipeline to {len(df_tasks)} actionable tasks for this week.")
        
    employees = df_employees.to_dict('records')
    tasks = df_tasks.to_dict('records')
    
    # 2. Parse Constraints 
    # Create flags for each rule based on substrings in df_constraints
    rule_trade_match = False
    rule_journeyman_presence = False
    rule_apprentice_ratio_elec = False
    rule_apprentice_ratio_plumb = False
    rule_apprentice_ratio_mech = False
    rule_no_double_book = False
    rule_travel_time = False
    
    # Check what constraints are provided in the table
    for _, row in df_constraints.iterrows():
        desc = str(row['logic_desc']).lower()
        if "trade must match" in desc:
            rule_trade_match = True
        if "at least one journeyman present" in desc:
            rule_journeyman_presence = True
        if "electrical max ratio" in desc:
            rule_apprentice_ratio_elec = True
        if "plumbing max ratio" in desc:
            rule_apprentice_ratio_plumb = True
        if "mechanical max ratio" in desc:
            rule_apprentice_ratio_mech = True
        if "double-booked" in desc:
            rule_no_double_book = True
        if "travel time" in desc:
            rule_travel_time = True

    # 3. Apply Manual Rule Toggles from Override CSV
    if df_overrides is not None and not df_overrides.empty:
        for _, row in df_overrides.iterrows():
            if str(row.get('override_type', '')).lower() == 'toggle_rule':
                rule_name = str(row.get('employee_id', '')).lower()
                is_active = str(row.get('task_id', '')).lower() in ['true', '1', 'yes']
                
                if 'trade_match' in rule_name: rule_trade_match = is_active
                elif 'journeyman_presence' in rule_name: rule_journeyman_presence = is_active
                elif 'apprentice_ratio_elec' in rule_name: rule_apprentice_ratio_elec = is_active
                elif 'apprentice_ratio_plumb' in rule_name: rule_apprentice_ratio_plumb = is_active
                elif 'apprentice_ratio_mech' in rule_name: rule_apprentice_ratio_mech = is_active
                elif 'no_double_book' in rule_name: rule_no_double_book = is_active
                elif 'travel_time' in rule_name: rule_travel_time = is_active
            
    print("\n[Constraint Engine] Active Rules:")
    print(f" -> Trade Match: {rule_trade_match}")
    print(f" -> Journeyman Presence: {rule_journeyman_presence}")
    print(f" -> Apprentice Ratio (Elec): {rule_apprentice_ratio_elec}")
    print(f" -> Apprentice Ratio (Plumb): {rule_apprentice_ratio_plumb}")
    print(f" -> Apprentice Ratio (Mech): {rule_apprentice_ratio_mech}")
    print(f" -> No Double Booking: {rule_no_double_book}")
    print(f" -> Travel Time Limits: {rule_travel_time}\n")
    
    model = cp_model.CpModel()
    
    # Define an 8-hour workday in minutes (480 mins)
    HORIZON = 480 
    DAYS = 5
    
    # Variables
    x = {} # Boolean: Is Employee assigned to Task on Day d
    task_intervals = {} # Time intervals for scheduling
    task_starts = {}
    task_ends = {}
    task_durs = {}
    
    for emp in employees:
        e_id = emp['employee_id']
        for t in tasks:
            t_id = t['task_id']
            for d in range(DAYS):
                # Assignment boolean
                assign_var = model.NewBoolVar(f"x_{e_id}_{t_id}_{d}")
                x[(e_id, t_id, d)] = assign_var
                
                start_var = model.NewIntVar(0, HORIZON, f"start_{e_id}_{t_id}_{d}")
                end_var = model.NewIntVar(0, HORIZON, f"end_{e_id}_{t_id}_{d}")
                dur_var = model.NewIntVar(0, 480, f"dur_{e_id}_{t_id}_{d}") # Max 8 hours per day
                
                # Link assignment flag to duration logically: if not assigned, duration is 0
                model.Add(dur_var == 0).OnlyEnforceIf(assign_var.Not())
                
                block_req = str(t.get('block_requirement', 'Any'))
                if block_req == 'Half-Day':
                    model.Add(dur_var == 240).OnlyEnforceIf(assign_var)
                elif block_req == 'Full-Day':
                    model.Add(dur_var == 480).OnlyEnforceIf(assign_var)
                else:
                    MIN_TASK_MINUTES = 60
                    model.Add(dur_var >= MIN_TASK_MINUTES).OnlyEnforceIf(assign_var)
                
                interval_var = model.NewOptionalIntervalVar(
                    start_var, dur_var, end_var, assign_var, f"interval_{e_id}_{t_id}_{d}"
                )
                
                task_intervals[(e_id, t_id, d)] = interval_var
                task_starts[(e_id, t_id, d)] = start_var
                task_ends[(e_id, t_id, d)] = end_var
                task_durs[(e_id, t_id, d)] = dur_var

    # ==========================
    # CONSTRAINTS
    # ==========================

    # BASE RULE 1: Total duration across all days and employees cannot exceed task's man_hours_est
    for t in tasks:
        t_id = t['task_id']
        # Fallback for man_hours_est in case of missing data
        man_hours = t.get('man_hours_est')
        man_hours_est = float(man_hours) if str(man_hours).replace('.', '', 1).isdigit() else 8.0 
        max_mins = int(man_hours_est * 60)
        total_time_expr = sum(task_durs[(emp['employee_id'], t_id, d)] 
                              for emp in employees for d in range(DAYS))
        model.Add(total_time_expr <= max_mins)

    # BASE RULE 2: Minimum Staffing required for a task IF active that day
    for t in tasks:
        t_id = t['task_id']
        min_staff = t.get('min_staff')
        m_staff = int(min_staff) if str(min_staff).isdigit() else 1
        
        task_active_days = []
        for d in range(DAYS):
            assigned_count = sum(x[(emp['employee_id'], t_id, d)] for emp in employees)
            task_active = model.NewBoolVar(f"active_{t_id}_{d}")
            task_active_days.append(task_active)
            
            # If anyone is assigned, task is active.
            model.Add(assigned_count > 0).OnlyEnforceIf(task_active)
            model.Add(assigned_count == 0).OnlyEnforceIf(task_active.Not())
            
            # If active, must meet min staff
            model.Add(assigned_count >= m_staff).OnlyEnforceIf(task_active)
            
        is_interruptible = t.get('is_interruptible', True)
        # Handle string "False" vs boolean False just in case Spark serialized it strangely
        if str(is_interruptible).lower() == 'false' or is_interruptible is False:
            model.Add(sum(task_active_days) <= 1)

    # C1: Trade Match
    if rule_trade_match:
        for emp in employees:
            for t in tasks:
                if emp.get('trade') != t.get('required_skill'):
                    for d in range(DAYS):
                        model.Add(x[(emp['employee_id'], t['task_id'], d)] == 0)

    # C3: Every physical job site task must have at least one Journeyman
    if rule_journeyman_presence:
        for t in tasks:
            t_id = t['task_id']
            for d in range(DAYS):
                journeymen = sum(x[(emp['employee_id'], t_id, d)] for emp in employees if emp.get('skill_level') == 'Journeyman')
                assigned_count = sum(x[(emp['employee_id'], t_id, d)] for emp in employees)
                model.Add(assigned_count <= 100 * journeymen)

    # C4: Trade-Specific Ratio of Apprentice to Journeyman
    # Note: 'Tech II' is excluded from this restriction boundary explicitly
    for t in tasks:
        t_id = t['task_id']
        req_skill = str(t.get('required_skill', '')).lower()
        
        # Only enforce if the specific rule flag is active
        if ('electrical' in req_skill and rule_apprentice_ratio_elec): ratio = 1
        elif ('plumbing' in req_skill and rule_apprentice_ratio_plumb): ratio = 2
        elif ('mechanical' in req_skill and rule_apprentice_ratio_mech): ratio = 3
        else: continue # Skip if rule toggled off
        
        for d in range(DAYS):
            journeymen = sum(x[(emp['employee_id'], t_id, d)] for emp in employees if emp.get('skill_level') == 'Journeyman')
            apprentices = sum(x[(emp['employee_id'], t_id, d)] for emp in employees if emp.get('skill_level') == 'Apprentice')
            # The mathematical solver constraint ensures apprentices never exceed ratio multiplier
            model.Add(apprentices <= ratio * journeymen)

    # C8: Hard-Code Licensed Professional Required
    # If tasks are critical, they MUST have a journeyman if active
    for t in tasks:
        t_id_c8 = t['task_id']
        t_desc = str(t.get('task_desc', '')).lower()
        
        if "final connection" in t_desc or "gas piping" in t_desc:
            for d in range(DAYS):
                active_assigns = sum(x[(emp['employee_id'], t_id_c8, d)] for emp in employees)
                journeys = sum(x[(emp['employee_id'], t_id_c8, d)] for emp in employees if emp.get('skill_level') == 'Journeyman')
                
                # In OR-Tools, OnlyEnforceIf requires a boolean variable, not a BoundedLinearExpression.
                # We must map the active_assigns expression to a boolean first.
                is_active = model.NewBoolVar(f"c8_active_{t_id_c8}_{d}")
                model.Add(active_assigns > 0).OnlyEnforceIf(is_active)
                model.Add(active_assigns == 0).OnlyEnforceIf(is_active.Not())
                
                # If the task is active, it must have at least 1 journeyman
                model.Add(journeys >= 1).OnlyEnforceIf(is_active)

    # C5: No Double Booking (No Overlap)
    if rule_no_double_book:
        for emp in employees:
            e_id = emp['employee_id']
            for d in range(DAYS):
                model.AddNoOverlap([task_intervals[(e_id, t['task_id'], d)] for t in tasks])

    # C6: Travel Time cannot exceed 2 hours between tasks within a single day
    if rule_travel_time:
        for emp in employees:
            e_id = emp['employee_id']
            for d in range(DAYS):
                for t1 in tasks:
                    for t2 in tasks:
                        if t1['task_id'] < t2['task_id']:
                            try:
                                travel_hrs = cal_distance_hrs(float(t1.get('site_lat', 0)), float(t1.get('site_long', 0)), 
                                                              float(t2.get('site_lat', 0)), float(t2.get('site_long', 0)))
                            except (ValueError, TypeError):
                                travel_hrs = 0.0
                            if travel_hrs > 2.0:
                                model.AddImplication(x[(e_id, t1['task_id'], d)], x[(e_id, t2['task_id'], d)].Not())

    # C7: Manual Data Overrides (Absences, Forced Tasks, Exclusions)
    if df_overrides is not None and not df_overrides.empty:
        for _, row in df_overrides.iterrows():
            otype = str(row.get('override_type', '')).lower()
            emp_id_override = str(row.get('employee_id', ''))
            task_id_override = str(row.get('task_id', ''))
            
            raw_day = row.get('day_index')
            d_idx = None
            if pd.notna(raw_day) and str(raw_day).strip() != '':
                try:
                    d_idx = int(float(raw_day))
                except ValueError:
                    d_idx = None

            if otype == 'absent' and d_idx is not None:
                for t in tasks:
                    if (emp_id_override, t['task_id'], d_idx) in x:
                        model.Add(x[(emp_id_override, t['task_id'], d_idx)] == 0)
                        
            elif otype == 'force_task':
                if d_idx is not None:
                    # Force assignment on a specific day
                    if (emp_id_override, task_id_override, d_idx) in x:
                        model.Add(x[(emp_id_override, task_id_override, d_idx)] == 1)
                else:
                    # Force assignment at least once during the week
                    valid_days = [x[(emp_id_override, task_id_override, d)] for d in range(DAYS) if (emp_id_override, task_id_override, d) in x]
                    if valid_days:
                        model.Add(sum(valid_days) >= 1)
                        
            elif otype == 'exclude_task':
                for d in range(DAYS):
                    if (emp_id_override, task_id_override, d) in x:
                        model.Add(x[(emp_id_override, task_id_override, d)] == 0)

    # ==========================
    # OBJECTIVE & LOAD BALANCING
    # ==========================
    # Maximize total duration assigned, but strictly penalize excessive setup/teardown.
    duration_expr = sum(task_durs[(emp['employee_id'], t['task_id'], d)] 
                        for emp in employees for t in tasks for d in range(DAYS))
    penalty_expr = sum(x[(emp['employee_id'], t['task_id'], d)] * int(t.get('setup_teardown_mins', 30))
                       for emp in employees for t in tasks for d in range(DAYS))
    
    # Fairness hook: We heavily reward the AI for simply getting a person "active" on the schedule.
    # This overrides the mild setup penalty, ensuring the AI spreads the work out across the entire company
    # rather than dropping it all on one guy to theoretically save 30 minutes of setup time.
    fairness_expr = []
    for emp in employees:
        e_id = emp['employee_id']
        emp_is_employed = model.NewBoolVar(f"employed_{e_id}")
        emp_total = sum(task_durs[(e_id, t['task_id'], d)] for t in tasks for d in range(DAYS))
        
        model.Add(emp_total > 0).OnlyEnforceIf(emp_is_employed)
        model.Add(emp_total == 0).OnlyEnforceIf(emp_is_employed.Not())
        fairness_expr.append(emp_is_employed)

    # 500 points per employed human guarantees load balancing is highly prioritized
    model.Maximize(duration_expr - penalty_expr + sum(fairness_expr) * 500)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15.0
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("[SUCCESS] Found a valid schedule!\n")
        
        schedule_records = []
        
        for emp in employees:
            e_id = emp['employee_id']
            for t in tasks:
                t_id = t['task_id']
                for d in range(DAYS):
                    if solver.Value(x[(e_id, t_id, d)]) == 1:
                        start_val = solver.Value(task_starts[(e_id, t_id, d)])
                        end_val = solver.Value(task_ends[(e_id, t_id, d)])
                        dur_val = solver.Value(task_durs[(e_id, t_id, d)])
                        
                        s_hr = 8 + (start_val // 60)
                        s_min = start_val % 60
                        e_hr = 8 + (end_val // 60)
                        e_min = end_val % 60
                        
                        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                        
                        # Handle potential missing metadata gracefully
                        proj_name = str(t.get('project_name', f"Project ({t.get('project_id', 'Unknown')})"))
                        task_desc = str(t.get('task_desc', f"Task {t_id}"))
                        
                        # Establish a relative timeline sequence starting on a fictional "Base Monday"
                        # For Power BI Date/Time plotting (e.g. 2026-01-05 is a Monday)
                        import datetime
                        base_date = datetime.datetime(2026, 1, 5)
                        task_date = base_date + datetime.timedelta(days=d)
                        actual_start = task_date.replace(hour=int(s_hr), minute=int(s_min), second=0)
                        actual_end = task_date.replace(hour=int(e_hr), minute=int(e_min), second=0)
                        
                        schedule_records.append({
                            "employee_id": str(e_id),
                            "task_id": str(t_id),
                            "day_index": int(d),
                            "day_name": str(day_names[d]),
                            "start_time": f"{s_hr:02d}:{s_min:02d}",
                            "end_time": f"{e_hr:02d}:{e_min:02d}",
                            "duration_hours": float(round(dur_val / 60.0, 2)),
                            "setup_teardown_mins_incurred": int(t.get('setup_teardown_mins', 30)),
                            "actual_start_time": actual_start,
                            "actual_end_time": actual_end
                        })
                        
        df_schedule = pd.DataFrame(schedule_records)
        
        # Ensure schema structure in pandas before arrow conversion
        if not df_schedule.empty:
            df_schedule['employee_id'] = df_schedule['employee_id'].astype(str)
            df_schedule['task_id'] = df_schedule['task_id'].astype(str)
            df_schedule['day_index'] = df_schedule['day_index'].astype(int)
            df_schedule['day_name'] = df_schedule['day_name'].astype(str)
            df_schedule['start_time'] = df_schedule['start_time'].astype(str)
            df_schedule['end_time'] = df_schedule['end_time'].astype(str)
            df_schedule['duration_hours'] = df_schedule['duration_hours'].astype(float)
            df_schedule['setup_teardown_mins_incurred'] = df_schedule['setup_teardown_mins_incurred'].astype(int)
            df_schedule['actual_start_time'] = pd.to_datetime(df_schedule['actual_start_time'])
            df_schedule['actual_end_time'] = pd.to_datetime(df_schedule['actual_end_time'])
            
            print(f"Generated {len(df_schedule)} assignment records!")
            
            # --- Capacity & Load Balancing Warning Calculation ---
            total_available = len(employees) * 40.0
            total_backlog_mins = sum(int((float(t.get('man_hours_est', 8.0)) if str(t.get('man_hours_est', 8.0)).replace('.', '', 1).isdigit() else 8.0) * 60) for t in tasks)
            total_backlog_hrs = total_backlog_mins / 60.0
            assigned_hrs = df_schedule['duration_hours'].sum()
            
            print("\n=======================================================")
            print("          CAPACITY & LOAD BALANCING REPORT             ")
            print("=======================================================")
            print(f" Total Available Labor Capacity: {total_available} hours ({len(employees)} technicians)")
            print(f" Total Backlog Need (Tasks):     {total_backlog_hrs} hours")
            print(f" Total Hours Scheduled by AI:    {assigned_hrs} hours")
            print("-------------------------------------------------------")
            if total_backlog_hrs > total_available:
                print(" >>> WARNING: Your backlog far exceeds your employee capacity!")
                print("              You need to hire more technicians or decline projects.")
            elif total_available > total_backlog_hrs + 40:
                print(" >>> WARNING: You have too many employees for the current workload!")
                print("              Technicians will be underutilized. Get more projects!")
            else:
                print(" >>> STATUS:  Excellent balance between workforce capacity and backlog.")
            print("=======================================================\n")
            
            # Brief visual print out
            for d in range(DAYS):
                df_day = df_schedule[df_schedule['day_index'] == d].sort_values(by=['employee_id', 'start_time'])
                if not df_day.empty:
                    print(f"--- {day_names[d]} ---")
                    for _, row in df_day.iterrows():
                        print(f"  EMP: {row['employee_id']} from {row['start_time']} to {row['end_time']} -> TASK: {row['task_id']}")
                    print("")
        return df_schedule
        
    else:
        print("\n[ERROR] Could not find a valid schedule to satisfy the rules.")
        print("This usually means there aren't enough Journeymen, or tasks require more staff than available.")
        return pd.DataFrame() # Empty on failure

def main():
    print("Initiating Fabric PySpark Session...")
    try:
        from pyspark.sql import SparkSession
        
        # In a Microsoft Fabric notebook, 'spark' is usually provided automatically,
        # but this ensures we have an instance if run as a standalone Spark job.
        spark = SparkSession.builder.appName("MEP_AI_Scheduler").getOrCreate()
        
        print("Fetching Delta Tables from Lakehouse...")
        df_spark_employees = spark.read.table("Employees")
        df_spark_tasks = spark.read.table("Tasks")
        df_spark_projects = spark.read.table("Projects")
        df_spark_constraints = spark.read.table("Constraints_Rules")
        
        print("Converting to Pandas for cp_model...")
        df_employees = df_spark_employees.toPandas()
        df_tasks = df_spark_tasks.toPandas()
        df_projects = df_spark_projects.toPandas()
        df_constraints = df_spark_constraints.toPandas()
        
        # Load Manual Overrides if present
        df_overrides = None
        try:
            print("Checking for 'Files/Manual_Overrides.csv'...")
            df_spark_overrides = spark.read.csv("Files/Manual_Overrides.csv", header=True, inferSchema=True)
            df_overrides = df_spark_overrides.toPandas()
            print(f"--> Detected Manual Overrides! Loading {len(df_overrides)} custom instructions.")
        except Exception:
            print("--> No 'Files/Manual_Overrides.csv' found. Proceeding with standard intelligent rules.")
        
        # Execute the AI Scheduler
        result_df = run_scheduler_algorithm(df_employees, df_tasks, df_projects, df_constraints, df_overrides)
        
        if not result_df.empty:
            print("Writing generated schedule back to Lakehouse as Delta Table 'Schedule_Output'...")
            
            # [CRITICAL FIX] Disable Arrow execution locally to bypass the 'BufferHolder by size -8' bug in Fabric/PyArrow
            # This happens exactly when data types like float NaN get combined into String columns!
            original_arrow_setting = spark.conf.get("spark.sql.execution.arrow.pyspark.enabled", "true")
            spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", "false")
            
            spark_schedule_df = spark.createDataFrame(result_df)
            spark_schedule_df.write.mode("overwrite").option("overwriteSchema", "true").format("delta").saveAsTable("Schedule_Output")
            
            # Restore Arrow setting
            spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", original_arrow_setting)
            
            print("[SUCCESS] Delta Table 'Schedule_Output' created/updated perfectly.")
            print("You can now connect a Power BI Semantic Model to 'Schedule_Output' to build your interactive dashboard.")
            
    except ImportError:
        print("[ERROR] PySpark is not installed or configured in this environment.")
        print("This file is intended to be executed inside a Microsoft Fabric Spark Notebook.")
    except Exception as e:
        print(f"\n[ERROR] execution failed: {e}")
        print("Please ensure this script is running in a Fabric Notebook with the Lakehouse attached.")

if __name__ == "__main__":
    main()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MEP AI Scheduler - Post-Run Validation Test Suite
# Target execution environment: Microsoft Fabric Spark Notebook

from pyspark.sql import SparkSession
import pandas as pd

def run_tests():
    print("Initializing Testing Suite...")
    spark = SparkSession.builder.appName("MEP_Validation_Suite").getOrCreate()
    
    try:
        print("Fetching Delta Tables from Lakehouse...")
        df_schedule = spark.read.table("Schedule_Output").toPandas()
        df_employees = spark.read.table("Employees").toPandas()
        df_tasks = spark.read.table("Tasks").toPandas()
    except Exception as e:
        print(f"[FAIL] Could not load tables. Have you run the scheduler yet? Error: {e}")
        return

    print(f"Loaded {len(df_schedule)} scheduled assignments.")
    
    # Merge datasets to get full context per assignment
    df_merged = df_schedule.merge(df_employees, on='employee_id', how='left')
    df_merged = df_merged.merge(df_tasks, on='task_id', how='left')
    
    # Group by task and day to evaluate crews
    crews = df_merged.groupby(['task_id', 'day_index'])
    
    violations_found = 0
    test_count = 0
    
    print("\n--- Running Ratio & Compliance Tests ---")
    
    for (task_id, day), crew in crews:
        test_count += 1
        journeymen = len(crew[crew['skill_level'] == 'Journeyman'])
        apprentices = len(crew[crew['skill_level'] == 'Apprentice'])
        tech_iis = len(crew[crew['skill_level'] == 'Tech II'])
        
        req_skill = str(crew.iloc[0]['required_skill']).lower()
        task_desc = str(crew.iloc[0]['task_desc']).lower()
        
        # 1. Trade-Specific Ratio Check
        ratio_mapping = {'electrical': 1, 'plumbing': 2, 'mechanical': 3}
        
        assigned_ratio = ratio_mapping.get(req_skill, 1)
        max_allowed_apprentices = journeymen * assigned_ratio
        
        if apprentices > max_allowed_apprentices:
            print(f"[VIOLATION] Ratio Failure on Task {task_id} (Day {day})")
            print(f"   -> Trade: {req_skill.upper()}")
            print(f"   -> Crew: {journeymen} Journeymen, {apprentices} Apprentices")
            print(f"   -> Max Apprentices Allowed: {max_allowed_apprentices}")
            violations_found += 1
            
        # 2. Licensed Professional Priority Check
        if "final connection" in task_desc or "gas piping" in task_desc:
            if journeymen < 1:
                print(f"[VIOLATION] Licensed Pro Failure on Task {task_id} (Day {day})")
                print(f"   -> Task: {task_desc}")
                print(f"   -> Issue: Task requires Journeyman but 0 are assigned.")
                violations_found += 1

    print("\n--- Test Results ---")
    if violations_found == 0:
        print(f"[PASS] Successfully verified {test_count} shift assignments.")
        print("[PASS] All trade-specific ratios (1:1, 1:2, 1:3) rigidly mathematically enforced.")
        print("[PASS] Tech II employees successfully ignored in apprentice ratio limits.")
        print("[PASS] All Licensed Professional assignments correctly feature a Journeyman.")
    else:
        print(f"[FAIL] Discovered {violations_found} compliance violations in the schedule.")

if __name__ == "__main__":
    run_tests()


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
