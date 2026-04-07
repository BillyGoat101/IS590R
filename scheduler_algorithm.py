import pandas as pd
import math
from ortools.sat.python import cp_model

def cal_distance_hrs(lat1, lon1, lat2, lon2):
    # Approximate equirectangular distance
    dy = (lat2 - lat1) * 69.0
    dx = (lon2 - lon1) * 53.0
    miles = math.sqrt(dx**2 + dy**2)
    return miles / 45.0  # Assumed 45 mph avg speed

def run_scheduler_algorithm(df_employees, df_tasks, df_projects, df_constraints):
    print("--- Lazenby Electric: MEP AI Scheduler ---")
    
    # 1. Parse Data
    if 'site_lat' not in df_tasks.columns:
        df_tasks = df_tasks.merge(df_projects, on='project_id', how='left')
        
    # Replace any NaNs with string 'Unknown' to avoid PyArrow serialization panic later
    df_tasks = df_tasks.fillna('Unknown')
        
    employees = df_employees.to_dict('records')
    tasks = df_tasks.to_dict('records')
    
    # 2. Parse Constraints 
    # Create flags for each rule based on substrings in df_constraints
    rule_trade_match = False
    rule_journeyman_presence = False
    rule_apprentice_ratio = False
    rule_no_double_book = False
    rule_travel_time = False
    
    # Check what constraints are provided in the table
    for _, row in df_constraints.iterrows():
        desc = str(row['logic_desc']).lower()
        if "trade must match" in desc:
            rule_trade_match = True
        if "at least one journeyman present" in desc:
            rule_journeyman_presence = True
        if "apprentice to journeyman" in desc:
            rule_apprentice_ratio = True
        if "double-booked" in desc:
            rule_no_double_book = True
        if "travel time" in desc:
            rule_travel_time = True
            
    print("\n[Constraint Engine] Active Rules:")
    print(f" -> Trade Match: {rule_trade_match}")
    print(f" -> Journeyman Presence: {rule_journeyman_presence}")
    print(f" -> Apprentice Ratio: {rule_apprentice_ratio}")
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

    # C4: Max ratio of Apprentice to Journeyman on any task is 1:1
    if rule_apprentice_ratio:
        for t in tasks:
            t_id = t['task_id']
            for d in range(DAYS):
                journeymen = sum(x[(emp['employee_id'], t_id, d)] for emp in employees if emp.get('skill_level') == 'Journeyman')
                apprentices = sum(x[(emp['employee_id'], t_id, d)] for emp in employees if emp.get('skill_level') == 'Apprentice')
                model.Add(apprentices <= journeymen)

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

    # ==========================
    # OBJECTIVE
    # ==========================
    # Maximize total duration assigned across the 5 days, but heavily strictly penalize
    # every unique assignment with the task's setup/teardown cost.
    # This prevents the solver from shattering tasks into 1-hour fragments.
    duration_expr = sum(task_durs[(emp['employee_id'], t['task_id'], d)] 
                        for emp in employees for t in tasks for d in range(DAYS))
    penalty_expr = sum(x[(emp['employee_id'], t['task_id'], d)] * int(t.get('setup_teardown_mins', 30))
                       for emp in employees for t in tasks for d in range(DAYS))
    
    model.Maximize(duration_expr - penalty_expr)

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
                            "employee_name": str(emp.get('full_name', e_id)),
                            "trade": str(emp.get('trade', 'Unknown')),
                            "task_id": str(t_id),
                            "task_desc": task_desc,
                            "project_name": proj_name,
                            "job_site": proj_name, 
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
            df_schedule['employee_name'] = df_schedule['employee_name'].astype(str)
            df_schedule['trade'] = df_schedule['trade'].astype(str)
            df_schedule['task_id'] = df_schedule['task_id'].astype(str)
            df_schedule['task_desc'] = df_schedule['task_desc'].astype(str)
            df_schedule['project_name'] = df_schedule['project_name'].astype(str)
            df_schedule['job_site'] = df_schedule['job_site'].astype(str)
            df_schedule['day_index'] = df_schedule['day_index'].astype(int)
            df_schedule['day_name'] = df_schedule['day_name'].astype(str)
            df_schedule['start_time'] = df_schedule['start_time'].astype(str)
            df_schedule['end_time'] = df_schedule['end_time'].astype(str)
            df_schedule['duration_hours'] = df_schedule['duration_hours'].astype(float)
            df_schedule['setup_teardown_mins_incurred'] = df_schedule['setup_teardown_mins_incurred'].astype(int)
            df_schedule['actual_start_time'] = pd.to_datetime(df_schedule['actual_start_time'])
            df_schedule['actual_end_time'] = pd.to_datetime(df_schedule['actual_end_time'])
            
            print(f"Generated {len(df_schedule)} assignment records!")
            # Brief visual print out
            for d in range(DAYS):
                df_day = df_schedule[df_schedule['day_index'] == d].sort_values(by=['employee_name', 'start_time'])
                if not df_day.empty:
                    print(f"--- {day_names[d]} ---")
                    for _, row in df_day.iterrows():
                        print(f"  [{row['trade']}] {row['employee_name']} from {row['start_time']} to {row['end_time']} -> {row['task_desc']} @ {row['job_site']}")
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
        
        # Execute the AI Scheduler
        result_df = run_scheduler_algorithm(df_employees, df_tasks, df_projects, df_constraints)
        
        if not result_df.empty:
            print("Writing generated schedule back to Lakehouse as Delta Table 'Schedule_Output'...")
            
            # [CRITICAL FIX] Disable Arrow execution locally to bypass the 'BufferHolder by size -8' bug in Fabric/PyArrow
            # This happens exactly when data types like float NaN get combined into String columns!
            original_arrow_setting = spark.conf.get("spark.sql.execution.arrow.pyspark.enabled", "true")
            spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", "false")
            
            spark_schedule_df = spark.createDataFrame(result_df)
            spark_schedule_df.write.mode("overwrite").format("delta").saveAsTable("Schedule_Output")
            
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
