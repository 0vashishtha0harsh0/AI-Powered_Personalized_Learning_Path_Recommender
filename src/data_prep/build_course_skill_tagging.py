"""
STEP 4: Tag every course with the skills it teaches.

Uses 3 signals combined (not just embedding similarity alone,
which gets noisy at this scale):
  1. Embedding similarity  -> semantic match (course text vs skill)
  2. Exact keyword match   -> skill label/alias literally appears in course text
  3. Category alignment    -> boost skills whose ESCO parent category
                               matches the course's Udemy category

Install once:
    pip install sentence-transformers faiss-cpu flashtext

Produces:
  processed/courses/course_skills.csv   (long format: course_id, skill_id, score, matched_by)
"""

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from flashtext import KeywordProcessor
import faiss
import os
import re

OUT = "../Data/processed"
EMB = "../embeddings"
os.makedirs(f"{OUT}/courses", exist_ok=True)

# ------------------------------------------------------------
# Load data built in previous steps
# ------------------------------------------------------------
courses = pd.read_csv(f"{OUT}/courses/unified_courses.csv")
skills = pd.read_csv(f"{OUT}/skills/skills_taxonomy.csv")
skill_ids_order = pd.read_csv(f"{EMB}/skill_embeddings/esco_skill_ids.csv")["skill_id"].tolist()
skill_emb = np.load(f"{EMB}/skill_embeddings/esco_skill_embeddings.npy")

skills = skills.set_index("skill_id").loc[skill_ids_order].reset_index()  # align order with embeddings

courses["title"] = courses["title"].fillna("").astype(str)
courses["description"] = courses["description"].fillna("").astype(str)
courses["embed_text"] = courses["embed_text"].fillna("").astype(str)

# ============================================================
# SIGNAL 1: Embedding similarity via FAISS
# ============================================================
model = SentenceTransformer("all-mpnet-base-v2")  # same model as skill embeddings -> comparable space

skill_index = faiss.IndexFlatIP(skill_emb.shape[1])  # inner product == cosine (embeddings are normalized)
skill_index.add(skill_emb.astype("float32"))

TOP_K_EMBED = 12
EMBED_THRESHOLD = 0.38

embed_matches = {}  # course_row_idx -> list of (skill_idx, score)

BATCH = 512
n = len(courses)
print(f"Embedding {n} courses in batches of {BATCH}...")
for start in range(0, n, BATCH):
    end = min(start + BATCH, n)
    batch_text = courses["embed_text"].iloc[start:end].tolist()
    batch_emb = model.encode(batch_text, normalize_embeddings=True, show_progress_bar=False)
    D, I = skill_index.search(batch_emb.astype("float32"), TOP_K_EMBED)
    for local_i in range(end - start):
        global_i = start + local_i
        pairs = [(int(I[local_i][k]), float(D[local_i][k])) for k in range(TOP_K_EMBED)
                 if D[local_i][k] >= EMBED_THRESHOLD]
        embed_matches[global_i] = pairs
    if (start // BATCH) % 10 == 0:
        print(f"  {end}/{n} courses embedded")

print("Embedding signal done.")

# ============================================================
# SIGNAL 2: Exact keyword match via FlashText (fast multi-pattern search)
# ============================================================
kp = KeywordProcessor(case_sensitive=False)
for _, row in skills.iterrows():
    label = str(row["skill_label"]).strip()
    if len(label) >= 3:
        kp.add_keyword(label, row["skill_id"])
    alias = row.get("skill_alias")
    if pd.notna(alias) and len(str(alias).strip()) >= 3:
        kp.add_keyword(str(alias).strip(), row["skill_id"])

skill_id_to_idx = {sid: i for i, sid in enumerate(skill_ids_order)}

print("Running keyword matching...")
keyword_matches = {}  # course_row_idx -> set of skill_id
for i, text in enumerate(courses["embed_text"].tolist()):
    found = set(kp.extract_keywords(text))
    keyword_matches[i] = found
print("Keyword signal done.")

# ============================================================
# SIGNAL 3: Category alignment boost
# ============================================================
CATEGORY_KEYWORDS = {
    "Tech": ["computer", "ict", "program", "software", "technolog", "data", "engineer"],
    "IT & Software": ["computer", "ict", "program", "software", "technolog", "data", "engineer"],
    "Business": ["business", "management", "administration", "project"],
    "Design": ["design", "art", "creativ", "graphic"],
    "Marketing": ["marketing", "sales", "communication", "media"],
    "Finance": ["financ", "account", "economic", "audit"],
}

skills["parent_text"] = (
    skills[["parent_1", "parent_2", "parent_3", "parent_4"]]
    .fillna("").agg(" ".join, axis=1).str.lower()
)

def category_boost(skill_idx, category):
    if category not in CATEGORY_KEYWORDS or pd.isna(category):
        return 1.0
    ptext = skills.iloc[skill_idx]["parent_text"]
    for kw in CATEGORY_KEYWORDS[category]:
        if kw in ptext:
            return 1.2
    return 1.0

# ============================================================
# COMBINE SIGNALS -> final course_skills table
# ============================================================
rows = []
for i in range(n):
    category = courses.iloc[i]["category"]
    course_id = courses.iloc[i]["course_id"]

    scored = {}  # skill_idx -> (score, matched_by set)

    for skill_idx, sim in embed_matches.get(i, []):
        boost = category_boost(skill_idx, category)
        scored[skill_idx] = [sim * boost, {"embedding"}]

    for skill_id in keyword_matches.get(i, []):
        skill_idx = skill_id_to_idx.get(skill_id)
        if skill_idx is None:
            continue
        boost = category_boost(skill_idx, category)
        base = 0.75 * boost  # keyword hits get a strong fixed base score
        if skill_idx in scored:
            scored[skill_idx][0] = max(scored[skill_idx][0], base)
            scored[skill_idx][1].add("keyword")
        else:
            scored[skill_idx] = [base, {"keyword"}]

    for skill_idx, (score, matched_by) in scored.items():
        rows.append({
            "course_id": course_id,
            "skill_id": skill_ids_order[skill_idx],
            "score": round(score, 4),
            "matched_by": "+".join(sorted(matched_by)),
        })

course_skills = pd.DataFrame(rows)

# keep top-8 skills per course by score (avoid over-tagging generic courses)
course_skills = (
    course_skills.sort_values("score", ascending=False)
    .groupby("course_id")
    .head(8)
    .reset_index(drop=True)
)

course_skills.to_csv(f"{OUT}/courses/course_skills.csv", index=False)

# ============================================================
# DIAGNOSTICS
# ============================================================
print("\n=== SUMMARY ===")
print("Total course-skill tags:", course_skills.shape[0])
print("Courses with >=1 skill tagged:", course_skills["course_id"].nunique(), "/", n)
print("\nMatched-by breakdown:")
print(course_skills["matched_by"].value_counts())

print("\n=== Most frequently tagged skills (sanity check) ===")
top_skills = course_skills.merge(skills[["skill_id", "skill_label"]], on="skill_id")
print(top_skills["skill_label"].value_counts().head(15))

print("\n=== Sample: 5 random courses with their tagged skills ===")
sample_courses = courses.sample(5, random_state=7)["course_id"].tolist()
for cid in sample_courses:
    title = courses[courses["course_id"] == cid]["title"].values[0]
    tags = course_skills[course_skills["course_id"] == cid].merge(
        skills[["skill_id", "skill_label"]], on="skill_id"
    )
    print(f"\n[{cid}] {title}")
    print(tags[["skill_label", "score", "matched_by"]].to_string(index=False))