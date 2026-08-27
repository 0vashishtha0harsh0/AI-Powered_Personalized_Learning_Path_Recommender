"""
STEP 1: Build the skill/career taxonomy backbone.
Run this in your notebook (adjust RAW/OUT paths to match your project root).

Produces:
  processed/skills/skills_taxonomy.csv         -> fine-grained ESCO skills (canonical, deduped)
  processed/skills/onet_elements.csv           -> broad O*NET elements (Skills/Knowledge/Abilities)
  processed/careers/occupations.csv            -> O*NET occupation master list
  processed/careers/occupation_element_scores.csv -> occupation x element importance/level matrix
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW = PROJECT_ROOT / "Data" / "raw"
OUT = PROJECT_ROOT / "Data" / "processed"
(OUT / "skills").mkdir(parents=True, exist_ok=True)
(OUT / "careers").mkdir(parents=True, exist_ok=True)

# ============================================================
# 1. ESCO FINE-GRAINED SKILL TAXONOMY
#    Source file is job-posting-derived skill extraction, NOT
#    a clean taxonomy — so we dedupe on skill_esco_uri to get
#    one canonical row per skill, and keep frequency as a
#    real-world "market demand" signal (bonus feature).
# ============================================================
esco_raw = pd.read_excel(f"{RAW}/esco/skills - 15000 sample.xlsx")

print("ESCO raw shape:", esco_raw.shape)
print("Null skill_esco_uri:", esco_raw["skill_esco_uri"].isna().sum())

# drop rows with no matched skill
esco_raw = esco_raw.dropna(subset=["skill_esco_uri"])

# aggregate: one row per unique skill, with demand frequency + avg fit confidence
esco_agg = (
    esco_raw.groupby("skill_esco_uri")
    .agg(
        skill_label=("skill_esco_label", "first"),
        skill_alias=("skill_esco_alias", "first"),
        is_green=("green", "max"),
        is_digital=("digital", "max"),
        is_language=("language", "max"),
        is_research=("research", "max"),
        parent_1=("parent_1", "first"),
        parent_2=("parent_2", "first"),
        parent_3=("parent_3", "first"),
        parent_4=("parent_4", "first"),
        demand_frequency=("jobposting_id", "count"),          # how often this skill appears in job postings
        avg_fit_score=("skill_esco_fit_score", "mean"),        # extraction confidence
    )
    .reset_index()
)

esco_agg["skill_id"] = "esco_" + pd.factorize(esco_agg["skill_esco_uri"])[0].astype(str)

skills_taxonomy = esco_agg.rename(columns={"skill_esco_uri": "esco_uri"})[
    [
        "skill_id", "esco_uri", "skill_label", "skill_alias",
        "parent_1", "parent_2", "parent_3", "parent_4",
        "is_green", "is_digital", "is_language", "is_research",
        "demand_frequency", "avg_fit_score",
    ]
]

skills_taxonomy.to_csv(f"{OUT}/skills/skills_taxonomy.csv", index=False)
print("\nUnique fine-grained skills:", skills_taxonomy.shape[0])
print(skills_taxonomy.sort_values("demand_frequency", ascending=False).head(10)[
    ["skill_label", "demand_frequency", "parent_3"]
])

# ============================================================
# 2. O*NET BROAD ELEMENT TAXONOMY (Skills / Knowledge / Abilities)
#    Content Model Reference gives the canonical description
#    of each element (used later for embedding-based crosswalk).
# ============================================================
ONET = f"{RAW}/onet/db_29_0_text"

content_model = pd.read_csv(f"{ONET}/Content Model Reference.txt", sep="\t")

onet_skills = pd.read_csv(f"{ONET}/Skills.txt", sep="\t")
onet_knowledge = pd.read_csv(f"{ONET}/Knowledge.txt", sep="\t")
onet_abilities = pd.read_csv(f"{ONET}/Abilities.txt", sep="\t")

for df, tag in [(onet_skills, "skill"), (onet_knowledge, "knowledge"), (onet_abilities, "ability")]:
    df["element_type"] = tag

onet_combined = pd.concat([onet_skills, onet_knowledge, onet_abilities], ignore_index=True)

# canonical element list = unique Element ID/Name, joined to its description
onet_elements = (
    onet_combined[["Element ID", "Element Name", "element_type"]]
    .drop_duplicates(subset=["Element ID"])
    .merge(content_model[["Element ID", "Description"]], on="Element ID", how="left")
)
onet_elements = onet_elements.rename(
    columns={"Element ID": "element_id", "Element Name": "element_name", "Description": "element_description"}
)
onet_elements.to_csv(f"{OUT}/skills/onet_elements.csv", index=False)
print("\nO*NET broad elements (skills+knowledge+abilities):", onet_elements.shape[0])
print(onet_elements["element_type"].value_counts())

# ============================================================
# 3. OCCUPATION MASTER LIST
# ============================================================
occ = pd.read_csv(f"{ONET}/Occupation Data.txt", sep="\t")
occ = occ.rename(columns={"O*NET-SOC Code": "onet_soc_code", "Title": "title", "Description": "description"})
occ.to_csv(f"{OUT}/careers/occupations.csv", index=False)
print("\nOccupations:", occ.shape[0])

# ============================================================
# 4. OCCUPATION x ELEMENT SCORE MATRIX
#    Scale ID: IM = Importance (1-5), LV = Level (0-7)
#    We pivot both scales side by side per (occupation, element).
# ============================================================
def build_scores(df, element_type):
    df = df.copy()
    df["element_type"] = element_type
    piv = df.pivot_table(
        index=["O*NET-SOC Code", "Element ID"],
        columns="Scale ID",
        values="Data Value",
        aggfunc="first",
    ).reset_index()
    piv["element_type"] = element_type
    return piv

scores_skills = build_scores(onet_skills, "skill")
scores_knowledge = build_scores(onet_knowledge, "knowledge")
scores_abilities = build_scores(onet_abilities, "ability")

occupation_element_scores = pd.concat([scores_skills, scores_knowledge, scores_abilities], ignore_index=True)
occupation_element_scores = occupation_element_scores.rename(
    columns={"O*NET-SOC Code": "onet_soc_code", "Element ID": "element_id", "IM": "importance", "LV": "level"}
)
occupation_element_scores = occupation_element_scores.merge(
    onet_elements[["element_id", "element_name"]], on="element_id", how="left"
)

# O*NET publishes ratings for detailed occupations (for example
# 15-2051.01/15-2051.02) while the occupation master also contains their
# parent (15-2051.00). Materialize parent rows from descendants so every
# master occupation has a usable, traceable profile instead of relying on a
# runtime fallback that mixes rows silently.
occupation_element_scores["onet_soc_code"] = (
    occupation_element_scores["onet_soc_code"].astype(str).str.strip().str.lower()
)
occ["onet_soc_code"] = occ["onet_soc_code"].astype(str).str.strip().str.lower()
existing_codes = set(occupation_element_scores["onet_soc_code"].unique())
derived_rows = []
for code in occ["onet_soc_code"].unique():
    if code in existing_codes or "." not in code:
        continue
    descendants = occupation_element_scores[
        occupation_element_scores["onet_soc_code"].str.startswith(code.rsplit(".", 1)[0] + ".")
    ]
    if descendants.empty:
        continue
    grouped = descendants.groupby(["element_id", "element_type", "element_name"], as_index=False)[
        ["importance", "level"]
    ].median()
    grouped["onet_soc_code"] = code
    grouped["derived_from"] = "descendants"
    derived_rows.append(grouped)

if derived_rows:
    occupation_element_scores = pd.concat(
        [occupation_element_scores, pd.concat(derived_rows, ignore_index=True)],
        ignore_index=True,
    )

occupation_element_scores["derived_from"] = occupation_element_scores.get(
    "derived_from", pd.Series("raw", index=occupation_element_scores.index)
).fillna("raw")
coverage = set(occupation_element_scores["onet_soc_code"].unique())
missing = sorted(set(occ["onet_soc_code"]) - coverage)
if missing:
    print(f"[WARNING] {len(missing)} occupations still have no ratings: {missing[:10]}")
else:
    print("[OK] Every occupation has an occupation-element profile.")

occupation_element_scores.to_csv(f"{OUT}/careers/occupation_element_scores.csv", index=False)
print("\nOccupation-element score rows:", occupation_element_scores.shape[0])
print(occupation_element_scores.dropna(subset=["importance"]).sort_values("importance", ascending=False).head(10)[
    ["onet_soc_code", "element_name", "importance", "level"]
])

print("\n\n=== SUMMARY ===")
print(f"Fine-grained skills (ESCO): {skills_taxonomy.shape[0]}")
print(f"Broad elements (O*NET): {onet_elements.shape[0]}")
print(f"Occupations: {occ.shape[0]}")
print(f"Occupation-skill score rows: {occupation_element_scores.shape[0]}")