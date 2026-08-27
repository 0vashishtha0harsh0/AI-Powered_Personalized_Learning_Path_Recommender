# AI-Powered Personalized Learning Path Recommender

An intelligent learning assistant that recommends personalized learning paths
based on a learner's goals, current skills, and career aspirations — generating
a structured roadmap of courses with prerequisites, milestones, and explainable
recommendations.

## Problem

Online learning platforms offer thousands of courses, but learners struggle to
identify the *right sequence* of resources to reach a specific goal. This project
bridges that gap by grounding recommendations in real occupational skill
requirements (O*NET), Stack Overflow technology demand, and course evidence, rather
than relying on course popularity alone.

## Architecture

```
Raw data (O*NET, ESCO, Stack Overflow, Udemy/edX/Coursera)
        │
        ▼
┌─────────────────────────┐
│ 1. Skill Taxonomy Layer │  ESCO (fine-grained, 1981 skills) +
│                          │  O*NET (broad, 120 elements) merged via
│                          │  embedding-based crosswalk
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│ 2. Career Profile Layer │  O*NET occupation × skill importance/level
│                          │  matrix (1016 occupations)
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│ 3. Course Tagging Layer │  52,943 courses (Udemy/edX/Coursera) tagged
│                          │  with skills via embedding similarity +
│                          │  keyword matching + category alignment
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│ 4. Recommendation Engine│  Learner resolution → hybrid career match →
│                          │  O*NET/ESCO gaps → course ranking → roadmap
└─────────────────────────┘
        │
        ▼
   React frontend + FastAPI backend
```

## Data Sources

| Source | Purpose | Link |
|---|---|---|
| O*NET Database 29.0 | Occupation-skill importance/level scores | onetcenter.org |
| ESCO (job posting extraction sample) | Fine-grained skills + real demand frequency | data.europa.eu/esco |
| Udemy course datasets | Course catalog | Kaggle |
| edX course dataset | Course catalog | Kaggle |
| Coursera course dataset | Course catalog | Kaggle |

Raw data is not committed to this repo (size/licensing). See `docs/data_setup.md`
for download instructions and expected folder structure.

## Pipeline (data_prep)

1. `build_taxonomy.py` — builds the two-layer skill taxonomy (ESCO fine-grained
   + O*NET broad elements) and the occupation-skill score matrix.
2. `build_crosswalk.py` — embedding-based crosswalk connecting ESCO skills to
   O*NET broad elements (sentence-transformers `all-mpnet-base-v2`).
3. `build_unified_courses.py` — unifies Udemy/edX/Coursera into one schema.
4. `build_course_skill_tagging.py` — tags each course with the skills it
   teaches using a 3-signal approach: embedding similarity (FAISS), exact
   keyword matching (FlashText), and category alignment boosting.

## Tech Stack

- **Data/ML**: Python, pandas, sentence-transformers, FAISS, FlashText
- **Backend**: FastAPI (planned)
- **Frontend**: React (planned)

## Status

🚧 In active development — skill taxonomy, career profiles, and course
skill-tagging pipeline complete. Recommendation engine + prerequisite DAG
in progress.

## Setup

```bash
pip install -r requirements.txt
```

See `docs/data_setup.md` for data download instructions before running the
pipeline scripts in `src/data_prep/`.

Run the preprocessing scripts from the project root in this order:

```bash
python src/data_prep/build_taxonomy.py
python src/data_prep/build_crosswalk.py
python src/data_prep/build_unified_courses.py
python src/data_prep/build_course_skill_tagging.py
python src/engine/stackoverflow_signal.py
```

The engine reuses validated career embeddings, resolves parent O*NET codes to
detailed sub-occupations, and keeps milestones when course availability is
missing. Roadmap ordering is a transparent heuristic when source prerequisite
data is unavailable. Start the API with:

```bash
uvicorn src.api.main:app --reload
```

## Deployment

The backend can be deployed on Render from `render.yaml`.

Required Render environment variables:

```bash
GEMINI_API_KEY=your_google_ai_studio_key
LLM_MODEL=gemini-3.6-flash
```

Render should use:

```bash
Build Command: pip install --upgrade pip && pip install -r requirements.txt
Start Command: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

The frontend must point to the Render backend:

```bash
VITE_API_URL=https://ai-powered-personalized-learning-path-8bvq.onrender.com
```

After changing backend environment variables, redeploy the Render service. If
users still see a session error, sign out and sign in again to refresh the
stored auth token.
