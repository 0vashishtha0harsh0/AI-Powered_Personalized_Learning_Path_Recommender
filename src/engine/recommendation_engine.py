"""
STEP 5: PERSONALIZED LEARNING PATH RECOMMENDATION ENGINE

Pipeline:

    Learner Goal
        ↓
    Goal -> O*NET Occupation
        ↓
    Target occupation is NEVER discarded merely because one
    skill-data source is missing.
        ↓
    O*NET Skill Profile
        ↓
    ESCO Skill Profile
        ↓
    If O*NET skill survey is unavailable:
        occupation text -> ESCO semantic skill inference
        ↓
    Goal-specific ESCO skill extraction
        ↓
    Learner Known Skills
        ↓
    Weighted Skill Gap
        ↓
    Course -> Skill matching
        ↓
    Course ranking
        ↓
    Diversity / duplicate control
        ↓
    Milestone roadmap
        ↓
    Explainable recommendations

This version is intentionally data-driven.
It does NOT hardcode:
    Data Scientist -> Python
    Data Scientist -> SQL
    etc.

Instead, skills are derived from:
    O*NET
    ESCO
    occupation descriptions
    learner goal
    course skill mappings
"""

import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


# ============================================================
# PROJECT PATHS
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
# CONFIGURATION
# ============================================================

MODEL_NAME = "all-mpnet-base-v2"

# Goal -> occupation
DEFAULT_TOP_OCCUPATIONS = 5

# Goal/occupation -> ESCO skill semantic matching
GOAL_SKILL_THRESHOLD = 0.38
OCCUPATION_SKILL_THRESHOLD = 0.30

# Learner known skill matching is deliberately stricter.
LEARNER_SKILL_THRESHOLD = 0.72

# O*NET -> ESCO crosswalk
CROSSWALK_THRESHOLD = 0.35

# Maximum number of target skills
DEFAULT_TARGET_SKILLS = 30

# Number of final roadmap gaps
DEFAULT_TOP_GAPS = 12

# Courses per skill before final ranking
COURSES_PER_SKILL = 5


# ============================================================
# LOAD DATA
# ============================================================

print("Loading data...")

occupations = pd.read_csv(
    CAREER_DATA / "occupations.csv"
)

occ_scores = pd.read_csv(
    CAREER_DATA / "occupation_element_scores.csv"
)

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
# NORMALIZE BASIC DATA TYPES
# ============================================================

for df in [
    occupations,
    occ_scores,
    crosswalk,
    skills_taxonomy,
    course_skills,
    courses,
]:
    df.columns = [str(c).strip() for c in df.columns]


# ============================================================
# SENTENCE TRANSFORMER
# ============================================================

print("Loading embedding model...")

model = SentenceTransformer(MODEL_NAME)


# ============================================================
# OCCUPATION EMBEDDINGS
# ============================================================

occ_emb_path = CAREER_EMB / "occupation_embeddings.npy"
occ_ids_path = CAREER_EMB / "occupation_ids.csv"


if not occ_emb_path.exists():

    print("Building occupation embeddings (one-time)...")

    occ_text = (
        occupations["title"].fillna("").astype(str)
        + ": "
        + occupations["description"].fillna("").astype(str)
    ).tolist()

    occ_emb = model.encode(
        occ_text,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    np.save(occ_emb_path, occ_emb)

    occupations[["onet_soc_code"]].to_csv(
        occ_ids_path,
        index=False
    )

else:

    occ_emb = np.load(occ_emb_path)


occ_ids_order = pd.read_csv(
    occ_ids_path
)["onet_soc_code"].tolist()

occ_lookup = occupations.set_index("onet_soc_code")


# ============================================================
# ESCO SKILL EMBEDDINGS
# ============================================================

esco_skill_ids_order = pd.read_csv(
    SKILL_EMB / "esco_skill_ids.csv"
)["skill_id"].tolist()

esco_skill_emb = np.load(
    SKILL_EMB / "esco_skill_embeddings.npy"
)

esco_skill_id_to_row = {
    sid: i
    for i, sid in enumerate(esco_skill_ids_order)
}

skills_lookup = skills_taxonomy.set_index("skill_id")


# ============================================================
# PRE-GROUP DATA
# ============================================================

crosswalk_by_element = {
    eid: grp
    for eid, grp in crosswalk.groupby("onet_element_id")
}

course_skills_by_skill = {
    sid: grp
    for sid, grp in course_skills.groupby("skill_id")
}

courses_lookup = courses.set_index("course_id")


# ============================================================
# O*NET DISTINCTIVENESS BASELINE
# ============================================================

element_baseline = (
    occ_scores
    .dropna(subset=["importance"])
    .groupby("element_id", as_index=False)["importance"]
    .mean()
    .rename(
        columns={
            "importance": "baseline_importance"
        }
    )
)

occ_scores = occ_scores.merge(
    element_baseline,
    on="element_id",
    how="left"
)


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):
    """
    Lightweight normalization for comparison only.
    Original text is never modified in the datasets.
    """

    if pd.isna(text):
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# SKILL LABEL LOOKUP
# ============================================================

def get_skill_label(skill_id):
    row = skills_lookup.loc[skill_id]

    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]

    return row["skill_label"]


# ============================================================
# SEMANTIC SKILL MATCHING
# ============================================================

def semantic_skill_search(
    text,
    top_n=20,
    threshold=0.35
):
    """
    Maps free text to ESCO skills using semantic embeddings.

    Returns:
        skill_id
        skill_label
        similarity
    """

    if not text:
        return pd.DataFrame(
            columns=[
                "skill_id",
                "skill_label",
                "similarity"
            ]
        )

    query_embedding = model.encode(
        [text],
        normalize_embeddings=True
    )[0]

    similarities = (
        esco_skill_emb @ query_embedding
    )

    top_indices = np.argsort(
        -similarities
    )[:top_n]

    rows = []

    for idx in top_indices:

        similarity = float(
            similarities[idx]
        )

        if similarity < threshold:
            continue

        skill_id = esco_skill_ids_order[idx]

        rows.append(
            {
                "skill_id": skill_id,
                "skill_label": get_skill_label(skill_id),
                "similarity": similarity
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 1. GOAL -> OCCUPATION
# ============================================================

def match_goal_to_occupation(
    goal_text,
    top_k=DEFAULT_TOP_OCCUPATIONS
):
    """
    Maps learner's free-text goal to O*NET occupations.

    IMPORTANT:
    Occupation relevance is independent from availability
    of O*NET survey data.
    """

    query_embedding = model.encode(
        [goal_text],
        normalize_embeddings=True
    )[0]

    similarities = (
        occ_emb @ query_embedding
    )

    top_indices = np.argsort(
        -similarities
    )[:top_k]

    results = []

    for idx in top_indices:

        soc = occ_ids_order[idx]

        results.append(
            {
                "onet_soc_code": soc,
                "title": occ_lookup.loc[
                    soc,
                    "title"
                ],
                "similarity": float(
                    similarities[idx]
                )
            }
        )

    return pd.DataFrame(results)


# ============================================================
# 2. O*NET -> ESCO SKILL PROFILE
# ============================================================

def get_onet_skill_profile(
    onet_soc_code,
    min_crosswalk_similarity=CROSSWALK_THRESHOLD,
    top_n=DEFAULT_TARGET_SKILLS,
    verbose=False
):
    """
    Converts O*NET occupation element scores to ESCO skills.

    Returns empty DataFrame when no O*NET survey rows exist.
    The caller decides whether to use a semantic fallback.
    """

    empty = pd.DataFrame(
        columns=[
            "skill_id",
            "weight",
            "skill_label",
            "source"
        ]
    )

    occ_rows = (
        occ_scores[
            occ_scores["onet_soc_code"]
            == onet_soc_code
        ]
        .dropna(subset=["importance"])
    )

    if verbose:
        print(
            f"    [debug] O*NET rows for "
            f"{onet_soc_code}: {len(occ_rows)}"
        )

    if len(occ_rows) == 0:
        return empty

    skill_weight = {}

    for _, row in occ_rows.iterrows():

        imp_norm = (
            row["importance"] / 5.0
        )

        lvl_norm = (
            row["level"] / 7.0
            if pd.notna(row["level"])
            else 0.5
        )

        baseline = (
            row["baseline_importance"]
            if pd.notna(row["baseline_importance"])
            else row["importance"]
        )

        distinctiveness_norm = max(
            row["importance"] - baseline,
            0
        ) / 5.0

        element_weight = (
            imp_norm * 0.25
            + lvl_norm * 0.25
            + distinctiveness_norm * 0.50
        )

        matches = crosswalk_by_element.get(
            row["element_id"]
        )

        if matches is None:
            continue

        confident_matches = matches[
            matches["similarity"]
            >= min_crosswalk_similarity
        ]

        for _, match in confident_matches.iterrows():

            sid = match["esco_skill_id"]

            contribution = (
                element_weight
                * match["similarity"]
            )

            skill_weight[sid] = (
                skill_weight.get(sid, 0)
                + contribution
            )

    if not skill_weight:
        return empty

    profile = pd.DataFrame(
        [
            {
                "skill_id": skill_id,
                "weight": weight
            }
            for skill_id, weight
            in skill_weight.items()
        ]
    )

    profile = profile.sort_values(
        "weight",
        ascending=False
    )

    profile = profile.merge(
        skills_taxonomy[
            ["skill_id", "skill_label"]
        ],
        on="skill_id",
        how="left"
    )

    profile["weight"] = (
        profile["weight"]
        / profile["weight"].max()
    )

    profile["source"] = "onet_crosswalk"

    return profile.head(
        top_n
    ).reset_index(drop=True)


# ============================================================
# 3. SEMANTIC OCCUPATION -> ESCO FALLBACK
# ============================================================

def get_semantic_occupation_skill_profile(
    onet_soc_code,
    top_n=DEFAULT_TARGET_SKILLS,
    threshold=OCCUPATION_SKILL_THRESHOLD,
    verbose=False
):
    """
    Fallback when O*NET survey data is unavailable.

    IMPORTANT:
    We do NOT switch to another occupation.

    Instead we keep the original target occupation and infer
    ESCO skills from its own title + description.
    """

    empty = pd.DataFrame(
        columns=[
            "skill_id",
            "weight",
            "skill_label",
            "source"
        ]
    )

    if onet_soc_code not in occ_lookup.index:
        return empty

    occupation = occ_lookup.loc[
        onet_soc_code
    ]

    occupation_text = (
        str(occupation.get("title", ""))
        + ". "
        + str(occupation.get("description", ""))
    )

    matches = semantic_skill_search(
        occupation_text,
        top_n=top_n,
        threshold=threshold
    )

    if len(matches) == 0:
        return empty

    matches = matches.rename(
        columns={
            "similarity": "weight"
        }
    )

    matches["source"] = (
        "occupation_semantic_inference"
    )

    # Normalize to 0-1
    matches["weight"] = (
        matches["weight"]
        / matches["weight"].max()
    )

    if verbose:
        print(
            "    [fallback] inferred ESCO skills:"
        )

        print(
            matches[
                [
                    "skill_label",
                    "weight"
                ]
            ].head(10).to_string(
                index=False
            )
        )

    return matches[
        [
            "skill_id",
            "weight",
            "skill_label",
            "source"
        ]
    ].reset_index(drop=True)


# ============================================================
# 4. GOAL -> EXPLICIT SKILLS
# ============================================================

def extract_goal_skills(
    goal_text,
    top_n=15,
    threshold=GOAL_SKILL_THRESHOLD
):
    """
    Extracts skills explicitly implied by the learner's goal.

    This prevents generic occupational skills from drowning out
    the actual intent of the learner.

    Example:

        "I want to become a data scientist working with machine learning"

    can semantically surface skills related to:
        data science
        machine learning
        statistics
        programming
        etc.

    No skill is hardcoded.
    """

    matches = semantic_skill_search(
        goal_text,
        top_n=top_n,
        threshold=threshold
    )

    if len(matches) == 0:
        return matches

    matches = matches.rename(
        columns={
            "similarity": "goal_similarity"
        }
    )

    return matches


# ============================================================
# 5. COMBINE OCCUPATION + GOAL SKILLS
# ============================================================

def get_target_skill_profile(
    onet_soc_code,
    goal_text=None,
    min_crosswalk_similarity=CROSSWALK_THRESHOLD,
    top_n=DEFAULT_TARGET_SKILLS,
    verbose=False
):
    """
    Main target skill profile builder.

    Priority:

        1. O*NET -> ESCO crosswalk
        2. If unavailable, semantic occupation -> ESCO
        3. Goal-specific skills are merged and boosted

    The occupation itself is NEVER replaced merely because
    O*NET skill survey rows are missing.
    """

    onet_profile = get_onet_skill_profile(
        onet_soc_code,
        min_crosswalk_similarity,
        top_n=top_n,
        verbose=verbose
    )

    if len(onet_profile) == 0:

        if verbose:
            print(
                "    [info] No O*NET skill-survey data."
            )

            print(
                "    [info] Keeping occupation and "
                "using semantic ESCO skill inference."
            )

        profile = get_semantic_occupation_skill_profile(
            onet_soc_code,
            top_n=top_n,
            verbose=verbose
        )

    else:

        profile = onet_profile.copy()

    # --------------------------------------------------------
    # Add goal-specific skill signal
    # --------------------------------------------------------

    if goal_text:

        goal_skills = extract_goal_skills(
            goal_text
        )

        if len(goal_skills) > 0:

            if len(profile) == 0:

                profile = goal_skills.rename(
                    columns={
                        "goal_similarity": "weight"
                    }
                )

                profile["source"] = (
                    "goal_semantic_inference"
                )

            else:

                profile = profile.merge(
                    goal_skills[
                        [
                            "skill_id",
                            "goal_similarity"
                        ]
                    ],
                    on="skill_id",
                    how="outer"
                )

                profile["weight"] = (
                    profile["weight"]
                    .fillna(0)
                )

                profile["goal_similarity"] = (
                    profile["goal_similarity"]
                    .fillna(0)
                )

                # Goal-specific relevance is deliberately
                # strong, because this is a personalized
                # recommendation system.
                profile["weight"] = (
                    profile["weight"] * 0.70
                    + profile["goal_similarity"] * 0.30
                )

                profile["source"] = (
                    profile["source"]
                    .fillna("goal_semantic_inference")
                )

    if len(profile) == 0:
        return pd.DataFrame(
            columns=[
                "skill_id",
                "weight",
                "skill_label",
                "source"
            ]
        )

    profile["weight"] = (
        profile["weight"]
        / profile["weight"].max()
    )

    return (
        profile
        .sort_values(
            "weight",
            ascending=False
        )
        .head(top_n)
        .reset_index(drop=True)
    )


# ============================================================
# 6. LEARNER SKILL MATCHING
# ============================================================

def match_learner_skills(
    learner_skill_labels,
    similarity_threshold=LEARNER_SKILL_THRESHOLD
):
    """
    Matches learner's known skills to ESCO.

    Returns a set of skill IDs.
    """

    if not learner_skill_labels:
        return set()

    query_embeddings = model.encode(
        learner_skill_labels,
        normalize_embeddings=True
    )

    similarities = (
        query_embeddings
        @ esco_skill_emb.T
    )

    known = set()

    for i, label in enumerate(
        learner_skill_labels
    ):

        best_j = int(
            np.argmax(similarities[i])
        )

        best_similarity = float(
            similarities[i][best_j]
        )

        if (
            best_similarity
            >= similarity_threshold
        ):

            known.add(
                esco_skill_ids_order[best_j]
            )

    return known


# ============================================================
# 7. GAP ANALYSIS
# ============================================================

def gap_analysis(
    target_profile,
    learner_skill_ids
):
    """
    Removes skills already known by learner.
    """

    if len(target_profile) == 0:
        return target_profile.copy()

    gap = target_profile[
        ~target_profile["skill_id"]
        .isin(learner_skill_ids)
    ].copy()

    return (
        gap
        .sort_values(
            "weight",
            ascending=False
        )
        .reset_index(drop=True)
    )


# ============================================================
# 8. COURSE QUALITY SCORE
# ============================================================

def calculate_course_quality(
    df
):
    """
    Calculates normalized quality signals.

    Uses:
        skill matching score
        rating
        popularity
    """

    df = df.copy()

    # --------------------------------------------------------
    # Rating
    # --------------------------------------------------------

    df["rating"] = pd.to_numeric(
        df["rating"],
        errors="coerce"
    )

    rating_mean = (
        df["rating"].mean()
        if df["rating"].notna().any()
        else 3.5
    )

    df["rating_norm"] = (
        df["rating"]
        .fillna(rating_mean)
        .clip(0, 5)
        / 5.0
    )

    # --------------------------------------------------------
    # Popularity
    # --------------------------------------------------------

    df["num_enrolled"] = pd.to_numeric(
        df["num_enrolled"],
        errors="coerce"
    ).fillna(0)

    df["popularity_log"] = np.log1p(
        df["num_enrolled"]
    )

    max_popularity = (
        df["popularity_log"].max()
    )

    if max_popularity > 0:

        df["popularity_norm"] = (
            df["popularity_log"]
            / max_popularity
        )

    else:

        df["popularity_norm"] = 0

    # --------------------------------------------------------
    # Final course quality
    # --------------------------------------------------------

    df["quality_score"] = (
        df["rating_norm"] * 0.65
        + df["popularity_norm"] * 0.35
    )

    return df


# ============================================================
# 9. COURSE RECOMMENDATION PER SKILL
# ============================================================

def recommend_courses_for_skill(
    skill_id,
    target_skill_weight=1.0,
    top_n=COURSES_PER_SKILL
):
    """
    Finds courses teaching a specific skill.
    """

    matches = course_skills_by_skill.get(
        skill_id
    )

    if (
        matches is None
        or len(matches) == 0
    ):
        return pd.DataFrame()

    merged = matches.merge(
        courses,
        on="course_id",
        how="left"
    )

    if len(merged) == 0:
        return pd.DataFrame()

    merged = calculate_course_quality(
        merged
    )

    # Skill score from course_skills
    merged["score"] = pd.to_numeric(
        merged["score"],
        errors="coerce"
    ).fillna(0)

    # Normalize course skill score
    max_score = merged["score"].max()

    if max_score > 0:

        merged["skill_match_norm"] = (
            merged["score"]
            / max_score
        )

    else:

        merged["skill_match_norm"] = 0

    # --------------------------------------------------------
    # Course final score
    # --------------------------------------------------------

    merged["final_rank_score"] = (
        merged["skill_match_norm"] * 0.55
        + merged["rating_norm"] * 0.30
        + merged["popularity_norm"] * 0.15
    )

    # Target skill importance
    merged["final_rank_score"] *= (
        0.75
        + 0.25 * target_skill_weight
    )

    merged = merged.sort_values(
        "final_rank_score",
        ascending=False
    )

    columns = [
        "course_id",
        "title",
        "source",
        "provider",
        "difficulty",
        "rating",
        "url",
        "final_rank_score"
    ]

    available_columns = [
        c for c in columns
        if c in merged.columns
    ]

    return (
        merged[
            available_columns
        ]
        .head(top_n)
        .reset_index(drop=True)
    )


# ============================================================
# 10. COURSE DIVERSITY
# ============================================================

def select_diverse_courses(
    recommendations,
    max_courses=12
):
    """
    Prevents the same course from appearing repeatedly
    for different skills.
    """

    if len(recommendations) == 0:
        return recommendations

    recommendations = (
        recommendations
        .sort_values(
            "final_rank_score",
            ascending=False
        )
        .drop_duplicates(
            subset=["course_id"]
        )
        .head(max_courses)
        .reset_index(drop=True)
    )

    return recommendations


# ============================================================
# 11. DIFFICULTY ORDER
# ============================================================

DIFFICULTY_ORDER = {
    "Beginner": 0,
    "Mixed": 1,
    "Intermediate": 1,
    "Advanced": 2
}


def difficulty_rank(value):
    if pd.isna(value):
        return 1

    return DIFFICULTY_ORDER.get(
        str(value),
        1
    )


# ============================================================
# 12. ROADMAP BUILDER
# ============================================================

def build_roadmap(
    goal_text,
    learner_skill_labels,
    skills_per_milestone=3,
    top_gap_skills=DEFAULT_TOP_GAPS,
    verbose=True
):
    """
    Complete end-to-end personalized roadmap.

    Critical behavior:

    The best occupation remains the target occupation even if
    O*NET survey data is unavailable.
    """

    # ========================================================
    # A. GOAL -> OCCUPATION
    # ========================================================

    occupation_matches = (
        match_goal_to_occupation(
            goal_text,
            top_k=DEFAULT_TOP_OCCUPATIONS
        )
    )

    if len(occupation_matches) == 0:
        raise ValueError(
            "No occupation matched the learner goal."
        )

    # IMPORTANT:
    # ALWAYS choose the semantically best occupation.
    occ = occupation_matches.iloc[0]

    if verbose:

        print(
            f"\nSelected target occupation:"
            f" {occ['title']}"
        )

        print(
            f"Occupation similarity:"
            f" {round(occ['similarity'], 4)}"
        )

    # ========================================================
    # B. TARGET SKILL PROFILE
    # ========================================================

    profile = get_target_skill_profile(
        occ["onet_soc_code"],
        goal_text=goal_text,
        top_n=30,
        verbose=verbose
    )

    if len(profile) == 0:

        raise ValueError(
            "Could not construct a target skill profile "
            f"for occupation '{occ['title']}'."
        )

    if verbose:

        print(
            "\nTop target skills:"
        )

        print(
            profile[
                [
                    "skill_label",
                    "weight",
                    "source"
                ]
            ]
            .head(15)
            .to_string(index=False)
        )

    # ========================================================
    # C. LEARNER SKILLS
    # ========================================================

    learner_skill_ids = (
        match_learner_skills(
            learner_skill_labels
        )
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
    # D. SKILL GAP
    # ========================================================

    gap = gap_analysis(
        profile,
        learner_skill_ids
    )

    gap = gap.head(
        top_gap_skills
    )

    if verbose:

        print(
            "\nTop skill gaps:"
        )

        if len(gap):

            print(
                gap[
                    [
                        "skill_label",
                        "weight",
                        "source"
                    ]
                ].to_string(
                    index=False
                )
            )

        else:

            print(
                "No skill gaps detected."
            )

    # ========================================================
    # E. COURSE RECOMMENDATIONS
    # ========================================================

    roadmap_items = []

    for _, skill_row in gap.iterrows():

        skill_id = skill_row[
            "skill_id"
        ]

        skill_weight = float(
            skill_row["weight"]
        )

        recs = recommend_courses_for_skill(
            skill_id,
            target_skill_weight=skill_weight,
            top_n=COURSES_PER_SKILL
        )

        if len(recs) == 0:

            if verbose:

                print(
                    f"    [info] No course found "
                    f"for skill: "
                    f"{skill_row['skill_label']}"
                )

            continue

        best = recs.iloc[0]

        roadmap_items.append(
            {
                "skill_id": skill_id,

                "skill_label":
                    skill_row[
                        "skill_label"
                    ],

                "gap_weight":
                    round(
                        skill_weight,
                        4
                    ),

                "skill_source":
                    skill_row[
                        "source"
                    ],

                "course_id":
                    best["course_id"],

                "course_title":
                    best["title"],

                "course_source":
                    best["source"],

                "course_provider":
                    best.get(
                        "provider",
                        None
                    ),

                "course_difficulty":
                    best.get(
                        "difficulty",
                        None
                    ),

                "course_rating":
                    best.get(
                        "rating",
                        None
                    ),

                "course_url":
                    best.get(
                        "url",
                        None
                    ),

                "course_score":
                    round(
                        float(
                            best[
                                "final_rank_score"
                            ]
                        ),
                        4
                    ),

                "explanation": (
                    f"This recommendation targets "
                    f"the skill '{skill_row['skill_label']}', "
                    f"which has a target relevance of "
                    f"{round(skill_weight, 2)}/1.0 "
                    f"for '{occ['title']}'. "
                    f"The course was selected using "
                    f"skill-match quality, learner "
                    f"relevance, rating and popularity."
                )
            }
        )

    roadmap_df = pd.DataFrame(
        roadmap_items
    )

    if len(roadmap_df) == 0:

        return occ, roadmap_df

    # ========================================================
    # F. REMOVE DUPLICATE COURSES
    # ========================================================

    roadmap_df = (
        roadmap_df
        .sort_values(
            [
                "gap_weight",
                "course_score"
            ],
            ascending=False
        )
        .drop_duplicates(
            subset=["course_id"]
        )
        .reset_index(drop=True)
    )

    # ========================================================
    # G. DIFFICULTY-AWARE ORDERING
    # ========================================================

    roadmap_df["diff_rank"] = (
        roadmap_df[
            "course_difficulty"
        ]
        .apply(
            difficulty_rank
        )
    )

    roadmap_df = (
        roadmap_df
        .sort_values(
            [
                "diff_rank",
                "gap_weight",
                "course_score"
            ],
            ascending=[
                True,
                False,
                False
            ]
        )
        .reset_index(drop=True)
    )

    # ========================================================
    # H. MILESTONES
    # ========================================================

    roadmap_df["milestone"] = (
        roadmap_df.index
        // skills_per_milestone
    ) + 1

    roadmap_df["milestone_title"] = (
        "Milestone "
        + roadmap_df[
            "milestone"
        ].astype(str)
    )

    return occ, roadmap_df


# ============================================================
# 13. HUMAN-READABLE ROADMAP
# ============================================================

def print_roadmap(
    occupation,
    roadmap
):
    """
    Pretty console output.
    """

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
        f"\nTarget career:"
        f" {occupation['title']}"
    )

    print(
        f"Confidence:"
        f" {round(occupation['similarity'], 3)}"
    )

    if len(roadmap) == 0:

        print(
            "\nNo course recommendations found."
        )

        return

    for milestone, group in (
        roadmap.groupby(
            "milestone"
        )
    ):

        print(
            f"\n--- MILESTONE {milestone} ---"
        )

        for _, row in group.iterrows():

            print(
                f"\nSkill:"
                f" {row['skill_label']}"
            )

            print(
                f"Course:"
                f" {row['course_title']}"
            )

            print(
                f"Source:"
                f" {row['course_source']}"
            )

            print(
                f"Difficulty:"
                f" {row['course_difficulty']}"
            )

            print(
                f"Skill relevance:"
                f" {row['gap_weight']}"
            )

            print(
                f"Why:"
                f" {row['explanation']}"
            )


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
        "mathematics"
    ]

    print(
        "\n"
        + "=" * 80
    )

    print(
        f"GOAL: {goal}"
    )

    print(
        f"KNOWN SKILLS: {known_skills}"
    )

    print(
        "=" * 80
    )

    # --------------------------------------------------------
    # Show occupation candidates
    # --------------------------------------------------------

    print(
        "\nTop occupation matches:"
    )

    occupation_matches = (
        match_goal_to_occupation(
            goal,
            top_k=5
        )
    )

    print(
        occupation_matches[
            [
                "title",
                "similarity"
            ]
        ].to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Build roadmap
    # --------------------------------------------------------

    occupation, roadmap = build_roadmap(
        goal_text=goal,
        learner_skill_labels=known_skills,
        skills_per_milestone=3,
        top_gap_skills=12,
        verbose=True
    )

    print_roadmap(
        occupation,
        roadmap
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