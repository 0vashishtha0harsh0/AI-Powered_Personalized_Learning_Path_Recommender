"""
Build unified O*NET career profiles.

Reads raw O*NET files and creates:
    Data/processed/careers/onet_career_profiles.csv

The profile combines:
    - Occupation
    - Skills
    - Knowledge
    - Abilities
    - Work Activities
    - Tasks
    - Task Ratings
    - Technology Skills
    - Tools
    - Work Styles
    - Work Values
    - Job Zones
    - Education / Training / Experience
    - Related Occupations
    - Emerging Tasks
    - Alternate Titles
    - Reported Titles
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# CHANGE THIS ONLY IF YOUR RAW O*NET DIRECTORY HAS A DIFFERENT NAME
RAW_ONET = PROJECT_ROOT / "Data" / "raw" / "onet" / "db_29_0_text"

OUTPUT_DIR = PROJECT_ROOT / "Data" / "processed" / "careers"
OUTPUT_FILE = OUTPUT_DIR / "onet_career_profiles.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def load_txt(filename):
    path = RAW_ONET / filename

    if not path.exists():
        print(f"[WARNING] Missing: {filename}")
        return pd.DataFrame()

    print(f"Loading: {filename}")

    df = pd.read_csv(
        path,
        sep="\t",
        encoding="utf-8-sig",
        low_memory=False
    )

    df.columns = [c.strip() for c in df.columns]

    print(f"  Shape: {df.shape}")

    return df


def clean_text(x):
    if pd.isna(x):
        return ""

    x = str(x)
    x = re.sub(r"\s+", " ", x)
    return x.strip()


def unique_join(values, limit=None):
    result = []

    for value in values:
        value = clean_text(value)

        if not value:
            continue

        if value not in result:
            result.append(value)

        if limit and len(result) >= limit:
            break

    return " | ".join(result)


def weighted_top_items(df, item_col, value_col="Data Value", top_n=20):
    """
    Get highest-scoring unique items.

    Used for Skills, Knowledge, Abilities, Work Activities,
    Work Styles, etc.
    """

    if df.empty or item_col not in df.columns:
        return ""

    temp = df.copy()

    if value_col in temp.columns:
        temp[value_col] = pd.to_numeric(
            temp[value_col],
            errors="coerce"
        )

        temp = temp.sort_values(
            value_col,
            ascending=False
        )

    return unique_join(
        temp[item_col].tolist(),
        limit=top_n
    )


def group_text(df, code_col, item_col, top_n=20):
    """
    Group an O*NET dataframe by occupation.
    """

    if df.empty:
        return {}

    output = {}

    for code, group in df.groupby(code_col):

        output[code] = weighted_top_items(
            group,
            item_col=item_col,
            top_n=top_n
        )

    return output


def group_technology_text(df, top_n=40, flag=None):
    """Keep named O*NET software examples alongside their categories."""
    if df.empty or "O*NET-SOC Code" not in df.columns:
        return {}
    output = {}
    for code, group in df.groupby("O*NET-SOC Code"):
        ranked = group.copy()
        ranked["_hot"] = ranked.get("Hot Technology", "N").astype(str).str.upper().eq("Y")
        ranked["_demand"] = ranked.get("In Demand", "N").astype(str).str.upper().eq("Y")
        if flag == "hot":
            ranked = ranked[ranked["_hot"]]
        elif flag == "demand":
            ranked = ranked[ranked["_demand"]]
        ranked = ranked.sort_values(["_demand", "_hot"], ascending=False)
        values = []
        for _, row in ranked.iterrows():
            example = clean_text(row.get("Example", ""))
            category = clean_text(row.get("Commodity Title", ""))
            value = " | ".join(item for item in (example, category) if item)
            if value and value not in values:
                values.append(value)
            if len(values) >= top_n:
                break
        output[code] = " | ".join(values)
    return output


# ============================================================
# LOAD DATA
# ============================================================

occupations = load_txt("Occupation Data.txt")

skills = load_txt("Skills.txt")
knowledge = load_txt("Knowledge.txt")
abilities = load_txt("Abilities.txt")
work_activities = load_txt("Work Activities.txt")

tasks = load_txt("Task Statements.txt")
task_ratings = load_txt("Task Ratings.txt")

technology = load_txt("Technology Skills.txt")
tools = load_txt("Tools Used.txt")

work_styles = load_txt("Work Styles.txt")
work_values = load_txt("Work Values.txt")

job_zones = load_txt("Job Zones.txt")

education = load_txt(
    "Education, Training, and Experience.txt"
)

related = load_txt(
    "Related Occupations.txt"
)

emerging_tasks = load_txt(
    "Emerging Tasks.txt"
)

alternate_titles = load_txt(
    "Alternate Titles.txt"
)

reported_titles = load_txt(
    "Sample of Reported Titles.txt"
)


# ============================================================
# NORMALIZE OCCUPATION CODE
# ============================================================

def normalize_code(df, column="O*NET-SOC Code"):

    if df.empty or column not in df.columns:
        return df

    df[column] = (
        df[column]
        .astype(str)
        .str.strip()
    )

    return df


all_dfs = [
    occupations,
    skills,
    knowledge,
    abilities,
    work_activities,
    tasks,
    task_ratings,
    technology,
    tools,
    work_styles,
    work_values,
    job_zones,
    education,
    related,
    emerging_tasks,
    alternate_titles,
    reported_titles
]

for df in all_dfs:
    normalize_code(df)


# ============================================================
# OCCUPATION BASE
# ============================================================

if occupations.empty:
    raise RuntimeError(
        "Occupation Data.txt could not be loaded."
    )

profiles = occupations[
    [
        "O*NET-SOC Code",
        "Title",
        "Description"
    ]
].copy()

profiles = profiles.rename(
    columns={
        "O*NET-SOC Code": "onet_soc_code",
        "Title": "title",
        "Description": "description"
    }
)


# ============================================================
# 1. SKILLS
# ============================================================

print("\nBuilding SKILLS profiles...")

skills_profile = group_text(
    skills,
    "O*NET-SOC Code",
    "Element Name",
    top_n=25
)

profiles["skills"] = profiles[
    "onet_soc_code"
].map(skills_profile).fillna("")


# ============================================================
# 2. KNOWLEDGE
# ============================================================

print("Building KNOWLEDGE profiles...")

knowledge_profile = group_text(
    knowledge,
    "O*NET-SOC Code",
    "Element Name",
    top_n=20
)

profiles["knowledge"] = profiles[
    "onet_soc_code"
].map(knowledge_profile).fillna("")


# ============================================================
# 3. ABILITIES
# ============================================================

print("Building ABILITIES profiles...")

abilities_profile = group_text(
    abilities,
    "O*NET-SOC Code",
    "Element Name",
    top_n=20
)

profiles["abilities"] = profiles[
    "onet_soc_code"
].map(abilities_profile).fillna("")


# ============================================================
# 4. WORK ACTIVITIES
# ============================================================

print("Building WORK ACTIVITIES profiles...")

activities_profile = group_text(
    work_activities,
    "O*NET-SOC Code",
    "Element Name",
    top_n=20
)

profiles["work_activities"] = profiles[
    "onet_soc_code"
].map(activities_profile).fillna("")


# ============================================================
# 5. TASKS
# ============================================================

print("Building TASK profiles...")

task_profile = {}

if not tasks.empty:

    for code, group in tasks.groupby(
        "O*NET-SOC Code"
    ):

        task_profile[code] = unique_join(
            group["Task"].tolist(),
            limit=20
        )

profiles["tasks"] = profiles[
    "onet_soc_code"
].map(task_profile).fillna("")


# ============================================================
# 6. TECHNOLOGY
# ============================================================

print("Building TECHNOLOGY profiles...")

technology_profile = {}

if not technology.empty:

    temp = technology.copy()

    if "In Demand" in temp.columns:

        temp["_demand"] = (
            temp["In Demand"]
            .astype(str)
            .str.lower()
            .isin(["y", "yes", "true", "1"])
        )

        temp = temp.sort_values(
            "_demand",
            ascending=False
        )

    for code, group in temp.groupby(
        "O*NET-SOC Code"
    ):

        technology_profile[code] = group_technology_text(group, top_n=40).get(code, "")

profiles["technology"] = profiles[
    "onet_soc_code"
].map(technology_profile).fillna("")
profiles["technology_hot"] = profiles["onet_soc_code"].map(
    group_technology_text(technology, top_n=40, flag="hot")
).fillna("")
profiles["technology_in_demand"] = profiles["onet_soc_code"].map(
    group_technology_text(technology, top_n=40, flag="demand")
).fillna("")


# ============================================================
# 7. TOOLS
# ============================================================

print("Building TOOL profiles...")

tools_profile = {}

if not tools.empty:

    for code, group in tools.groupby(
        "O*NET-SOC Code"
    ):

        tools_profile[code] = unique_join(
            group["Commodity Title"].tolist(),
            limit=20
        )

profiles["tools"] = profiles[
    "onet_soc_code"
].map(tools_profile).fillna("")


# ============================================================
# 8. WORK STYLES
# ============================================================

print("Building WORK STYLE profiles...")

work_styles_profile = group_text(
    work_styles,
    "O*NET-SOC Code",
    "Element Name",
    top_n=12
)

profiles["work_styles"] = profiles[
    "onet_soc_code"
].map(work_styles_profile).fillna("")


# ============================================================
# 9. WORK VALUES
# ============================================================

print("Building WORK VALUE profiles...")

work_values_profile = group_text(
    work_values,
    "O*NET-SOC Code",
    "Element Name",
    top_n=10
)

profiles["work_values"] = profiles[
    "onet_soc_code"
].map(work_values_profile).fillna("")


# ============================================================
# 10. JOB ZONE
# ============================================================

print("Adding JOB ZONE...")

if not job_zones.empty:

    job_zone_map = (
        job_zones
        .drop_duplicates("O*NET-SOC Code")
        .set_index("O*NET-SOC Code")["Job Zone"]
        .to_dict()
    )

    profiles["job_zone"] = profiles[
        "onet_soc_code"
    ].map(job_zone_map)

else:

    profiles["job_zone"] = np.nan


# ============================================================
# 11. EDUCATION / TRAINING / EXPERIENCE
# ============================================================

print("Building EDUCATION profiles...")

education_profile = {}

if not education.empty:

    for code, group in education.groupby(
        "O*NET-SOC Code"
    ):

        education_profile[code] = unique_join(
            group["Element Name"].tolist(),
            limit=15
        )

profiles["education_training"] = profiles[
    "onet_soc_code"
].map(education_profile).fillna("")


# ============================================================
# 12. RELATED OCCUPATIONS
# ============================================================

print("Building RELATED OCCUPATION profiles...")

related_profile = {}

if not related.empty:

    for code, group in related.groupby(
        "O*NET-SOC Code"
    ):

        related_profile[code] = unique_join(
            group["Related O*NET-SOC Code"].tolist(),
            limit=15
        )

profiles["related_occupations"] = profiles[
    "onet_soc_code"
].map(related_profile).fillna("")


# ============================================================
# 13. EMERGING TASKS
# ============================================================

print("Building EMERGING TASK profiles...")

emerging_profile = {}

if not emerging_tasks.empty:

    for code, group in emerging_tasks.groupby(
        "O*NET-SOC Code"
    ):

        emerging_profile[code] = unique_join(
            group["Task"].tolist(),
            limit=15
        )

profiles["emerging_tasks"] = profiles[
    "onet_soc_code"
].map(emerging_profile).fillna("")


# ============================================================
# 14. ALTERNATE TITLES
# ============================================================

print("Building ALTERNATE TITLE profiles...")

alternate_profile = {}

if not alternate_titles.empty:

    for code, group in alternate_titles.groupby(
        "O*NET-SOC Code"
    ):

        alternate_profile[code] = unique_join(
            group["Alternate Title"].tolist(),
            limit=20
        )

profiles["alternate_titles"] = profiles[
    "onet_soc_code"
].map(alternate_profile).fillna("")


# ============================================================
# 15. REPORTED TITLES
# ============================================================

print("Building REPORTED TITLE profiles...")

reported_profile = {}

if not reported_titles.empty:

    for code, group in reported_titles.groupby(
        "O*NET-SOC Code"
    ):

        reported_profile[code] = unique_join(
            group["Reported Job Title"].tolist(),
            limit=20
        )

profiles["reported_titles"] = profiles[
    "onet_soc_code"
].map(reported_profile).fillna("")


# ============================================================
# 16. COMBINED SEARCH TEXT
# ============================================================

print("\nBuilding combined semantic text...")

profiles["career_text"] = (
    "Occupation: "
    + profiles["title"].fillna("")
    + ". Description: "
    + profiles["description"].fillna("")
    + ". Skills: "
    + profiles["skills"].fillna("")
    + ". Knowledge: "
    + profiles["knowledge"].fillna("")
    + ". Abilities: "
    + profiles["abilities"].fillna("")
    + ". Work Activities: "
    + profiles["work_activities"].fillna("")
    + ". Tasks: "
    + profiles["tasks"].fillna("")
    + ". Technology: "
    + profiles["technology"].fillna("")
    + ". Tools: "
    + profiles["tools"].fillna("")
    + ". Work Styles: "
    + profiles["work_styles"].fillna("")
    + ". Work Values: "
    + profiles["work_values"].fillna("")
    + ". Education: "
    + profiles["education_training"].fillna("")
    + ". Emerging Tasks: "
    + profiles["emerging_tasks"].fillna("")
    + ". Alternate Titles: "
    + profiles["alternate_titles"].fillna("")
    + ". Reported Titles: "
    + profiles["reported_titles"].fillna("")
)


# ============================================================
# 17. QUALITY CHECKS
# ============================================================

print("\n" + "=" * 80)
print("PROFILE QUALITY")
print("=" * 80)

for col in [
    "skills",
    "knowledge",
    "abilities",
    "work_activities",
    "tasks",
    "technology",
    "tools",
    "work_styles",
    "work_values",
    "education_training",
    "related_occupations",
    "emerging_tasks",
    "alternate_titles",
    "reported_titles"
]:

    non_empty = (
        profiles[col]
        .fillna("")
        .astype(str)
        .str.len()
        .gt(0)
        .sum()
    )

    print(
        f"{col:25s}: "
        f"{non_empty:4d}/{len(profiles)}"
    )


# ============================================================
# 18. SAVE
# ============================================================

profiles.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)

print(
    f"Profiles created : {len(profiles)}"
)

print(
    f"Columns          : {len(profiles.columns)}"
)

print(
    f"Output           : {OUTPUT_FILE}"
)


# ============================================================
# DATA SCIENTIST CHECK
# ============================================================

print("\n" + "=" * 80)
print("DATA SCIENTIST CHECK")
print("=" * 80)

ds = profiles[
    profiles["title"]
    .astype(str)
    .str.contains(
        "Data Scientist",
        case=False,
        na=False
    )
]

if len(ds):

    row = ds.iloc[0]

    print(
        "\nOccupation:",
        row["title"]
    )

    print(
        "SOC:",
        row["onet_soc_code"]
    )

    print(
        "\nSkills:\n",
        row["skills"][:1500]
    )

    print(
        "\nKnowledge:\n",
        row["knowledge"][:1500]
    )

    print(
        "\nTasks:\n",
        row["tasks"][:2000]
    )

    print(
        "\nTechnology:\n",
        row["technology"][:1500]
    )

    print(
        "\nEducation:\n",
        row["education_training"][:1000]
    )

else:

    print(
        "Data Scientist occupation not found."
    )