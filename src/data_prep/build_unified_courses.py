"""
STEP 3: Unify Udemy(x2) + EdX + Coursera into one clean course table.

Produces:
  processed/courses/unified_courses.csv
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW = PROJECT_ROOT / "Data" / "raw" / "courses"
OUT = PROJECT_ROOT / "Data" / "processed" / "courses"
OUT.mkdir(parents=True, exist_ok=True)

def safe_str(x):
    return "" if pd.isna(x) else str(x).strip()

# ============================================================
# UDEMY 1  (Title, Summary, Enrollment, Stars, Rating, Link, Category)
# ============================================================
u1 = pd.read_csv(f"{RAW}/udemy/Udemy_Courses.csv")
u1_std = pd.DataFrame({
    "course_id": "udemy1_" + u1.index.astype(str),
    "source": "udemy",
    "title": u1["Title"],
    "description": u1["Summary"],
    "provider": None,
    "difficulty": None,
    "category": u1["Category"],
    "rating": pd.to_numeric(u1["Rating"], errors="coerce"),
    "num_enrolled": u1["Enrollment"],
    "url": u1["Link"],
    "price": None,
    "certificate_type": None,
})

# ============================================================
# UDEMY 2  (id, title, url, ..., avg_rating, num_subscribers, ...)
# ============================================================
u2 = pd.read_csv(f"{RAW}/udemy/udemy_output_All_IT__Software_p1_p626.csv")
u2_std = pd.DataFrame({
    "course_id": "udemy2_" + u2["id"].astype(str),
    "source": "udemy",
    "title": u2["title"],
    "description": None,          # no description column in this file
    "provider": None,
    "difficulty": None,
    "category": "IT & Software",  # this file is scoped to this category
    "rating": pd.to_numeric(u2["avg_rating"], errors="coerce"),
    "num_enrolled": u2["num_subscribers"],
    "url": "https://www.udemy.com" + u2["url"].astype(str),
    "price": u2["price_detail__price_string"],
    "certificate_type": None,
})

# ============================================================
# EDX  (Name, University, Difficulty Level, Link, About, Course Description)
# ============================================================
ex = pd.read_csv(f"{RAW}/edx/EdX.csv")
ex_std = pd.DataFrame({
    "course_id": "edx_" + ex.index.astype(str),
    "source": "edx",
    "title": ex["Name"],
    "description": ex["About"].fillna("").astype(str) + " " + ex["Course Description"].fillna("").astype(str),
    "provider": ex["University"],
    "difficulty": ex["Difficulty Level"],
    "category": None,
    "rating": None,
    "num_enrolled": None,
    "url": ex["Link"],
    "price": None,
    "certificate_type": None,
})

# ============================================================
# COURSERA (course_title, course_organization, course_Certificate_type,
#            course_rating, course_difficulty, course_students_enrolled)
# ============================================================
co = pd.read_csv(f"{RAW}/coursera/coursea_data.csv")
co_std = pd.DataFrame({
    "course_id": "coursera_" + co.index.astype(str),
    "source": "coursera",
    "title": co["course_title"],
    "description": None,   # no description column here
    "provider": co["course_organization"],
    "difficulty": co["course_difficulty"],
    "category": None,
    "rating": pd.to_numeric(co["course_rating"], errors="coerce") if "course_rating" in co.columns else None,
    "num_enrolled": co["course_students_enrolled"],
    "url": None,
    "price": None,
    "certificate_type": co["course_Certificate_type"],
})

# ============================================================
# COMBINE + CLEAN
# ============================================================
unified = pd.concat([u1_std, u2_std, ex_std, co_std], ignore_index=True)

unified["title"] = unified["title"].apply(safe_str)
unified["description"] = unified["description"].apply(safe_str)
unified = unified[unified["title"].str.len() > 2].reset_index(drop=True)
unified = unified.drop_duplicates(subset=["source", "title"]).reset_index(drop=True)

# content_richness_score: how much text signal do we actually have for this
# course -> used later to weight confidence in skill tagging
def richness(row):
    score = 0
    if len(row["title"]) > 0:
        score += 1
    if len(row["description"]) > 20:
        score += 2       # description is the highest-value signal
    if pd.notna(row["category"]):
        score += 1
    if pd.notna(row["difficulty"]):
        score += 1
    return score

unified["content_richness_score"] = unified.apply(richness, axis=1)

# combined text used for embeddings downstream: title is always there,
# description added when available, category/provider added as light context
def build_embed_text(row):
    parts = [row["title"]]
    if len(row["description"]) > 20:
        parts.append(row["description"])
    if pd.notna(row["category"]):
        parts.append(f"Category: {row['category']}")
    if pd.notna(row["provider"]):
        parts.append(f"Provider: {row['provider']}")
    return " | ".join(parts)

unified["embed_text"] = unified.apply(build_embed_text, axis=1)

unified.to_csv(f"{OUT}/unified_courses.csv", index=False)

print("=== SUMMARY ===")
print("Total unified courses:", unified.shape[0])
print("\nBy source:")
print(unified["source"].value_counts())
print("\nContent richness distribution:")
print(unified["content_richness_score"].value_counts().sort_index())
print("\n% missing description:", round(100 * (unified["description"].str.len() < 20).mean(), 1), "%")
print("\nSample rows:")
print(unified[["source", "title", "category", "difficulty", "content_richness_score"]].sample(5, random_state=1))