# MEP AI Scheduler - Synthetic Data Generation
# Target execution environment: Microsoft Fabric Spark Notebook

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType
import random
import uuid

# Initialize Spark Session (In Fabric notebooks, 'spark' is usually provided by default, 
# but it's good practice to getOrCreate)
spark = SparkSession.builder.appName("MEP_AI_Scheduler_Data_Gen").getOrCreate()

# ==========================================
# 1. Schema Definitions & Data Generation
# ==========================================

# Trades & Skills
TRADES = ['Mechanical', 'Electrical', 'Plumbing']
SKILL_LEVELS = ['Journeyman', 'Apprentice', 'Tech II']

# Utah County Coordinates (Provo, Orem, Spanish Fork approximate bounding box)
# Provo: ~40.2338, -111.6585
# Orem: ~40.2969, -111.6946
# Spanish Fork: ~40.1150, -111.6549
LAT_MIN, LAT_MAX = 40.1100, 40.3000
LONG_MIN, LONG_MAX = -111.7500, -111.6000

# Generate Employees (20 technicians)
employees_data = []
for i in range(1, 21):
    emp_id = f"EMP{i:03d}"
    full_name = f"Tech_{i}"
    trade = random.choice(TRADES)
    skill_level = random.choice(SKILL_LEVELS)
    
    # Generate home locations within Utah County
    home_lat = round(random.uniform(LAT_MIN, LAT_MAX), 5)
    home_long = round(random.uniform(LONG_MIN, LONG_MAX), 5)
    
    # Normally distributed hourly rate around $40/hr
    hourly_rate = round(random.normalvariate(40.0, 5.0), 2)
    # Ensure minimum wage bounds to be realistic
    hourly_rate = max(15.0, min(hourly_rate, 75.0))
    
    employees_data.append((emp_id, full_name, trade, skill_level, home_lat, home_long, hourly_rate))

employees_schema = StructType([
    StructField("employee_id", StringType(), False),
    StructField("full_name", StringType(), False),
    StructField("trade", StringType(), False),
    StructField("skill_level", StringType(), False),
    StructField("home_lat", DoubleType(), False),
    StructField("home_long", DoubleType(), False),
    StructField("hourly_rate", DoubleType(), False)
])
df_employees = spark.createDataFrame(employees_data, schema=employees_schema)

# Generate Projects (5-10 active projects)
num_projects = random.randint(5, 10)
projects_data = []
for i in range(1, num_projects + 1):
    proj_id = f"PRJ{i:03d}"
    proj_name = f"Utah_County_Site_{i}"
    
    site_lat = round(random.uniform(LAT_MIN, LAT_MAX), 5)
    site_long = round(random.uniform(LONG_MIN, LONG_MAX), 5)
    
    total_budget = round(random.uniform(10000.0, 500000.0), 2)
    
    projects_data.append((proj_id, proj_name, site_lat, site_long, total_budget))

projects_schema = StructType([
    StructField("project_id", StringType(), False),
    StructField("project_name", StringType(), False),
    StructField("site_lat", DoubleType(), False),
    StructField("site_long", DoubleType(), False),
    StructField("total_budget", DoubleType(), False)
])
df_projects = spark.createDataFrame(projects_data, schema=projects_schema)

# Generate Tasks
tasks_data = []
for proj in projects_data:
    proj_id = proj[0]
    num_tasks = random.randint(3, 8)
    for _ in range(num_tasks):
        task_id = str(uuid.uuid4())[:8]
        req_skill = random.choice(TRADES)
        man_hours_est = round(random.uniform(10.0, 200.0), 1)
        min_staff = random.randint(1, 4)
        
        tasks_data.append((task_id, proj_id, req_skill, man_hours_est, min_staff))

tasks_schema = StructType([
    StructField("task_id", StringType(), False),
    StructField("project_id", StringType(), False),
    StructField("required_skill", StringType(), False),
    StructField("man_hours_est", DoubleType(), False),
    StructField("min_staff", IntegerType(), False)
])
df_tasks = spark.createDataFrame(tasks_data, schema=tasks_schema)

# Define Constraints_Rules
constraints_data = [
    ("Hard", "Max ratio of Apprentice to Journeyman on any task or trade operation is 1:1"),
    ("Hard", "Every physical job site task must have at least one Journeyman present"),
    ("Hard", "Technicians cannot be double-booked on overlapping schedules"),
    ("Hard", "Technician assigned trade must match the task required skill trade"),
    ("Hard", "Travel time between consecutive tasks on the same day cannot exceed 2 hours")
]

constraints_schema = StructType([
    StructField("rule_type", StringType(), False),
    StructField("logic_desc", StringType(), False)
])
df_constraints = spark.createDataFrame(constraints_data, schema=constraints_schema)

# ==========================================
# 2. Output Requirements: Save as Delta Tables
# ==========================================

# Note: In a Microsoft Fabric Lakehouse environment, you can save directly to Delta tables
# Assuming the default lakehouse is already attached to this notebook.

print("Saving Tables to Delta Lake...")

# Depending on your environment configuration, you might write to a specific location or database.
# Here we're saving them as managed tables in the default attached Lakehouse.

try:
    df_employees.write.format("delta").mode("overwrite").saveAsTable("Employees")
    df_projects.write.format("delta").mode("overwrite").saveAsTable("Projects")
    df_tasks.write.format("delta").mode("overwrite").saveAsTable("Tasks")
    df_constraints.write.format("delta").mode("overwrite").saveAsTable("Constraints_Rules")
    print("Successfully saved all Delta tables.")
except Exception as e:
    print("Encountered an error while saving to Delta tables. Ensure a Lakehouse is attached.")
    print(f"Error: {str(e)}")

# Display snippets to confirm structure natively in notebook
df_employees.show(5)
df_projects.show(5)
df_tasks.show(5)
df_constraints.show(5, truncate=False)
