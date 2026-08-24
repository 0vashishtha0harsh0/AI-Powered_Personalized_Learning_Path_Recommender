"""
STEP 5: AI-Powered Personalized Learning Path Recommendation Engine

Pipeline:

1. Learner free-text goal
        ↓
2. O*NET career-profile semantic matching
        ↓
3. O*NET career profile
        ↓
4. ESCO fine-grained skill inference
        ↓
5. Learner skill matching
        ↓
6. Skill gap analysis
        ↓
7. Course recommendation
        ↓
8. Milestone-based roadmap

O*NET profile includes:
- Skills
- Knowledge
- Abilities
- Work Activities
- Tasks
- Technology
- Tools
- Work Styles
- Work Values
- Education / Training
- Job Zone
- Related Occupations
- Alternate Titles
- Reported Titles

This version keeps the existing ESCO + course recommendation pipeline
and upgrades occupation matching using the complete O*NET career profile.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA = PROJECT_ROOT / "Data" / "processed"
EMB = PROJECT_ROOT / "embeddings"

CAREER_DATA = DATA / "careers"
SKILL_DATA = DATA / "skills"
COURSE_DATA = DATA / "courses"

CAREER_EMB = EMB / "career_embeddings"
SKILL_EMB = EMB / "skill_embeddings"

CAREER_EMB.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD DATA
# ============================================================

print("Loading data...")

# ------------------------------------------------------------
# O*NET career profiles
# ------------------------------------------------------------

career_profiles_path = CAREER_DATA / "onet_career_profiles.csv"

if not career_profiles_path.exists():
    raise FileNotFoundError(
        f"\nO*NET career profile file not found:\n"
        f"{career_profiles_path}\n\n"
        f"Run:\n"
        f"python src/preprocessing/build_onet_career_profiles.py"
    )

career_profiles = pd.read_csv(career_profiles_path)

print(f"Loaded O*NET career profiles: {career_profiles.shape}")


# ------------------------------------------------------------
# Existing processed datasets
# ------------------------------------------------------------

crosswalk = pd.read_csv(
    SKILL_DATA / "esco_onet_crosswalk.csv"
)

skills_taxonomy = pd.read_csv(
    SKILL_DATA / "skills_taxonomy.csv"
)

course_skills = pd.read_csv(
    COURSE_DATA / "course_skills.csv"
)

courses = pd.read_csv(
    COURSE_DATA / "unified_courses.csv"
)


# ============================================================
# MODEL
# ============================================================

print("Loading embedding model...")

model = SentenceTransformer("all-mpnet-base-v2")


# ============================================================
# INDEXES
# ============================================================

print("Building skill indexes...")


skills_lookup = skills_taxonomy.set_index("skill_id")


course_skills_by_skill = {
    sid: grp
    for sid, grp in course_skills.groupby("skill_id")
}


courses_lookup = courses.set_index("course_id")


# ============================================================
# HELPER
# ============================================================

def clean_text(value):
    """
    Convert NaN / None / non-string values into clean strings.
    """
    if pd.isna(value):
        return ""

    return str(value).strip()


def combine_profile_text(row):
    """
    Convert one complete O*NET career profile into semantic text.

    The profile builder creates columns such as:

    skills
    knowledge
    abilities
    work_activities
    tasks
    technology
    tools
    work_styles
    work_values
    education_training
    job_zone
    related_occupations
    emerging_tasks
    alternate_titles
    reported_titles

    We deliberately weight important career signals by repeating
    selected sections.
    """

    title = clean_text(row.get("title", ""))
    description = clean_text(row.get("description", ""))

    skills = clean_text(row.get("skills", ""))
    knowledge = clean_text(row.get("knowledge", ""))
    abilities = clean_text(row.get("abilities", ""))
    activities = clean_text(row.get("work_activities", ""))
    tasks = clean_text(row.get("tasks", ""))
    technology = clean_text(row.get("technology", ""))
    tools = clean_text(row.get("tools", ""))
    work_styles = clean_text(row.get("work_styles", ""))
    work_values = clean_text(row.get("work_values", ""))
    education = clean_text(row.get("education_training", ""))
    job_zone = clean_text(row.get("job_zone", ""))
    related = clean_text(row.get("related_occupations", ""))
    emerging = clean_text(row.get("emerging_tasks", ""))
    alternate = clean_text(row.get("alternate_titles", ""))
    reported = clean_text(row.get("reported_titles", ""))

    text = f"""
Occupation: {title}

Description:
{description}

Skills:
{skills}

Knowledge:
{knowledge}

Abilities:
{abilities}

Work Activities:
{activities}

Tasks:
{tasks}

Technology:
{technology}

Tools:
{tools}

Work Styles:
{work_styles}

Work Values:
{work_values}

Education, Training and Experience:
{education}

Job Zone:
{job_zone}

Related Occupations:
{related}

Emerging Tasks:
{emerging}

Alternate Titles:
{alternate}

Reported Job Titles:
{reported}
"""

    return " ".join(text.split())


# ============================================================
# BUILD / LOAD CAREER EMBEDDINGS
# ============================================================

career_emb_path = CAREER_EMB / "onet_career_profile_embeddings.npy"
career_ids_path = CAREER_EMB / "onet_career_profile_ids.csv"


def build_career_embeddings():
    """
    Build embeddings using the COMPLETE O*NET career profile.
    """

    print("\nBuilding O*NET career profile embeddings...")

    profile_texts = []

    for _, row in career_profiles.iterrows():
        profile_texts.append(
            combine_profile_text(row)
        )

    embeddings = model.encode(
        profile_texts,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=32,
    )

    np.save(
        career_emb_path,
        embeddings,
    )

    career_profiles[
        ["onet_soc_code"]
    ].to_csv(
        career_ids_path,
        index=False,
    )

    print(
        f"Saved career embeddings: {career_emb_path}"
    )

    return embeddings


if (
    not career_emb_path.exists()
    or not career_ids_path.exists()
):

    career_embeddings = build_career_embeddings()

else:

    print("Loading existing O*NET career embeddings...")

    career_embeddings = np.load(
        career_emb_path
    )


# ============================================================
# CAREER ID ORDER
# ============================================================

career_ids_order = pd.read_csv(
    career_ids_path
)["onet_soc_code"].tolist()


career_lookup = career_profiles.set_index(
    "onet_soc_code"
)


# ============================================================
# 1. GOAL -> O*NET CAREER MATCHING
# ============================================================

def match_goal_to_occupation(
    goal_text,
    top_k=5,
):
    """
    Match learner's free-text goal against COMPLETE O*NET
    career profiles.
    """

    query_embedding = model.encode(
        [goal_text],
        normalize_embeddings=True,
    )[0]

    similarities = (
        career_embeddings @ query_embedding
    )

    top_indices = np.argsort(
        -similarities
    )[:top_k]

    results = []

    for idx in top_indices:

        soc = career_ids_order[idx]

        row = career_lookup.loc[soc]

        results.append(
            {
                "onet_soc_code": soc,
                "title": row["title"],
                "similarity": float(
                    similarities[idx]
                ),
            }
        )

    return pd.DataFrame(results)


# ============================================================
# 2. SEMANTIC ESCO SKILL INFERENCE
# ============================================================

esco_skill_ids_order = pd.read_csv(
    SKILL_EMB / "esco_skill_ids.csv"
)["skill_id"].tolist()


esco_skill_emb = np.load(
    SKILL_EMB / "esco_skill_embeddings.npy"
)


esco_skill_id_to_row = {
    sid: i
    for i, sid in enumerate(
        esco_skill_ids_order
    )
}


def infer_target_esco_skills(
    occupation_code,
    top_n=25,
):
    """
    Infer fine-grained ESCO skills from the COMPLETE
    O*NET career profile.

    Uses semantic similarity between the occupation profile
    and ESCO skill taxonomy.

    Also uses skill metadata to slightly favour:
    - digital skills
    - research skills
    - demand frequency
    - fit score
    """

    if occupation_code not in career_lookup.index:

        return pd.DataFrame(
            columns=[
                "skill_id",
                "skill_label",
                "weight",
                "source",
            ]
        )

    row = career_lookup.loc[
        occupation_code
    ]

    profile_text = combine_profile_text(
        row
    )

    profile_embedding = model.encode(
        [profile_text],
        normalize_embeddings=True,
    )[0]

    similarities = (
        esco_skill_emb @ profile_embedding
    )

    # --------------------------------------------------------
    # Base semantic similarity
    # --------------------------------------------------------

    candidate_df = skills_taxonomy[
        [
            "skill_id",
            "skill_label",
            "is_digital",
            "is_research",
            "demand_frequency",
            "avg_fit_score",
        ]
    ].copy()

    candidate_df["semantic_score"] = [
        float(
            similarities[
                esco_skill_id_to_row[sid]
            ]
        )
        if sid in esco_skill_id_to_row
        else 0.0
        for sid in candidate_df["skill_id"]
    ]

    # --------------------------------------------------------
    # Normalize demand
    # --------------------------------------------------------

    demand = pd.to_numeric(
        candidate_df["demand_frequency"],
        errors="coerce",
    ).fillna(0)

    if demand.max() > 0:

        demand_norm = (
            np.log1p(demand)
            / np.log1p(demand.max())
        )

    else:

        demand_norm = 0.0

    # --------------------------------------------------------
    # Normalize fit
    # --------------------------------------------------------

    fit = pd.to_numeric(
        candidate_df["avg_fit_score"],
        errors="coerce",
    ).fillna(0)

    fit_norm = fit / 100.0

    # --------------------------------------------------------
    # Metadata-aware score
    # --------------------------------------------------------

    digital_bonus = (
        candidate_df["is_digital"]
        .fillna(False)
        .astype(float)
        * 0.025
    )

    research_bonus = (
        candidate_df["is_research"]
        .fillna(False)
        .astype(float)
        * 0.015
    )

    candidate_df["final_score"] = (
        candidate_df["semantic_score"] * 0.82
        + demand_norm * 0.08
        + fit_norm * 0.055
        + digital_bonus
        + research_bonus
    )

    # --------------------------------------------------------
    # Remove extremely weak semantic matches
    # --------------------------------------------------------

    candidate_df = candidate_df[
        candidate_df["semantic_score"] >= 0.30
    ]

    candidate_df = candidate_df.sort_values(
        "final_score",
        ascending=False,
    )

    candidate_df["weight"] = (
        candidate_df["final_score"]
        / candidate_df["final_score"].max()
    )

    candidate_df["source"] = (
        "onet_profile_semantic_inference"
    )

    return candidate_df[
        [
            "skill_id",
            "skill_label",
            "weight",
            "source",
        ]
    ].head(top_n).reset_index(drop=True)


# ============================================================
# 3. LEARNER SKILL MATCHING
# ============================================================

def match_learner_skills(
    learner_skill_labels,
    similarity_threshold=0.72,
):
    """
    Resolve learner-provided skill names to ESCO.

    Strategy:

    1. Exact skill_label match
    2. Exact skill_alias match
    3. Embedding fuzzy match
    """

    if not learner_skill_labels:

        return set()

    known = set()

    labels_lower = (
        skills_taxonomy["skill_label"]
        .fillna("")
        .str.lower()
        .str.strip()
    )

    aliases_lower = (
        skills_taxonomy["skill_alias"]
        .fillna("")
        .str.lower()
        .str.strip()
    )

    for raw_label in learner_skill_labels:

        label = str(
            raw_label
        ).lower().strip()

        # ----------------------------------------------------
        # EXACT LABEL
        # ----------------------------------------------------

        exact = skills_taxonomy[
            labels_lower == label
        ]

        if len(exact) > 0:

            ids = exact["skill_id"].tolist()

            known.update(ids)

            print(
                f"  [exact] '{raw_label}' -> "
                f"{exact['skill_label'].tolist()}"
            )

            continue

        # ----------------------------------------------------
        # EXACT ALIAS
        # ----------------------------------------------------

        alias_match = skills_taxonomy[
            aliases_lower == label
        ]

        if len(alias_match) > 0:

            ids = alias_match[
                "skill_id"
            ].tolist()

            known.update(ids)

            print(
                f"  [alias] '{raw_label}' -> "
                f"{alias_match['skill_label'].tolist()}"
            )

            continue

        # ----------------------------------------------------
        # EMBEDDING FALLBACK
        # ----------------------------------------------------

        q_emb = model.encode(
            [raw_label],
            normalize_embeddings=True,
        )[0]

        sims = (
            q_emb @ esco_skill_emb.T
        )

        best_idx = int(
            np.argmax(sims)
        )

        best_score = float(
            sims[best_idx]
        )

        if best_score >= similarity_threshold:

            sid = esco_skill_ids_order[
                best_idx
            ]

            known.add(sid)

            skill_label = skills_lookup.loc[
                sid,
                "skill_label",
            ]

            print(
                f"  [semantic] '{raw_label}' -> "
                f"'{skill_label}' "
                f"(similarity={best_score:.3f})"
            )

        else:

            print(
                f"  [unmatched] '{raw_label}' "
                f"(best similarity={best_score:.3f})"
            )

    return known


# ============================================================
# 4. GAP ANALYSIS
# ============================================================

def gap_analysis(
    target_profile,
    learner_skill_ids,
):
    """
    Remove skills already known by learner.
    """

    if target_profile.empty:

        return target_profile.copy()

    gap = target_profile[
        ~target_profile["skill_id"].isin(
            learner_skill_ids
        )
    ].copy()

    return gap.reset_index(
        drop=True
    )


# ============================================================
# 5. COURSE RECOMMENDATION
# ============================================================

DIFFICULTY_ORDER = {
    "Beginner": 0,
    "Intermediate": 1,
    "Mixed": 1,
    "Advanced": 2,
}


def recommend_courses_for_skill(
    skill_id,
    top_n=2,
):
    """
    Recommend courses tagged with a specific ESCO skill.
    """

    matches = course_skills_by_skill.get(
        skill_id
    )

    if matches is None or len(matches) == 0:

        return pd.DataFrame()

    merged = matches.merge(
        courses,
        on="course_id",
        how="left",
    )

    # --------------------------------------------------------
    # Skill match score
    # --------------------------------------------------------

    merged["score"] = pd.to_numeric(
        merged["score"],
        errors="coerce",
    ).fillna(0)

    # --------------------------------------------------------
    # Rating
    # --------------------------------------------------------

    rating = pd.to_numeric(
        merged["rating"],
        errors="coerce",
    )

    rating_fill = (
        rating.mean()
        if rating.notna().any()
        else 3.5
    )

    merged["rating_norm"] = (
        rating.fillna(rating_fill)
        / 5.0
    )

    # --------------------------------------------------------
    # Popularity
    # --------------------------------------------------------

    enrolled = pd.to_numeric(
        merged["num_enrolled"],
        errors="coerce",
    ).fillna(0)

    popularity = np.log1p(
        enrolled
    )

    if popularity.max() > 0:

        merged["popularity_norm"] = (
            popularity
            / popularity.max()
        )

    else:

        merged["popularity_norm"] = 0

    # --------------------------------------------------------
    # Final course score
    # --------------------------------------------------------

    merged["final_rank_score"] = (
        merged["score"] * 0.50
        + merged["rating_norm"] * 0.30
        + merged["popularity_norm"] * 0.20
    )

    merged = merged.sort_values(
        "final_rank_score",
        ascending=False,
    )

    columns = [
        "course_id",
        "title",
        "source",
        "provider",
        "difficulty",
        "rating",
        "url",
        "final_rank_score",
    ]

    existing_columns = [
        c
        for c in columns
        if c in merged.columns
    ]

    return merged[
        existing_columns
    ].head(top_n).reset_index(
        drop=True
    )


# ============================================================
# 6. ROADMAP BUILDER
# ============================================================

def build_roadmap(
    goal_text,
    learner_skill_labels,
    skills_per_milestone=3,
    top_gap_skills=9,
    verbose=True,
):
    """
    Complete recommendation pipeline.
    """

    # ========================================================
    # OCCUPATION
    # ========================================================

    occ_matches = match_goal_to_occupation(
        goal_text,
        top_k=5,
    )

    if occ_matches.empty:

        raise ValueError(
            "No O*NET occupation matched the goal."
        )

    occ = occ_matches.iloc[0]

    if verbose:

        print(
            f"\nSelected target occupation: "
            f"{occ['title']}"
        )

        print(
            f"Occupation similarity: "
            f"{occ['similarity']:.4f}"
        )

    # ========================================================
    # ESCO TARGET SKILLS
    # ========================================================

    target_profile = infer_target_esco_skills(
        occ["onet_soc_code"],
        top_n=25,
    )

    if verbose:

        print(
            "\nTop target skills:"
        )

        if target_profile.empty:

            print(
                "No ESCO skills inferred."
            )

        else:

            print(
                target_profile.head(15).to_string(
                    index=False
                )
            )

    # ========================================================
    # LEARNER SKILLS
    # ========================================================

    learner_skill_ids = match_learner_skills(
        learner_skill_labels
    )

    if verbose:

        matched_labels = (
            skills_taxonomy[
                skills_taxonomy[
                    "skill_id"
                ].isin(
                    learner_skill_ids
                )
            ]["skill_label"]
            .tolist()
        )

        print(
            "\nLearner skills resolved to ESCO:"
        )

        print(
            matched_labels
        )

    # ========================================================
    # GAP
    # ========================================================

    gap = gap_analysis(
        target_profile,
        learner_skill_ids,
    ).head(
        top_gap_skills
    )

    if verbose:

        print(
            "\nTop skill gaps:"
        )

        if gap.empty:

            print(
                "No skill gaps found."
            )

        else:

            print(
                gap.to_string(
                    index=False
                )
            )

    # ========================================================
    # COURSE RECOMMENDATIONS
    # ========================================================

    roadmap_items = []

    for _, row in gap.iterrows():

        recs = recommend_courses_for_skill(
            row["skill_id"],
            top_n=2,
        )

        if recs.empty:

            if verbose:

                print(
                    f"\n[no course] "
                    f"{row['skill_label']}"
                )

            continue

        best = recs.iloc[0]

        difficulty = best.get(
            "difficulty",
            "Unknown",
        )

        if pd.isna(difficulty):

            difficulty = "Unknown"

        roadmap_items.append(
            {
                "skill_label":
                    row["skill_label"],

                "gap_weight":
                    round(
                        float(
                            row["weight"]
                        ),
                        4,
                    ),

                "course_title":
                    best["title"],

                "course_source":
                    best["source"],

                "course_difficulty":
                    difficulty,

                "course_url":
                    best.get(
                        "url",
                        "",
                    ),

                "explanation": (
                    f"This recommendation targets "
                    f"'{row['skill_label']}', which has "
                    f"a target relevance of "
                    f"{float(row['weight']):.2f}/1.0 "
                    f"for '{occ['title']}'. "
                    f"The course was selected using "
                    f"skill-match quality, learner "
                    f"relevance, rating and popularity."
                ),
            }
        )

    roadmap_df = pd.DataFrame(
        roadmap_items
    )

    if roadmap_df.empty:

        return occ, roadmap_df

    # ========================================================
    # MILESTONE ORDER
    # ========================================================

    roadmap_df["diff_rank"] = (
        roadmap_df[
            "course_difficulty"
        ]
        .map(DIFFICULTY_ORDER)
        .fillna(1)
    )

    roadmap_df = roadmap_df.sort_values(
        [
            "diff_rank",
            "gap_weight",
        ],
        ascending=[
            True,
            False,
        ],
        kind="stable",
    ).reset_index(
        drop=True
    )

    roadmap_df["milestone"] = (
        roadmap_df.index
        // skills_per_milestone
    ) + 1

    return occ, roadmap_df


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":

    goal = (
        "I want to become a data scientist "
        "working with machine learning"
    )

    known_skills = [
        "computer programming",
        "mathematics",
    ]

    print(
        "\n"
        + "=" * 80
    )

    print(
        "GOAL:",
        goal,
    )

    print(
        "KNOWN SKILLS:",
        known_skills,
    )

    print(
        "=" * 80
    )

    # --------------------------------------------------------
    # Occupation matching
    # --------------------------------------------------------

    print(
        "\nTop occupation matches:"
    )

    occupation_matches = (
        match_goal_to_occupation(
            goal,
            top_k=5,
        )
    )

    print(
        occupation_matches[
            [
                "title",
                "similarity",
            ]
        ].to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Full pipeline
    # --------------------------------------------------------

    occ, roadmap = build_roadmap(
        goal,
        known_skills,
        skills_per_milestone=3,
        top_gap_skills=9,
        verbose=True,
    )

    print(
        "\n"
        + "=" * 80
    )

    print(
        "PERSONALIZED LEARNING ROADMAP"
    )

    print(
        "=" * 80
    )

    print(
        f"\nTarget career: "
        f"{occ['title']}"
    )

    print(
        f"Confidence: "
        f"{float(occ['similarity']):.3f}"
    )

    if roadmap.empty:

        print(
            "\nNo course recommendations found."
        )

    else:

        for milestone, group in roadmap.groupby(
            "milestone"
        ):

            print(
                f"\n--- MILESTONE {milestone} ---"
            )

            for _, row in group.iterrows():

                print(
                    f"\nSkill: "
                    f"{row['skill_label']}"
                )

                print(
                    f"Course: "
                    f"{row['course_title']}"
                )

                print(
                    f"Source: "
                    f"{row['course_source']}"
                )

                print(
                    f"Difficulty: "
                    f"{row['course_difficulty']}"
                )

                print(
                    f"Skill relevance: "
                    f"{row['gap_weight']}"
                )

                print(
                    f"Why: "
                    f"{row['explanation']}"
                )

    print(
        "\n"
        + "=" * 80
    )

    print(
        "ENGINE COMPLETE"
    )

    print(
        "=" * 80
    )