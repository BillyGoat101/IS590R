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
# META         },
# META         {
# META           "id": "1586ed29-f85b-413a-90ff-3f8970271a05"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# MEP AI Scheduler - Synthetic Data Generation
# Target execution environment: Microsoft Fabric Spark Notebook

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, BooleanType
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
# A collection of 100 blue-collar Utah names
first_names = [
    "Bridger", "Colter", "Hyrum", "Porter", "Dalton", "Wyatt", "Gage", "Stetson", "Corbin", "Thayne",
    "Blaine", "Garrett", "Weston", "Tanner", "Clint", "Travis", "Rusty", "Cody", "Bo", "Kaden",
    "Skyler", "Zane", "Waylon", "Beau", "Tucker", "Colt", "Remington", "Hunter", "Gunner", "Ryker",
    "Oakley", "Bronson", "Dallin", "Jared", "Sterling", "Sawyer", "Clay", "Cade", "Wade", "Jesse",
    "Jed", "Ephraim", "Zeke", "Hank", "Brooks", "Cooper", "Lane", "Trace", "Cash", "Tyson",
    "Chance", "Riley", "Austin", "Brent", "Casey", "Dallas", "Dustin", "Shane", "Lonnie", "Vernal",
    "Kurt", "Devin", "Brock", "Grant", "Klayton", "Marshall", "Quinton", "Roper", "Canyon", "Ridge",
    "Flint", "Stone", "Diesel", "Wilder", "Stockton", "Karl", "Anson", "Merrill", "Orrin", "Newell",
    "Boyd", "Lyle", "Duane", "Keith", "Glen", "Dale", "Wayne", "Floyd", "Roy", "Dean",
    "Gus", "Mack", "Rex", "Buddy", "Art", "Cliff", "Burt", "Judd", "Blaze", "Tyrell"
]
last_names = [
    "Andersen", "Barney", "Beckstead", "Bennion", "Bingham", "Blackburn", "Bradshaw", "Brown", "Call", "Cannon",
    "Christensen", "Clark", "Clawson", "Cook", "Curtis", "Dalton", "Davies", "Day", "Draper", "Dutton",
    "Eckman", "Egbert", "Erickson", "Evans", "Farnsworth", "Finlinson", "Gardner", "Gentry", "Giles", "Goodrich",
    "Greenhalgh", "Hansen", "Hatch", "Hendrickson", "Hinckley", "Holbrook", "Huntsman", "Ivie", "Jacobsen", "Jensen",
    "Jeppson", "Jorgensen", "Kimball", "Knudsen", "Larson", "Leavitt", "Lund", "Lyman", "Madsen", "Manning",
    "Maughan", "McConkie", "Mickelsen", "Miller", "Monson", "Murdock", "Naylor", "Nebeker", "Nielsen", "Oaks",
    "Odekirk", "Olsen", "Osmond", "Pace", "Packer", "Palmer", "Pendleton", "Petersen", "Poulson", "Pratt",
    "Rasmussen", "Rawson", "Richards", "Rigby", "Robison", "Rowley", "Savage", "Sessions", "Sharp", "Skinner",
    "Smith", "Snow", "Sorensen", "Stevens", "Tanner", "Taylor", "Thurston", "Tolman", "Udall", "Van Wagoner",
    "Wadsworth", "Walker", "Warner", "Webb", "Whitaker", "Wilcox", "Winder", "Wood", "Wright", "Young"
]
employees_data = []
# Using an index up to 30 guarantees exactly 10 per trade, and exactly 3, 3, 4 distribution of skills within each
for i in range(30):
    emp_id = f"EMP{i+1:03d}"
    first_name = random.choice(first_names)
    first_names.remove(first_name)
    last_name = random.choice(last_names)
    last_names.remove(last_name)
    
    # Mathematical distribution guarantees perfect proportions across the company
    trade = TRADES[i % len(TRADES)]
    skill_level = SKILL_LEVELS[(i // len(TRADES)) % len(SKILL_LEVELS)]
    
    # Generate home locations within Utah County
    home_lat = round(random.uniform(LAT_MIN, LAT_MAX), 5)
    home_long = round(random.uniform(LONG_MIN, LONG_MAX), 5)
    
    # Normally distributed hourly rate around $40/hr
    hourly_rate = round(random.normalvariate(40.0, 5.0), 2)
    # Ensure minimum wage bounds to be realistic
    hourly_rate = max(15.0, min(hourly_rate, 75.0))
    
    employees_data.append((emp_id, first_name, last_name, trade, skill_level, home_lat, home_long, hourly_rate))

employees_schema = StructType([
    StructField("employee_id", StringType(), False),
    StructField("first_name", StringType(), False),
    StructField("last_name",StringType(), False),
    StructField("trade", StringType(), False),
    StructField("skill_level", StringType(), False),
    StructField("home_lat", DoubleType(), False),
    StructField("home_long", DoubleType(), False),
    StructField("hourly_rate", DoubleType(), False)
])
df_employees = spark.createDataFrame(employees_data, schema=employees_schema)

# Generate Projects (10-20 active projects)
proj_names = [
    "Alpine Summit HVAC Overhaul", "Beehive State Data Center Cooling", "Canyon Rim Substation Expansion", "Desert Wind Solar Integration", "Eagle Ridge Medical Gas Piping",
    "Fossil Butte Boiler Replacement", "Great Basin Industrial Rewire", "High Uinta Pump Station Retrofit", "Iron King Chillers Phase II", "Juniper Grove Lift Station",
    "King Peak Transformer Upgrade", "Lone Pine Hydronic Heating", "Mesa Verde Waste Water Install", "North Star Ventilation Ducting", "Oasis Valley Fire Sprinkler Main",
    "Painted Desert Electrical Vault", "Quartzite Quarry Power Feed", "Red Rock Server Room CRAC", "Sagebrush District Heating", "Timberline Tower Comms Rack",
    "Uinta Basin Gas Header", "Vermillion Cliffs Pumping Plant", "Wasatch Front Air Handler Unit", "Zion Canyon Graywater System", "Antelope Island Backup Gen",
    "Bear Lake Marina Shore Power", "Copper Mine Heavy Duty Conduit", "Deep Creek Drainage Realignment", "Emigration Canyon Pipe Trace", "Fairview Farm Irrigation Controls",
    "Golden Spike Rail Depot Lighting", "Hidden Valley High-Voltage Feed", "Indian Canyon Blower Install", "Jordan River Siphon Project", "Kamas Valley School HVAC",
    "Lake Mountain Radio Site Power", "Mirror Lake Lodge Winterization", "Navajo Sandstone Septic Field", "Oquirrh View Switchgear Swap", "Promontory Point Scada System",
    "Quaking Aspen Cooling Tower", "Rimrock Residential MEP Rough-in", "Skyline Drive Fiber Conduit", "Tushar Mountain Solar Array", "Utah Lake Pump Filter Array",
    "Valley Forge Foundry Ductwork", "Wolf Creek Water Treatment", "Yellowstone Boundary Heat Pump", "Arches Complex Sanitary Sewer", "Basin & Range VFD Install",
    "Castle Valley Electrical Mains", "Dinosaurland Museum Humidity Control", "Escalante Basin Flare Piping", "Flaming Gorge Turbine Service", "Grand Staircase Site Lighting",
    "Hole-In-The-Rock Hydrant Line", "Island In The Sky HVAC Loop", "Juab County Cold Storage Ref", "Kanab Creek Water Main", "Logan Peak Repeater Battery",
    "Moab Arch Mechanical Penthouse", "Needles District Generator Shed", "Old Deseret Village Rewiring", "Parowan Gap Pipeline Valve", "Rainbow Bridge Pump Refurb",
    "Salt Flats Telemetry Power", "Temple View Boiler Plant", "Ute Mountain Mechanical Mezzanine", "Virgin River Pipe Stabilizing", "Wheeler Peak Exhaust Fans",
    "Yarrow Creek Chilled Water", "Zion Gateway Electrical Panel", "Big Horn Compressor Station", "Cliff Rose Condominium Plumbing", "Douglas Fir Apartment MEP",
    "Elk Ridge Municipal Well Power", "Four Corners Pipe Manifold", "Gunlock Reservoir Flow Meter", "Henry Mountain Radio Tower HVAC", "Iosepa Desert Water Loop",
    "Johnson Canyon Electrical Boring", "Kolob Terrace Plumbing Stack", "Little Sahara Sand-Proof Electric", "Manti Forest Ranger Station MEP", "Nebeker Ranch Irrigation Pump",
    "Ophir Canyon Mine Ventilation", "Panguitch Lake Water Filtration", "Red Butte Lab Gas Upgrade", "Silver Reef Industrial Waste", "Tropic Town Main Street Lighting",
    "Uintalands Cabin HVAC Pack", "Vernal Industrial Boiler Room", "Wildcat Ridge Pump Skid", "X-Stream Creek Hydrologic Sensors", "Yuba Lake Campsite Electrical",
    "Zig-Zag Canyon Pressure Station", "Boulder Mountain Septic Upgrade", "Cottonwood Creek Storm Drainage", "Dead Horse Point Solar Feed", "East Bench Hydronic Loop"
]
num_projects = random.randint(20, 30)
projects_data = []
for i in range(1, num_projects + 1):
    proj_id = f"PRJ{i:03d}"
    proj_name = random.choice(proj_names)
    proj_names.remove(proj_name)
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
TASK_DESCRIPTIONS = {
    'Mechanical': ['Install HVAC system', 'Ductwork route installation', 'HVAC unit maintenance', 'Ventilation setup', 'Gas Piping', 'Final Connections'],
    'Electrical': ['Wire basic circuits', 'Install main breaker panel', 'Run conduit', 'Install light fixtures', 'Electrical safety inspection', 'Final Connections'],
    'Plumbing':  ['Install main water line', 'Connect drainage pipes', 'Install bathroom fixtures', 'Water pressure testing', 'Gas Piping', 'Final Connections']
}

tasks_data = []
for proj in projects_data:
    proj_id = proj[0]
    num_tasks = random.randint(3, 8)
    for _ in range(num_tasks):
        task_id = str(uuid.uuid4())[:8]
        req_skill = random.choice(TRADES)
        task_desc = random.choice(TASK_DESCRIPTIONS[req_skill]) + f" (Phase {random.randint(1, 3)})"
        min_staff = random.randint(1, 4)
        
        # New advanced constraints
        setup_teardown_mins = random.choice([15, 30, 45, 60])
        is_interruptible = random.choice([True, True, True, False]) # 25% chance of being uninterruptible
        block_requirement = random.choice(["Any", "Any", "Half-Day", "Full-Day"])
        
        # Adjust man_hours safely based on constraint realities
        if block_requirement == "Half-Day":
            man_hours_est = round(random.uniform(4.0 * min_staff, 8.0 * min_staff), 1)
        elif block_requirement == "Full-Day":
            man_hours_est = round(random.uniform(8.0 * min_staff, 16.0 * min_staff), 1)
        else:
            man_hours_est = round(random.uniform(4.0, 60.0), 1)
            
        if not is_interruptible:
            # If it must be completed in a single day, it functionally cannot exceed (8 hours * MAX realistic staff)
            # To ensure it's easily solvable by the AI, we'll bound it strictly.
            max_daily_allowed = min_staff * 8.0
            man_hours_est = min(man_hours_est, max_daily_allowed)
            
        # Add realistic task statuses
        # We heavily weight "Backlog" to simulate multi-year project pipelines
        status_pool = ['Backlog', 'Ready', 'In Progress', 'Blocked', 'Completed']
        status_weights = [0.60, 0.20, 0.10, 0.05, 0.05]
        task_status = random.choices(status_pool, weights=status_weights, k=1)[0]
        
        tasks_data.append((task_id, proj_id, req_skill, task_desc, man_hours_est, min_staff, setup_teardown_mins, is_interruptible, block_requirement, task_status))

tasks_schema = StructType([
    StructField("task_id", StringType(), False),
    StructField("project_id", StringType(), False),
    StructField("required_skill", StringType(), False),
    StructField("task_desc", StringType(), False),
    StructField("man_hours_est", DoubleType(), False),
    StructField("min_staff", IntegerType(), False),
    StructField("setup_teardown_mins", IntegerType(), False),
    StructField("is_interruptible", BooleanType(), False),
    StructField("block_requirement", StringType(), False),
    StructField("task_status", StringType(), False)
])
df_tasks = spark.createDataFrame(tasks_data, schema=tasks_schema)

# Define Constraints_Rules
constraints_data = [
    ("Hard", "Electrical max ratio of Apprentice to Journeyman on any task is 1:1"),
    ("Hard", "Plumbing max ratio of Apprentice to Journeyman on any task is 1:2"),
    ("Hard", "Mechanical max ratio of Apprentice to Journeyman on any task is 1:3"),
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
    df_employees.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("Employees")
    df_projects.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("Projects")
    df_tasks.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("Tasks")
    df_constraints.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("Constraints_Rules")
    print("Successfully saved all Delta tables.")
except Exception as e:
    print("Encountered an error while saving to Delta tables. Ensure a Lakehouse is attached.")
    print(f"Error: {str(e)}")

# Display snippets to confirm structure natively in notebook
df_employees.show(5)
df_projects.show(5)
df_tasks.show(5)
df_constraints.show(5, truncate=False)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
