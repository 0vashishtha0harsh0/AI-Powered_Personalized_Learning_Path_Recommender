import pandas as pd
import numpy as np
from pathlib import Path
import re
import warnings
from functools import lru_cache

warnings.filterwarnings("ignore")


# =============================================================================
# PROJECT PATHS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "Data"
PROCESSED_DIR = DATA_DIR / "processed"

CAREERS_DIR = PROCESSED_DIR / "careers"
SKILLS_DIR = PROCESSED_DIR / "skills"
COURSES_DIR = PROCESSED_DIR / "courses"

OCCUPATIONS_PATH = CAREERS_DIR / "occupations.csv"
OCCUPATION_SCORES_PATH = (
    CAREERS_DIR / "occupation_element_scores.csv"
)
CAREER_PROFILES_PATH = (
    CAREERS_DIR / "onet_career_profiles.csv"
)

CROSSWALK_PATH = (
    SKILLS_DIR / "esco_onet_crosswalk.csv"
)

SKILLS_TAXONOMY_PATH = (
    SKILLS_DIR / "skills_taxonomy.csv"
)

ONET_ELEMENTS_PATH = (
    SKILLS_DIR / "onet_elements.csv"
)

COURSES_PATH = (
    COURSES_DIR / "unified_courses.csv"
)

COURSE_SKILLS_PATH = (
    COURSES_DIR / "course_skills.csv"
)

STACKOVERFLOW_PATH = (
    PROCESSED_DIR / "stackoverflow_skill_demand.csv"
)


# =============================================================================
# CONFIGURATION
# =============================================================================

TOP_OCCUPATIONS = 5
TOP_TARGET_SKILLS = 15
TOP_SKILL_GAPS = 10
TOP_COURSES_PER_SKILL = 3

# Minimum confidence for O*NET -> ESCO crosswalk
CROSSWALK_MIN_SIMILARITY = 0.40

# Stack Overflow influence
STACKOVERFLOW_WEIGHT = 0.20

# Course ranking
COURSE_SKILL_WEIGHT = 0.65
COURSE_TEXT_WEIGHT = 0.20
COURSE_POPULARITY_WEIGHT = 0.10
COURSE_RATING_WEIGHT = 0.05
COURSE_DIFFICULTY_WEIGHT = 0.05
COURSE_TECHNOLOGY_WEIGHT = 0.05

GENERIC_LEARNING_LABEL_PATTERNS = (
    r"^working with computers$",
    r"^keep time accurately$",
    r"^operate digital hardware$",
    r"^communicate verbal instructions$",
    r"maintain(?:ing)? electrical",
    r"^engineering and engineering trades$",
    r"^communication$",
    r"^communicating$",
    r"^communicating with",
    r"^interact verbally",
    r"^use communication techniques$",
    r"^writing and composing$",
    r"^geometry$",
    r"^making decisions$",
    r"^interact with an audience$",
    r"^time management$",
    r"^judgment and decision making$",
    r"^social and communication",
)


# =============================================================================
# HELPERS
# =============================================================================

def normalize_text(value):
    """
    Normalize text for robust matching.
    """

    if pd.isna(value):
        return ""

    value = str(value).strip().lower()

    value = re.sub(r"\s+", " ", value)

    return value


def normalize_id(value):
    """
    Normalize IDs such as:
        2.A.1.e
        2.A.1.E
        15-2051.00
    """

    if pd.isna(value):
        return ""

    return str(value).strip().lower()


def occupation_code_variants(value):
    """Return comparable O*NET SOC forms without assuming an occupation."""
    code = normalize_id(value)
    if not code:
        return set()
    parent = code.rsplit(".", 1)[0] if "." in code else code
    return {code, code.replace("-", "").replace(".", ""), parent, parent.replace("-", "")}


def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default

        return float(value)

    except Exception:
        return default


def split_multi_value(value):
    """
    StackOverflow/course fields use ';' separated values.
    """

    if pd.isna(value):
        return []

    return [
        x.strip()
        for x in str(value).split(";")
        if x.strip()
    ]


def unique_preserve_order(items):
    seen = set()
    result = []

    for item in items:

        key = normalize_text(item)

        if not key:
            continue

        if key not in seen:

            seen.add(key)
            result.append(item)

    return result


def is_learning_relevant_skill(label):
    normalized = normalize_text(label)
    return bool(normalized) and not any(
        re.search(pattern, normalized) for pattern in GENERIC_LEARNING_LABEL_PATTERNS
    )


# =============================================================================
# FILE CHECK
# =============================================================================

def check_files():

    print("\nChecking project files...")

    files = {
        "occupations": OCCUPATIONS_PATH,
        "occupation_element_scores": OCCUPATION_SCORES_PATH,
        "career_profiles": CAREER_PROFILES_PATH,
        "crosswalk": CROSSWALK_PATH,
        "skills_taxonomy": SKILLS_TAXONOMY_PATH,
        "onet_elements": ONET_ELEMENTS_PATH,
        "courses": COURSES_PATH,
        "course_skills": COURSE_SKILLS_PATH,
        "stackoverflow": STACKOVERFLOW_PATH,
    }

    for name, path in files.items():

        if path.exists():

            print(f"  [OK] {name}: {path}")

        else:

            print(f"  [MISSING] {name}: {path}")

    print()


# =============================================================================
# LOAD DATA
# =============================================================================

def load_data():

    print("Loading data...\n")

    check_files()

    occupations = pd.read_csv(
        OCCUPATIONS_PATH
    )

    occupation_scores = pd.read_csv(
        OCCUPATION_SCORES_PATH
    )

    career_profiles = pd.read_csv(
        CAREER_PROFILES_PATH
    )

    crosswalk = pd.read_csv(
        CROSSWALK_PATH
    )

    skills_taxonomy = pd.read_csv(
        SKILLS_TAXONOMY_PATH
    )

    onet_elements = pd.read_csv(
        ONET_ELEMENTS_PATH
    )

    courses = pd.read_csv(
        COURSES_PATH
    )

    course_skills = pd.read_csv(
        COURSE_SKILLS_PATH
    )

    stackoverflow = pd.read_csv(
        STACKOVERFLOW_PATH
    )

    print(
        f"Loaded Stack Overflow demand: "
        f"{stackoverflow.shape}"
    )

    print(
        f"Loaded O*NET career profiles: "
        f"{career_profiles.shape}"
    )

    print(
        f"Loaded occupation scores: "
        f"{occupation_scores.shape}"
    )

    print(
        f"Loaded courses: "
        f"{courses.shape}"
    )

    print(
        f"Loaded course skills: "
        f"{course_skills.shape}"
    )

    return (
        occupations,
        occupation_scores,
        career_profiles,
        crosswalk,
        skills_taxonomy,
        onet_elements,
        courses,
        course_skills,
        stackoverflow,
    )


@lru_cache(maxsize=1)
def load_cached_career_embeddings():
    """Load precomputed occupation embeddings once per process."""
    embedding_path = BASE_DIR / "embeddings" / "career_embeddings" / "occupation_embeddings.npy"
    ids_path = BASE_DIR / "embeddings" / "career_embeddings" / "occupation_ids.csv"
    if not embedding_path.exists() or not ids_path.exists():
        return None, None
    embeddings = np.load(embedding_path, mmap_mode="r")
    ids = pd.read_csv(ids_path).iloc[:, 0].map(normalize_id).tolist()
    if len(ids) != len(embeddings) or len(set(ids)) != len(ids):
        print("[WARNING] Career embedding IDs do not match embedding rows; using in-memory embeddings.")
        return None, None
    return embeddings, ids


# =============================================================================
# STACK OVERFLOW
# =============================================================================

def prepare_stackoverflow(stackoverflow):

    if stackoverflow.empty:
        return {}

    required = {
        "technology",
        "demand_score",
    }

    if not required.issubset(
        set(stackoverflow.columns)
    ):
        print(
            "[WARNING] Stack Overflow demand "
            "columns not found."
        )

        return {}

    result = {}

    for _, row in stackoverflow.iterrows():

        tech = normalize_text(
            row["technology"]
        )

        if not tech:
            continue

        score = safe_float(
            row["demand_score"]
        )

        result[tech] = score

    print(
        f"Stack Overflow technologies loaded: "
        f"{len(result)}"
    )

    return result


# =============================================================================
# OCCUPATION MATCHING
# =============================================================================

def find_occupation_matches(
    goal,
    occupations,
    model,
):
    """
    Semantic matching between learner goal and occupations.
    """

    titles = (
        occupations["title"]
        .fillna("")
        .astype(str)
    )

    descriptions = (
        occupations["description"]
        .fillna("")
        .astype(str)
    )

    occupation_text = (
        titles + ". " + descriptions
    ).tolist()

    if model is None:
        similarities = lexical_occupation_similarities(goal, occupation_text)
    else:
        goal_embedding = model.encode(
            [goal],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        cached_embeddings, cached_ids = load_cached_career_embeddings()
        occupation_embeddings = None
        if cached_embeddings is not None:
            row_ids = occupations["onet_soc_code"].map(normalize_id).tolist()
            if row_ids == cached_ids:
                occupation_embeddings = cached_embeddings
        if occupation_embeddings is None:
            occupation_embeddings = model.encode(
                occupation_text,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

        similarities = (
            occupation_embeddings
            @ goal_embedding[0]
        )

    result = occupations.copy()

    result["similarity"] = similarities

    # Embeddings capture meaning, but career labels contain decisive intent.
    # Apply a bounded lexical boost so "data scientist" does not become a
    # generic software or hardware role just because descriptions overlap.
    normalized_goal = normalize_text(goal)
    goal_tokens = set(re.findall(r"[a-z0-9]+", normalized_goal))
    ai_intent = bool(
        goal_tokens.intersection(
            {"ai", "ml", "machine", "learning", "deep", "neural", "generative", "nlp"}
        )
    )

    def intent_boost(title):
        normalized_title = normalize_text(title)
        title_tokens = set(re.findall(r"[a-z0-9]+", normalized_title))
        boost = 0.0
        if normalized_title in normalized_goal or normalized_goal in normalized_title:
            boost += 0.45
        boost += min(len(goal_tokens.intersection(title_tokens)) * 0.08, 0.24)
        if ai_intent:
            if title_tokens.intersection({"data", "scientists"}) or normalized_title == "data scientists":
                boost += 0.80
            if title_tokens.intersection({"computer", "information", "research"}):
                boost += 0.65
            if title_tokens.intersection({"software", "developers"}):
                boost += 0.45
            if title_tokens.intersection({"systems", "engineers", "architects"}):
                boost += 0.25
            if title_tokens.intersection({"operators", "machine"}) and not title_tokens.intersection(
                {"computer", "software", "data", "scientists", "research"}
            ):
                boost -= 0.70
        if "engineer" in goal_tokens:
            boost += 0.10 if "engineer" in title_tokens else 0.0
            if goal_tokens.intersection({"data", "ai", "artificial", "machine"}):
                boost += 0.08 if title_tokens.intersection({"computer", "software", "scientist", "data"}) else 0.0
            if title_tokens.intersection({"mechatronics", "mechanical", "electrical"}):
                boost -= 0.18
        if goal_tokens.intersection({"developer", "backend", "software", "stack"}):
            if title_tokens.intersection({"developer", "developers", "software", "web"}):
                boost += 0.85
            elif title_tokens.intersection({"programmers", "computer"}):
                boost += 0.25
        if goal_tokens.intersection({"analyst", "analytics"}):
            analyst_title = title_tokens.intersection({"analyst", "analysts"})
            boost += 0.18 if analyst_title else 0.0
            if goal_tokens.intersection({"data", "business", "bi"}):
                boost += 0.90 if analyst_title and title_tokens.intersection({"business", "intelligence"}) else 0.0
                boost += 0.55 if analyst_title and "data" in title_tokens else 0.0
                boost += 0.35 if normalized_title == "data scientists" else 0.0
                boost -= 0.35 if title_tokens.intersection({"scientist", "scientists"}) else 0.0
                if title_tokens.intersection({"intelligence", "security", "financial", "credit", "market", "fraud"}) and not title_tokens.intersection({"business"}):
                    boost -= 0.80
        return boost

    result["similarity"] = result.apply(
        lambda row: float(row["similarity"]) + intent_boost(row["title"]),
        axis=1,
    )

    result = result.sort_values(
        "similarity",
        ascending=False,
    ).reset_index(drop=True)

    result["career_similarity"] = result["similarity"].clip(-1, 1)
    top = float(result["similarity"].iloc[0]) if not result.empty else 0.0
    second = float(result["similarity"].iloc[1]) if len(result) > 1 else top - 1.0
    margin = max(0.0, min(1.0, (top - second) / 0.5))
    result["career_confidence"] = (
        0.75 * result["career_similarity"].clip(0, 1) + 0.25 * margin
    ).clip(0, 1)

    return result


def lexical_occupation_similarities(goal, occupation_text):
    """Calculate TF-IDF cosine scores without the optional sklearn dependency."""
    from collections import Counter
    from math import log, sqrt

    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "in", "is", "of", "on", "or", "that", "the", "to", "with",
    }

    def terms(value):
        tokens = [token for token in re.findall(r"[a-z0-9]+", str(value).lower()) if token not in stop_words]
        return tokens + [f"{left} {right}" for left, right in zip(tokens, tokens[1:])]

    documents = [terms(goal)] + [terms(text) for text in occupation_text]
    document_frequency = Counter(
        term for document in documents for term in set(document)
    )
    total_documents = len(documents)

    def vector(document):
        counts = Counter(document)
        return {
            term: count * log((total_documents + 1) / (document_frequency[term] + 1))
            for term, count in counts.items()
        }

    goal_vector = vector(documents[0])
    goal_norm = sqrt(sum(value * value for value in goal_vector.values()))
    scores = []
    for document in documents[1:]:
        current = vector(document)
        current_norm = sqrt(sum(value * value for value in current.values()))
        dot_product = sum(value * current.get(term, 0.0) for term, value in goal_vector.items())
        scores.append(dot_product / (goal_norm * current_norm) if goal_norm and current_norm else 0.0)
    return np.asarray(scores, dtype=float)


# =============================================================================
# O*NET ELEMENT EXTRACTION
# =============================================================================

def get_occupation_elements(
    occupation_code,
    occupation_scores,
):
    """
    Get O*NET skills/knowledge for occupation.

    IMPORTANT:
    This deliberately does NOT rely on career_profiles.
    The source of truth is occupation_element_scores.csv.
    """

    if occupation_scores.empty:
        return pd.DataFrame()

    df = occupation_scores.copy()

    df["_occupation_code"] = (
        df["onet_soc_code"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    target_code = normalize_id(
        occupation_code
    )

    target = df[
        df["_occupation_code"]
        == target_code
    ].copy()
    resolved_codes = target["_occupation_code"].drop_duplicates().tolist()

    # -------------------------------------------------------------------------
    # Fallback: normalize codes more aggressively
    # -------------------------------------------------------------------------

    if target.empty:

        compact_target = (
            target_code
            .replace("-", "")
            .replace(".", "")
        )

        df["_compact"] = (
            df["_occupation_code"]
            .str.replace(
                "-", "",
                regex=False
            )
            .str.replace(
                ".", "",
                regex=False
            )
        )

        target = df[
            df["_compact"]
            == compact_target
        ].copy()
        resolved_codes = target["_occupation_code"].drop_duplicates().tolist()

    # -------------------------------------------------------------------------
    # Fallback: match sub-codes by prefix
    # e.g. 15-2051.00 -> 15-2051.01, 15-2051.02
    # O*NET stores ratings at sub-code level for many
    # parent/broad occupation codes.
    # -------------------------------------------------------------------------

    if target.empty:

        base_prefix = (
            target_code.rsplit(".", 1)[0]
            + "."
        )

        sub_matches = df[
            (
                df["_occupation_code"]
                .str.startswith(base_prefix)
            )
            & (
                df["_occupation_code"]
                != target_code
            )
        ].copy()

        if not sub_matches.empty:

            matched_codes = (
                sub_matches[
                    "_occupation_code"
                ]
                .unique()
            )

            print(
                f"[FALLBACK] No exact match for "
                f"{occupation_code}. "
                f"Using {len(matched_codes)} "
                f"sub-code(s): "
                f"{list(matched_codes)}"
            )

            target = sub_matches
            resolved_codes = list(matched_codes)

    # -------------------------------------------------------------------------
    # Debug
    # -------------------------------------------------------------------------

    if target.empty:

        print(
            f"[WARNING] No O*NET elements found "
            f"for occupation {occupation_code}"
        )

        available = (
            df["onet_soc_code"]
            .dropna()
            .astype(str)
            .unique()
        )

        print(
            f"Available occupation codes: "
            f"{len(available)}"
        )

        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # Keep only useful element types
    # -------------------------------------------------------------------------

    if "element_type" in target.columns:

        target["_element_type"] = (
            target["element_type"]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.strip()
        )

        target = target[target["_element_type"].isin(["skill", "knowledge"])].copy()

    # -------------------------------------------------------------------------
    # Numeric importance
    # -------------------------------------------------------------------------

    if "importance" in target.columns:

        target["importance"] = pd.to_numeric(
            target["importance"],
            errors="coerce",
        ).fillna(0)

    else:

        target["importance"] = 1.0

    if "level" in target.columns:

        target["level"] = pd.to_numeric(
            target["level"],
            errors="coerce",
        ).fillna(0)

    else:

        target["level"] = 0.0

    # -------------------------------------------------------------------------
    # Combined importance
    # -------------------------------------------------------------------------

    target["onet_weight"] = (
        target["importance"]
        * (
            0.7
            + 0.3
            * (
                target["level"]
                / max(
                    target["level"].max(),
                    1.0,
                )
            )
        )
    )

    target["resolved_occupation_codes"] = ",".join(resolved_codes)

    target = target.sort_values(
        "onet_weight",
        ascending=False,
    )

    return target


# =============================================================================
# O*NET -> ESCO MAPPING
# =============================================================================

def infer_esco_skills(
    occupation_code,
    occupation_scores,
    crosswalk,
    top_n=TOP_TARGET_SKILLS,
):
    """
    Convert O*NET occupation elements into ESCO skills.

    Mapping:
        O*NET occupation
              ↓
        O*NET elements
              ↓
        ESCO crosswalk
              ↓
        ESCO skills
    """

    print(
        f"\nInferring ESCO skills for O*NET occupation: "
        f"{occupation_code}"
    )

    elements = get_occupation_elements(
        occupation_code,
        occupation_scores,
    )

    if elements.empty:

        print(
            "[WARNING] Could not extract "
            "O*NET occupation elements."
        )

        return pd.DataFrame()

    print(
        f"Found {len(elements)} O*NET elements."
    )

    # -------------------------------------------------------------------------
    # Normalize crosswalk
    # -------------------------------------------------------------------------

    cw = crosswalk.copy()

    cw["_onet_id"] = (
        cw["onet_element_id"]
        .apply(normalize_id)
    )

    cw["_esco_id"] = (
        cw["esco_skill_id"]
        .apply(normalize_id)
    )

    cw["_esco_label"] = (
        cw["esco_skill_label"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    cw["similarity"] = pd.to_numeric(
        cw["similarity"],
        errors="coerce",
    ).fillna(0)

    if "confident" in cw.columns:

        cw["_confident"] = (
            cw["confident"]
            .astype(str)
            .str.lower()
            .isin(
                [
                    "true",
                    "1",
                    "yes",
                ]
            )
        )

    else:

        cw["_confident"] = False

    # -------------------------------------------------------------------------
    # Normalize O*NET IDs
    # -------------------------------------------------------------------------

    elements["_element_id"] = (
        elements["element_id"]
        .apply(normalize_id)
    )

    # -------------------------------------------------------------------------
    # Merge
    # -------------------------------------------------------------------------

    merged = elements.merge(
        cw,
        left_on="_element_id",
        right_on="_onet_id",
        how="inner",
        suffixes=(
            "_onet",
            "_crosswalk",
        ),
    )

    if merged.empty:

        print(
            "[WARNING] O*NET elements found, "
            "but no matching ESCO crosswalk entries."
        )

        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # Filter weak mappings
    # -------------------------------------------------------------------------

    merged = merged[
        merged["similarity"]
        >= max(CROSSWALK_MIN_SIMILARITY, 0.55)
    ].copy()

    if merged.empty:

        print(
            "[WARNING] All ESCO mappings "
            "were below similarity threshold."
        )

        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # Final ESCO importance
    # -------------------------------------------------------------------------

    merged["esco_score"] = (
        merged["onet_weight"]
        * merged["similarity"]
        * np.where(
            merged["_confident"],
            1.15,
            1.0,
        )
    )

    # -------------------------------------------------------------------------
    # Aggregate same ESCO skill
    # -------------------------------------------------------------------------

    grouped = (
        merged
        .groupby(
            [
                "_esco_id",
                "_esco_label",
            ],
            as_index=False,
        )
        .agg(
            {
                "esco_score": "max",
                "similarity": "max",
                "onet_weight": "max",
                "importance": "max",
                "level": "max",
                "_confident": "max",
                "_element_id": "first",
                "element_name": "first",
            }
        )
    )

    grouped = grouped.sort_values(
        "esco_score",
        ascending=False,
    )

    grouped = grouped.head(
        top_n
    ).reset_index(drop=True)

    grouped = grouped.rename(
        columns={
            "_esco_id": "esco_skill_id",
            "_esco_label": "esco_skill_label",
        }
    )

    grouped = grouped[
        grouped["esco_skill_label"].apply(is_learning_relevant_skill)
    ].copy()
    grouped["mapping_confidence"] = grouped["similarity"] * np.where(
        grouped["_confident"], 1.0, 0.85
    )
    grouped["onet_element_id"] = grouped["_element_id"]
    grouped["onet_element_name"] = grouped["element_name"]

    print(
        f"Mapped {len(grouped)} ESCO skills."
    )

    return grouped


# =============================================================================
# SKILL TAXONOMY INDEX
# =============================================================================

def build_skill_indexes(
    skills_taxonomy
):
    """
    Build multiple indexes for resolving learner skills.
    """

    indexes = {
        "id_to_label": {},
        "label_to_ids": {},
        "normalized_to_label": {},
    }

    if skills_taxonomy.empty:
        return indexes

    columns = set(
        skills_taxonomy.columns
    )

    # -------------------------------------------------------------------------
    # Detect ID column
    # -------------------------------------------------------------------------

    id_col = None

    for col in [
        "skill_id",
        "esco_skill_id",
        "id",
    ]:
        if col in columns:
            id_col = col
            break

    # -------------------------------------------------------------------------
    # Detect label column
    # -------------------------------------------------------------------------

    label_col = None

    for col in [
        "skill_label",
        "esco_skill_label",
        "preferred_label",
        "label",
        "title",
        "name",
    ]:

        if col in columns:
            label_col = col
            break

    if id_col is None or label_col is None:

        print(
            "[WARNING] Could not identify "
            "skill taxonomy columns."
        )

        return indexes

    for _, row in skills_taxonomy.iterrows():

        skill_id = str(
            row[id_col]
        ).strip()

        label = str(
            row[label_col]
        ).strip()

        if not skill_id or not label:
            continue

        normalized = normalize_text(
            label
        )

        indexes[
            "id_to_label"
        ][skill_id] = label

        indexes[
            "label_to_ids"
        ].setdefault(
            normalized,
            []
        ).append(
            skill_id
        )

        indexes[
            "normalized_to_label"
        ][normalized] = label

    return indexes


# =============================================================================
# RESOLVE LEARNER SKILLS
# =============================================================================

def resolve_learner_skill(
    skill,
    skill_indexes,
    model=None,
    taxonomy_labels=None,
):
    """
    Resolve a learner skill to ESCO.

    Exact matching is preferred.
    """

    raw_skill = str(skill).strip()
    if raw_skill in skill_indexes["id_to_label"]:
        return [raw_skill]

    normalized = normalize_text(
        skill
    )

    if not normalized:
        return []

    # -------------------------------------------------------------------------
    # Exact taxonomy match
    # -------------------------------------------------------------------------

    exact = skill_indexes[
        "label_to_ids"
    ].get(
        normalized,
        []
    )

    if exact:

        return exact

    # -------------------------------------------------------------------------
    # Small alias dictionary
    # -------------------------------------------------------------------------

    aliases = {
        # Programming languages
        "python programming": "python",
        "python": "python",
        "java programming": "java",
        "javascript programming": "javascript",
        "javascript": "javascript",
        "typescript": "typescript",
        "typescript programming": "typescript",
        "c++ programming": "c++",
        "c programming": "c",
        "r programming": "r",
        "r language": "r",
        "rust programming": "rust",
        "golang": "go",
        "go programming": "go",
        "swift programming": "swift",
        "kotlin programming": "kotlin",
        "php programming": "php",
        "ruby programming": "ruby",
        "scala programming": "scala",
        "matlab programming": "matlab",
        "matlab": "matlab",
        "computer programming": "computer programming",
        "programming": "computer programming",

        # AI / ML
        "machine learning": "machine learning",
        "ml": "machine learning",
        "artificial intelligence": "artificial intelligence",
        "ai": "artificial intelligence",
        "deep learning": "deep learning",
        "natural language processing": "natural language processing",
        "nlp": "natural language processing",
        "computer vision": "computer vision",
        "reinforcement learning": "reinforcement learning",
        "generative ai": "generative ai",
        "generative artificial intelligence": "generative ai",
        "gen ai": "generative ai",
        "large language models": "large language models",
        "llm": "large language models",
        "neural networks": "neural networks",
        "neural network": "neural networks",
        "tensorflow": "tensorflow",
        "pytorch": "pytorch",
        "keras": "keras",
        "scikit-learn": "scikit-learn",
        "scikit learn": "scikit-learn",
        "xgboost": "xgboost",
        "transformers": "transformers",
        "hugging face": "hugging face",

        # Data
        "data science": "data science",
        "data analysis": "data analysis",
        "data analytics": "data analysis",
        "data engineering": "data engineering",
        "data visualization": "data visualization",
        "data mining": "data mining",
        "big data": "big data",
        "data processing": "data processing",
        "statistics": "statistics",
        "statistical analysis": "statistics",
        "probability": "probability",
        "linear algebra": "linear algebra",
        "math": "mathematics",
        "mathematics": "mathematics",

        # Databases
        "sql": "sql",
        "mysql": "mysql",
        "postgresql": "postgresql",
        "postgres": "postgresql",
        "mongodb": "mongodb",
        "nosql": "nosql",
        "database management": "database management",
        "database": "database management",
        "data warehousing": "data warehousing",

        # Web development
        "web development": "web development",
        "web development frameworks": "web development",
        "frontend development": "frontend development",
        "frontend": "frontend development",
        "backend development": "backend development",
        "backend": "backend development",
        "full stack development": "full stack development",
        "fullstack": "full stack development",
        "react": "react",
        "reactjs": "react",
        "react.js": "react",
        "angular": "angular",
        "vue": "vue.js",
        "vue.js": "vue.js",
        "node.js": "node.js",
        "nodejs": "node.js",
        "express.js": "express.js",
        "html": "html",
        "css": "css",
        "rest api": "rest api",
        "restful api": "rest api",
        "graphql": "graphql",
        "api development": "api development",

        # Cloud / DevOps
        "cloud computing": "cloud computing",
        "aws": "amazon web services",
        "amazon web services": "amazon web services",
        "azure": "microsoft azure",
        "microsoft azure": "microsoft azure",
        "gcp": "google cloud platform",
        "google cloud platform": "google cloud platform",
        "docker": "docker",
        "kubernetes": "kubernetes",
        "devops": "devops",
        "ci/cd": "ci/cd",
        "cicd": "ci/cd",
        "infrastructure as code": "infrastructure as code",
        "terraform": "terraform",
        "ansible": "ansible",

        # Tools
        "git": "git",
        "version control": "git",
        "github": "github",
        "linux": "linux",
        "linux administration": "linux",
        "bash": "bash",
        "shell scripting": "bash",
        "excel": "microsoft excel",
        "microsoft excel": "microsoft excel",
        "power bi": "power bi",
        "tableau": "tableau",
        "jupyter": "jupyter notebook",
        "jupyter notebook": "jupyter notebook",
        "pandas": "pandas",
        "numpy": "numpy",
        "scipy": "scipy",
        "matplotlib": "matplotlib",
        "seaborn": "seaborn",

        # Cybersecurity
        "cybersecurity": "cybersecurity",
        "information security": "information security",
        "network security": "network security",
        "penetration testing": "penetration testing",
        "ethical hacking": "ethical hacking",

        # Project / Soft
        "project management": "project management",
        "agile": "agile methodology",
        "scrum": "scrum",
        "problem solving": "problem solving",
        "critical thinking": "critical thinking",
    }

    alias = aliases.get(
        normalized
    )

    if alias:

        exact = skill_indexes[
            "label_to_ids"
        ].get(
            alias,
            []
        )

        if exact:
            return exact

    # -------------------------------------------------------------------------
    # Fuzzy/simple substring matching
    # -------------------------------------------------------------------------

    matches = []

    for label_norm, ids in skill_indexes[
        "label_to_ids"
    ].items():

        if (
            normalized in label_norm
            or label_norm in normalized
        ):

            matches.extend(ids)

    return unique_preserve_order(
        matches
    )


def resolve_learner_skills(
    known_skills,
    skill_indexes,
):
    resolved_ids = []
    resolved_labels = []

    for skill in known_skills:

        ids = resolve_learner_skill(
            skill,
            skill_indexes,
        )

        if ids:

            labels = [
                skill_indexes[
                    "id_to_label"
                ].get(
                    skill_id,
                    skill,
                )
                for skill_id in ids
            ]

            print(
                f"  [exact] '{skill}' -> "
                f"{ids}"
            )

            resolved_ids.extend(
                ids
            )

            resolved_labels.extend(
                labels
            )

        else:

            print(
                f"  [unresolved] '{skill}'"
            )

    resolved_ids = unique_preserve_order(
        resolved_ids
    )

    resolved_labels = unique_preserve_order(
        resolved_labels
    )

    return (
        resolved_ids,
        resolved_labels,
    )


# =============================================================================
# STACK OVERFLOW BOOST
# =============================================================================

def stackoverflow_score_for_skill(
    skill_label,
    stackoverflow_index,
):
    """
    Find Stack Overflow demand for a skill.

    Supports:
        exact match
        substring match
    """

    normalized = normalize_text(
        skill_label
    )

    if not normalized:
        return 0.0

    # Exact
    if normalized in stackoverflow_index:

        return stackoverflow_index[
            normalized
        ]

    # Substring
    best = 0.0

    for tech, score in stackoverflow_index.items():

        if (
            normalized in tech
            or tech in normalized
        ):

            best = max(
                best,
                score
            )

    return best


# =============================================================================
# SKILL GAP CALCULATION
# =============================================================================

def calculate_skill_gaps(
    target_skills,
    learner_skill_ids,
    stackoverflow_index,
):
    """
    Target ESCO skills - learner skills.

    Stack Overflow demand is used as an additional
    real-world technology signal.
    """

    if target_skills.empty:

        return pd.DataFrame()

    learner_set = {
        normalize_text(x)
        for x in learner_skill_ids
    }

    gaps = []

    for _, row in target_skills.iterrows():

        skill_id = str(
            row["esco_skill_id"]
        ).strip()

        label = str(
            row["esco_skill_label"]
        ).strip()

        if normalize_text(
            skill_id
        ) in learner_set:

            continue

        base_score = safe_float(
            row["esco_score"]
        )

        occupation_importance = safe_float(row.get("importance", 0.0)) / 5.0
        occupation_level = safe_float(row.get("level", 0.0)) / 7.0
        mapping_confidence = safe_float(
            row.get("mapping_confidence", row.get("similarity", 0.0))
        )

        so_score = (
            stackoverflow_score_for_skill(
                label,
                stackoverflow_index,
            )
        )

        target_score = min(1.0, base_score / 5.0)
        priority_score = (
            0.55 * target_score
            + 0.20 * occupation_importance
            + 0.10 * occupation_level
            + 0.10 * mapping_confidence
            + 0.05 * so_score
        )

        gaps.append(
            {
                "esco_skill_id":
                    skill_id,

                "skill":
                    label,

                "base_score": base_score,
                "target_score": target_score,
                "occupation_importance": occupation_importance,
                "occupation_level": occupation_level,
                "crosswalk_confidence": mapping_confidence,

                "technology_supported": bool(row.get("technology_supported", False)),

                "stackoverflow_demand":
                    so_score,

                "priority_score": priority_score,
                "reason": (
                    "Required by the selected O*NET occupation; "
                    + ("also reinforced by Stack Overflow demand." if so_score > 0 else "no additional Stack Overflow signal was found.")
                ),
            }
        )

    if not gaps:

        return pd.DataFrame()

    result = pd.DataFrame(
        gaps
    )

    result = result.sort_values(
        "priority_score",
        ascending=False,
    ).reset_index(
        drop=True
    )

    return result.head(
        TOP_SKILL_GAPS
    )


# =============================================================================
# COURSE SKILL INDEX
# =============================================================================

def prepare_course_skills(
    course_skills
):
    """
    Detect flexible column names in course_skills.csv.
    """

    df = course_skills.copy()

    columns = set(
        df.columns
    )

    course_id_col = None

    for col in [
        "course_id",
        "id",
        "courseId",
    ]:

        if col in columns:
            course_id_col = col
            break

    skill_id_col = None

    for col in [
        "skill_id",
        "esco_skill_id",
        "skillId",
    ]:

        if col in columns:
            skill_id_col = col
            break

    if (
        course_id_col is None
        or skill_id_col is None
    ):

        print(
            "[WARNING] Could not detect "
            "course_skills columns."
        )

        print(
            "Columns:",
            list(df.columns)
        )

        return None

    df["_course_id"] = (
        df[course_id_col]
        .astype(str)
        .str.strip()
    )

    df["_skill_id"] = (
        df[skill_id_col]
        .astype(str)
        .str.strip()
    )

    return df


# =============================================================================
# COURSE RECOMMENDATIONS
# =============================================================================

def recommend_courses(
    skill_gaps,
    courses,
    course_skills,
    skills_taxonomy,
    stackoverflow_index,
):
    """
    Recommend courses for skill gaps.

    Ranking:
        course-skill match
        +
        text relevance
        +
        popularity
        +
        rating
    """

    if skill_gaps.empty:
        return []

    if courses.empty:
        return []

    courses = courses.copy()

    # -------------------------------------------------------------------------
    # Detect course ID
    # -------------------------------------------------------------------------

    course_id_col = None

    for col in [
        "course_id",
        "id",
        "courseId",
    ]:

        if col in courses.columns:
            course_id_col = col
            break

    if course_id_col is None:

        # Generate stable ID
        courses["_generated_course_id"] = (
            np.arange(
                len(courses)
            ).astype(str)
        )

        course_id_col = (
            "_generated_course_id"
        )

    courses["_course_id"] = (
        courses[course_id_col]
        .astype(str)
        .str.strip()
    )

    # -------------------------------------------------------------------------
    # Numeric columns
    # -------------------------------------------------------------------------

    for col in [
        "rating",
        "num_enrolled",
        "enrollment",
        "students",
        "popularity",
    ]:

        if col in courses.columns:

            courses[
                f"_num_{col}"
            ] = pd.to_numeric(
                courses[col],
                errors="coerce",
            ).fillna(0)

    # -------------------------------------------------------------------------
    # Normalize popularity
    # -------------------------------------------------------------------------

    popularity_col = None

    for col in [
        "_num_num_enrolled",
        "_num_enrollment",
        "_num_students",
        "_num_popularity",
    ]:

        if col in courses.columns:

            popularity_col = col
            break

    if popularity_col:

        max_pop = (
            courses[popularity_col].max()
        )

        if max_pop > 0:

            courses["_pop_score"] = (
                courses[
                    popularity_col
                ]
                / max_pop
            )

        else:

            courses["_pop_score"] = 0.0

    else:

        courses["_pop_score"] = 0.0

    # -------------------------------------------------------------------------
    # Rating normalization
    # -------------------------------------------------------------------------

    if "_num_rating" in courses.columns:

        max_rating = (
            courses["_num_rating"].max()
        )

        if max_rating > 0:

            courses["_rating_score"] = (
                courses["_num_rating"]
                / max_rating
            )

        else:

            courses["_rating_score"] = 0.0

    else:

        courses["_rating_score"] = 0.0

    # -------------------------------------------------------------------------
    # Course skill mapping
    # -------------------------------------------------------------------------

    mapping = prepare_course_skills(
        course_skills
    )

    skill_to_courses = {}

    if mapping is not None:

        for _, row in mapping.iterrows():

            skill_id = normalize_text(
                row["_skill_id"]
            )

            course_id = str(
                row["_course_id"]
            ).strip()

            if not skill_id:
                continue

            link_score = safe_float(row.get("score", 0.0))
            course_scores = skill_to_courses.setdefault(skill_id, {})
            course_scores[course_id] = max(
                link_score,
                course_scores.get(course_id, 0.0),
            )

    # -------------------------------------------------------------------------
    # Course text
    # -------------------------------------------------------------------------

    title_col = (
        "title"
        if "title" in courses.columns
        else None
    )

    description_col = (
        "description"
        if "description" in courses.columns
        else None
    )

    category_col = (
        "category"
        if "category" in courses.columns
        else None
    )

    recommendations = []

    for _, gap in skill_gaps.iterrows():

        skill_id = normalize_text(
            gap["esco_skill_id"]
        )

        skill_label = str(
            gap["skill"]
        ).strip()

        priority = safe_float(
            gap["priority_score"]
        )

        matching_course_scores = (
            skill_to_courses.get(
                skill_id,
                {}
            )
        )

        # ---------------------------------------------------------------------
        # If course-skill mapping exists
        # ---------------------------------------------------------------------

        if matching_course_scores:

            candidate = courses[
                courses["_course_id"].isin(
                    matching_course_scores.keys()
                )
            ].copy()

            candidate["_skill_match"] = candidate["_course_id"].map(
                matching_course_scores
            ).fillna(0.0).clip(0, 1)
            skill_words = [
                word for word in re.findall(r"[a-zA-Z0-9+#.-]+", normalize_text(skill_label))
                if len(word) >= 3
            ]
            normalized_skill_phrase = normalize_text(skill_label)
            candidate["_text_match"] = candidate.apply(
                lambda row: (
                    1.0
                    if normalized_skill_phrase in normalize_text(" ".join(
                        str(row[col]) for col in [title_col, description_col] if col
                    ))
                    else sum(
                        bool(re.search(
                            rf"(?<![a-z]){re.escape(word)}(?![a-z])",
                            normalize_text(" ".join(
                                str(row[col]) for col in [title_col, description_col] if col
                            )),
                        ))
                        for word in skill_words
                    ) / len(skill_words)
                    if skill_words else 0.0
                ),
                axis=1,
            )
            candidate = candidate[candidate["_skill_match"] >= 0.50].copy()
            if not bool(gap.get("technology_supported", False)):
                candidate = candidate[candidate["_text_match"] >= 1.0].copy()

        else:
            # The precomputed course-skill index is authoritative. A text-only
            # fallback can turn generic words into unrelated recommendations.
            continue

        if candidate.empty:
            continue

        so_score = safe_float(gap["stackoverflow_demand"])

        # ---------------------------------------------------------------------
        # Final course score
        # ---------------------------------------------------------------------

        candidate["_course_score"] = (
            COURSE_SKILL_WEIGHT
            * candidate[
                "_skill_match"
            ]
            + COURSE_TEXT_WEIGHT
            * candidate["_text_match"]
            +
            COURSE_POPULARITY_WEIGHT
            * candidate[
                "_pop_score"
            ]
            + COURSE_RATING_WEIGHT * candidate["_rating_score"]
            + COURSE_TECHNOLOGY_WEIGHT * so_score
        )

        candidate = candidate.sort_values(
            "_course_score",
            ascending=False,
        )

        # ---------------------------------------------------------------------
        # Keep top courses
        # ---------------------------------------------------------------------

        selected = candidate.head(
            TOP_COURSES_PER_SKILL
        )

        for _, course in selected.iterrows():

            title = (
                course[title_col]
                if title_col
                else "Untitled Course"
            )

            description = (
                course[
                    description_col
                ]
                if description_col
                else ""
            )

            category = (
                course[
                    category_col
                ]
                if category_col
                else ""
            )

            difficulty = ""

            if "difficulty" in course.index:

                difficulty = (
                    ""
                    if pd.isna(
                        course[
                            "difficulty"
                        ]
                    )
                    else str(
                        course[
                            "difficulty"
                        ]
                    )
                )

            recommendations.append(
                {
                    "skill":
                        skill_label,

                    "priority":
                        priority,

                    "course_id":
                        course[
                            "_course_id"
                        ],

                    "title":
                        str(title),

                    "description":
                        str(description),

                    "category":
                        str(category),

                    "source":
                        str(
                            course["source"]
                            if "source" in course.index
                            and not pd.isna(course["source"])
                            else ""
                        ),

                    "url":
                        str(
                            course["url"]
                            if "url" in course.index
                            and not pd.isna(course["url"])
                            else ""
                        ),

                    "difficulty":
                        difficulty,

                    "course_score":
                        safe_float(
                            course[
                                "_course_score"
                            ]
                        ),

                    "skill_match_score": safe_float(course.get("_skill_match", 0.0)),
                    "text_match_score": safe_float(course.get("_text_match", 0.0)),
                    "popularity_score": safe_float(course.get("_pop_score", 0.0)),
                    "rating_score": safe_float(course.get("_rating_score", 0.0)),
                    "technology_score": safe_float(so_score),
                }
            )

    # -------------------------------------------------------------------------
    # Remove duplicate courses
    # -------------------------------------------------------------------------

    unique = {}

    for item in recommendations:

        key = (
            item["course_id"],
            normalize_text(
                item["skill"]
            ),
        )

        if key not in unique:

            unique[key] = item

    recommendations = list(
        unique.values()
    )

    recommendations.sort(
        key=lambda x: (
            x["priority"],
            x["course_score"],
        ),
        reverse=True,
    )

    return recommendations


# =============================================================================
# ROADMAP
# =============================================================================

def build_roadmap(
    skill_gaps,
    courses,
):
    """
    Build milestone-based learning roadmap.
    """

    if skill_gaps.empty:

        return []

    def stage(label):
        """Assign a learning stage to a skill for roadmap ordering.
        Lower stages come first (foundational → advanced)."""
        text = normalize_text(label)
        # Order: foundations → math/stats → data handling → ML/AI → deployment/soft skills
        stages = [
            (0, {"basic", "foundation", "programming", "computer", "html", "css"}),
            (1, {"math", "mathematics", "statistics", "probability", "linear algebra", "algebra"}),
            (2, {"data", "database", "sql", "query", "analysis", "excel", "visualization", "tableau", "power bi"}),
            (3, {"machine", "learning", "model", "artificial", "neural", "deep", "nlp", "natural language", "computer vision", "reinforcement", "generative", "transformer", "llm", "large language"}),
            (4, {"deploy", "cloud", "docker", "kubernetes", "devops", "ci/cd", "application", "software", "project", "agile", "scrum"}),
        ]
        return min((rank for rank, words in stages if any(word in text for word in words)), default=2)

    ordered_gaps = sorted(
        skill_gaps.to_dict("records"),
        key=lambda gap: (stage(gap.get("skill", "")), -safe_float(gap.get("priority_score"))),
    )
    roadmap = []
    previous_skill = None

    for index, gap in enumerate(ordered_gaps, start=1):

        skill = str(
            gap["skill"]
        )

        # Match courses to skills with both exact and substring matching
        skill_text = normalize_text(skill)
        relevant_courses = [
            course
            for course in courses
            if (
                normalize_text(course["skill"]) == skill_text
                or skill_text in normalize_text(course["skill"])
                or normalize_text(course["skill"]) in skill_text
            )
        ]
        # Sort by course score descending
        relevant_courses.sort(
            key=lambda c: safe_float(c.get("course_score", 0)),
            reverse=True,
        )

        prerequisites = [previous_skill] if previous_skill else []
        previous_skill = skill

        roadmap.append(
            {
                "milestone":
                    index,

                "skill":
                    skill,

                "priority":
                    round(
                        safe_float(
                            gap[
                                "priority_score"
                            ]
                        ),
                        4,
                    ),

                "prerequisites": prerequisites,

                "why_required": str(
                    gap.get("reason", "Required by the target occupation.")
                ),

                "recommended_courses":
                    relevant_courses[:3],

                "course_availability": (
                    "available" if relevant_courses else "course availability unavailable"
                ),
            }
        )

    return roadmap


# =============================================================================
# PRINT ROADMAP
# =============================================================================

def print_roadmap(
    target_occupation,
    confidence,
    skill_gaps,
    course_recommendations,
):
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
        f"{target_occupation}"
    )

    print(
        f"Confidence: "
        f"{confidence:.3f}"
    )

    # -------------------------------------------------------------------------
    # Gaps
    # -------------------------------------------------------------------------

    print(
        "\n"
        + "-" * 80
    )

    print(
        "PRIORITY SKILL GAPS"
    )

    print(
        "-" * 80
    )

    if skill_gaps.empty:

        print(
            "No skill gaps found."
        )

    else:

        display = skill_gaps[
            [
                "skill",
                "base_score",
                "stackoverflow_demand",
                "priority_score",
            ]
        ].copy()

        display[
            "base_score"
        ] = display[
            "base_score"
        ].round(3)

        display[
            "stackoverflow_demand"
        ] = display[
            "stackoverflow_demand"
        ].round(3)

        display[
            "priority_score"
        ] = display[
            "priority_score"
        ].round(3)

        print(
            display.to_string(
                index=False
            )
        )

    # -------------------------------------------------------------------------
    # Course roadmap
    # -------------------------------------------------------------------------

    print(
        "\n"
        + "-" * 80
    )

    print(
        "LEARNING MILESTONES"
    )

    print(
        "-" * 80
    )

    if not course_recommendations:

        print(
            "No courses matched the "
            "identified skill gaps."
        )

        return

    grouped = {}

    for course in course_recommendations:

        grouped.setdefault(
            course["skill"],
            []
        ).append(
            course
        )

    for milestone, (
        skill,
        courses,
    ) in enumerate(
        grouped.items(),
        start=1,
    ):

        print(
            f"\nMILESTONE {milestone}: "
            f"{skill}"
        )

        for i, course in enumerate(
            courses[:3],
            start=1,
        ):

            difficulty = (
                course["difficulty"]
                if course["difficulty"]
                else "Not specified"
            )

            category = (
                course["category"]
                if course["category"]
                else "General"
            )

            print(
                f"  {i}. "
                f"{course['title']}"
            )

            print(
                f"     Category: "
                f"{category}"
            )

            print(
                f"     Difficulty: "
                f"{difficulty}"
            )

            print(
                f"     Score: "
                f"{course['course_score']:.3f}"
            )


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":

    # -------------------------------------------------------------------------
    # User input
    # -------------------------------------------------------------------------

    GOAL = (
        "I want to become a data scientist "
        "working with machine learning"
    )

    KNOWN_SKILLS = [
        "computer programming",
        "mathematics",
    ]

    print(
        "=" * 80
    )

    print(
        "AI PERSONALIZED LEARNING PATH RECOMMENDER"
    )

    print(
        "=" * 80
    )

    # -------------------------------------------------------------------------
    # Load
    # -------------------------------------------------------------------------

    (
        occupations,
        occupation_scores,
        career_profiles,
        crosswalk,
        skills_taxonomy,
        onet_elements,
        courses,
        course_skills,
        stackoverflow,
    ) = load_data()

    # -------------------------------------------------------------------------
    # StackOverflow
    # -------------------------------------------------------------------------

    stackoverflow_index = (
        prepare_stackoverflow(
            stackoverflow
        )
    )

    # -------------------------------------------------------------------------
    # Sentence Transformer
    # -------------------------------------------------------------------------

    print(
        "\nLoading embedding model..."
    )

    from sentence_transformers import (
        SentenceTransformer,
    )

    MODEL_NAME = (
        "all-mpnet-base-v2"
    )

    model = SentenceTransformer(
        MODEL_NAME
    )

    # -------------------------------------------------------------------------
    # Occupation matching
    # -------------------------------------------------------------------------

    print(
        "\nBuilding occupation matching..."
    )

    occupation_matches = (
        find_occupation_matches(
            GOAL,
            occupations,
            model,
        )
    )

    print(
        "\n"
        + "=" * 80
    )

    print(
        f"GOAL: {GOAL}"
    )

    print(
        f"KNOWN SKILLS: {KNOWN_SKILLS}"
    )

    print(
        "=" * 80
    )

    print(
        "\nTop occupation matches:"
    )

    print(
        occupation_matches[
            [
                "onet_soc_code",
                "title",
                "similarity",
            ]
        ]
        .head(
            TOP_OCCUPATIONS
        )
        .to_string(
            index=False
        )
    )

    # -------------------------------------------------------------------------
    # Select occupation
    # -------------------------------------------------------------------------

    selected = (
        occupation_matches.iloc[0]
    )

    occupation_code = (
        selected[
            "onet_soc_code"
        ]
    )

    occupation_title = (
        selected["title"]
    )

    occupation_similarity = safe_float(
        selected["similarity"]
    )

    print(
        f"\nSelected target occupation: "
        f"{occupation_title}"
    )

    print(
        f"Occupation similarity: "
        f"{occupation_similarity:.4f}"
    )

    # -------------------------------------------------------------------------
    # Target ESCO skills
    # -------------------------------------------------------------------------

    target_skills = (
        infer_esco_skills(
            occupation_code,
            occupation_scores,
            crosswalk,
            TOP_TARGET_SKILLS,
        )
    )

    print(
        "\nTop target skills:"
    )

    if target_skills.empty:

        print(
            "No ESCO skills inferred."
        )

    else:

        print(
            target_skills[
                [
                    "esco_skill_id",
                    "esco_skill_label",
                    "esco_score",
                    "similarity",
                ]
            ]
            .head(
                TOP_TARGET_SKILLS
            )
            .to_string(
                index=False
            )
        )

    # -------------------------------------------------------------------------
    # Skill indexes
    # -------------------------------------------------------------------------

    print(
        "\nBuilding skill indexes..."
    )

    skill_indexes = (
        build_skill_indexes(
            skills_taxonomy
        )
    )

    print(
        f"ESCO skills indexed: "
        f"{len(skill_indexes['id_to_label'])}"
    )

    # -------------------------------------------------------------------------
    # Resolve learner skills
    # -------------------------------------------------------------------------

    print(
        "\nResolving learner skills..."
    )

    (
        learner_skill_ids,
        learner_skill_labels,
    ) = resolve_learner_skills(
        KNOWN_SKILLS,
        skill_indexes,
    )

    print(
        "\nLearner skills resolved to ESCO:"
    )

    print(
        learner_skill_labels
    )

    # -------------------------------------------------------------------------
    # Skill gaps
    # -------------------------------------------------------------------------

    print(
        "\nCalculating skill gaps..."
    )

    skill_gaps = (
        calculate_skill_gaps(
            target_skills,
            learner_skill_ids,
            stackoverflow_index,
        )
    )

    print(
        "\nTop skill gaps:"
    )

    if skill_gaps.empty:

        print(
            "No skill gaps found."
        )

    else:

        print(
            skill_gaps[
                [
                    "skill",
                    "base_score",
                    "stackoverflow_demand",
                    "priority_score",
                ]
            ]
            .to_string(
                index=False
            )
        )

    # -------------------------------------------------------------------------
    # Courses
    # -------------------------------------------------------------------------

    print(
        "\nGenerating course recommendations..."
    )

    course_recommendations = (
        recommend_courses(
            skill_gaps,
            courses,
            course_skills,
            skills_taxonomy,
            stackoverflow_index,
        )
    )

    print(
        f"Courses recommended: "
        f"{len(course_recommendations)}"
    )

    # -------------------------------------------------------------------------
    # Roadmap
    # -------------------------------------------------------------------------

    print_roadmap(
        occupation_title,
        occupation_similarity,
        skill_gaps,
        course_recommendations,
    )

    # -------------------------------------------------------------------------
    # Final
    # -------------------------------------------------------------------------

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

