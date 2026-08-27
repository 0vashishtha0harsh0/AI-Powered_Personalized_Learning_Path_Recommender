from functools import lru_cache
import re
import pandas as pd

from fastapi import HTTPException

from src.api.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    RoadmapItem,
    TargetCareer,
)

TECHNOLOGY_EVIDENCE = {
    "sql": ("database", "query", "data base"),
    "python": ("analytical or scientific", "data analysis", "development environment"),
    "numpy": ("analytical or scientific", "data analysis"),
    "pandas": ("analytical or scientific", "data analysis"),
    "scikit-learn": ("analytical or scientific", "data mining", "data analysis"),
    "r": ("analytical or scientific", "statistical"),
    "tableau": ("business intelligence", "data analysis"),
    "power bi": ("business intelligence", "data analysis"),
}

TECHNOLOGY_SKILL_TERMS = {
    "python": ("python",),
    "numpy": ("numpy",),
    "pandas": ("pandas",),
    "scikit-learn": ("scikit-learn",),
    "sql": ("sql",),
    "javascript": ("javascript",),
    "typescript": ("typescript",),
    "docker": ("docker",),
    "git": ("version control", "file versioning"),
}

TECHNOLOGY_PROFILE_EVIDENCE = {
    "python": ("analytical or scientific", "data analysis", "development environment"),
    "numpy": ("analytical or scientific", "data analysis"),
    "pandas": ("analytical or scientific", "data analysis"),
    "scikit-learn": ("analytical or scientific", "data mining", "data analysis"),
    "sql": ("database", "query", "data base"),
    "javascript": ("web platform", "web page", "development environment"),
    "typescript": ("web platform", "development environment"),
    "docker": ("cloud-based", "application server", "operating system"),
    "git": ("file versioning", "configuration management"),
}


@lru_cache(maxsize=1)
def _load_resources():
    from src.engine.recommendation_engine import load_data

    return load_data()


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer

    try:
        return SentenceTransformer("all-mpnet-base-v2")
    except Exception as exc:
        print(f"[WARNING] Could not load embedding model; using lexical matching fallback: {exc}")
        return None


@lru_cache(maxsize=1)
def list_skills():
    """Return the learner-selectable skills from the processed ESCO taxonomy."""
    skills_taxonomy = _load_resources()[4]
    columns = set(skills_taxonomy.columns)

    # Detect ID column
    id_col = None
    for col in ["skill_id", "esco_skill_id", "id"]:
        if col in columns:
            id_col = col
            break

    # Detect label column
    label_col = None
    for col in ["skill_label", "esco_skill_label", "preferred_label", "label", "title", "name"]:
        if col in columns:
            label_col = col
            break

    if id_col is None or label_col is None:
        print(f"[WARNING] list_skills: could not detect columns. Available: {list(columns)}")
        return []

    return [
        {"id": str(row[id_col]), "label": str(row[label_col])}
        for _, row in skills_taxonomy[[id_col, label_col]]
        .dropna()
        .drop_duplicates(id_col)
        .sort_values(label_col)
        .iterrows()
    ]


def build_recommendation_response(
    occupation,
    roadmap_df,
) -> RecommendationResponse:
    """
    Convert recommendation engine output into
    the API response format.

    The recommendation engine returns:
        - occupation: pandas Series
        - roadmap_df: pandas DataFrame

    FastAPI should return:
        - RecommendationResponse
    """

    target_career = TargetCareer(
        onet_soc_code=str(
            occupation["onet_soc_code"]
        ),
        title=str(
            occupation["title"]
        ),
        similarity=float(
            occupation["similarity"]
        ),
    )

    roadmap = []

    for _, row in roadmap_df.iterrows():

        roadmap.append(
            RoadmapItem(
                milestone=int(
                    row["milestone"]
                ),
                skill_label=str(
                    row["skill_label"]
                ),
                gap_weight=float(
                    row["gap_weight"]
                ),
                course_title=str(
                    row["course_title"]
                ),
                course_source=str(
                    row["course_source"]
                ),
                course_difficulty=str(
                    row["course_difficulty"]
                ),
                course_url=str(
                    row["course_url"]
                ),
                explanation=str(
                    row["explanation"]
                ),
            )
        )

    return RecommendationResponse(
        goal="",
        current_skills=[],
        target_career=target_career,
        roadmap=roadmap,
    )


def _technology_recommendations(profile, stackoverflow_index):
    profile_text = " ".join(str(profile.get(column, "")) for column in (
        "technology_in_demand", "tools"
    ))
    profile_normalized = profile_text.casefold()
    technologies = []
    for technology, demand in stackoverflow_index.items():
        normalized = technology.casefold()
        evidence_terms = TECHNOLOGY_PROFILE_EVIDENCE.get(normalized, (normalized,))
        if len(normalized) < 3 or not any(term in profile_normalized for term in evidence_terms):
            continue
        technologies.append({
            "name": technology,
            "demand_score": float(demand),
            "relevance_score": round(min(1.0, 0.65 + 0.35 * float(demand)), 4),
        })
    return sorted(technologies, key=lambda item: item["relevance_score"], reverse=True)[:12]


def _augment_with_supported_technologies(target_skills, taxonomy, profile, stackoverflow_index):
    """Add only taxonomy skills evidenced by O*NET technology/tools and SO demand."""
    profile_text = " ".join(str(profile.get(column, "")) for column in (
        "technology_in_demand", "tools"
    )).casefold()
    if not profile_text:
        return target_skills
    existing = set(target_skills.get("esco_skill_id", [])) if not target_skills.empty else set()
    additions = []
    for _, row in taxonomy.iterrows():
        label = str(row.get("skill_label", "")).strip()
        normalized = label.casefold()
        if not normalized or row["skill_id"] in existing or len(normalized) < 3:
            continue
        matched_technology = next((technology for technology in stackoverflow_index
            if any(term in normalized for term in TECHNOLOGY_SKILL_TERMS.get(technology.casefold(), ())) ), None)
        if not matched_technology:
            continue
        if matched_technology.casefold() == "sql" and normalized != "sql":
            continue
        if matched_technology.casefold() == "python" and not normalized.startswith("python"):
            continue
        evidence_terms = TECHNOLOGY_PROFILE_EVIDENCE.get(matched_technology.casefold(), (matched_technology.casefold(),))
        if not any(term in profile_text for term in evidence_terms) and normalized not in profile_text:
            continue
        demand = float(stackoverflow_index[matched_technology])
        additions.append({
            "esco_skill_id": str(row["skill_id"]),
            "esco_skill_label": label,
            "esco_score": 2.0 + demand,
            "similarity": 1.0,
            "mapping_confidence": 1.0,
            "importance": 4.0,
            "level": 4.0,
            "technology_supported": True,
        })
    if additions:
            target_skills = pd.concat(
                [target_skills, pd.DataFrame(additions)], ignore_index=True
            ).drop_duplicates("esco_skill_id")
    return target_skills


def generate_recommendation(
    request: RecommendationRequest,
) -> RecommendationResponse:
    """Run the same recommendation pipeline used by the CLI engine."""
    try:
        from src.engine.recommendation_engine import (
            TOP_TARGET_SKILLS,
            build_skill_indexes,
            calculate_skill_gaps,
            find_occupation_matches,
            infer_esco_skills,
            prepare_stackoverflow,
            recommend_courses,
            resolve_learner_skills,
            build_roadmap,
            safe_float,
        )

        (
            occupations,
            occupation_scores,
            _career_profiles,
            crosswalk,
            skills_taxonomy,
            _onet_elements,
            courses,
            course_skills,
            stackoverflow,
        ) = _load_resources()
        stackoverflow_index = prepare_stackoverflow(stackoverflow)
        matches = find_occupation_matches(request.goal, occupations, _load_model())
        if matches.empty:
            raise ValueError("No target careers were found for this goal.")

        selected = matches.iloc[0]
        selected_profile = _career_profiles[
            _career_profiles["onet_soc_code"].astype(str).str.strip().str.lower()
            == str(selected["onet_soc_code"]).strip().lower()
        ]
        profile = selected_profile.iloc[0].to_dict() if not selected_profile.empty else {}
        target_skills = infer_esco_skills(
            selected["onet_soc_code"], occupation_scores, crosswalk, TOP_TARGET_SKILLS
        )
        target_skills = _augment_with_supported_technologies(
            target_skills, skills_taxonomy, profile, stackoverflow_index
        )
        indexes = build_skill_indexes(skills_taxonomy)
        learner_ids, _ = resolve_learner_skills(
            request.current_skills + request.learner_skill_ids, indexes
        )
        gaps = calculate_skill_gaps(target_skills, learner_ids, stackoverflow_index)
        course_recommendations = recommend_courses(
            gaps, courses, course_skills, skills_taxonomy, stackoverflow_index
        )

        roadmap = []
        gap_records = gaps.to_dict("records") if not gaps.empty else []
        for item in build_roadmap(gaps, course_recommendations):
            gap = next(
                record for record in gap_records
                if str(record.get("skill", "")).casefold() == str(item["skill"]).casefold()
            )
            skill = str(gap["skill"])
            skill_courses = [
                course for course in course_recommendations
                if str(course.get("skill", "")).casefold() == skill.casefold()
            ]
            course = skill_courses[0] if skill_courses else {}
            recommended_courses = [
                {
                    "title": str(item.get("title", "")),
                    "source": str(item.get("source", item.get("category", ""))),
                    "difficulty": str(item.get("difficulty", "Not specified")),
                    "url": str(item.get("url", "")),
                    "score": safe_float(item.get("course_score")),
                }
                for item in skill_courses[:3]
            ]
            roadmap.append(
                RoadmapItem(
                    milestone=int(item["milestone"]),
                    skill_label=skill,
                    gap_weight=safe_float(gap.get("priority_score")),
                    course_title=str(course.get("title", "Explore this skill")),
                    course_source=str(course.get("source", course.get("category", ""))),
                    course_difficulty=str(course.get("difficulty", "Not specified")),
                    course_url=str(course.get("url", "")),
                    explanation=str(item.get("why_required", "Required by the target occupation.")),
                    recommended_courses=recommended_courses,
                    prerequisites=item.get("prerequisites", []),
                )
            )

        return RecommendationResponse(
            goal=request.goal,
            current_skills=request.current_skills,
            target_career=TargetCareer(
                onet_soc_code=str(selected["onet_soc_code"]),
                title=str(selected["title"]),
                similarity=safe_float(selected["similarity"]),
                confidence=safe_float(selected.get("career_confidence", selected["similarity"])),
            ),
            skill_gaps=[
                {
                    "skill_id": str(record.get("esco_skill_id", "")),
                    "skill": str(record.get("skill", "")),
                    "gap_score": safe_float(record.get("priority_score")),
                    "priority": "high" if safe_float(record.get("priority_score")) >= 0.65 else "medium",
                    "reason": str(record.get("reason", "Required by the target occupation.")),
                }
                for record in gap_records
            ],
            technologies=_technology_recommendations(profile, stackoverflow_index),
            roadmap=roadmap,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Recommendation service unavailable: {exc}",
        ) from exc
