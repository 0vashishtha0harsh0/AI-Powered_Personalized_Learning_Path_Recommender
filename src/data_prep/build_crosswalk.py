"""
STEP 2: Embedding-based crosswalk between ESCO (fine) skills and
O*NET (broad) elements, and save reusable embeddings.

Install once (in your notebook environment):
    pip install sentence-transformers

Produces:
  embeddings/skill_embeddings/esco_skill_embeddings.npy
  embeddings/skill_embeddings/onet_element_embeddings.npy
  embeddings/skill_embeddings/esco_skill_ids.csv        (row order key for the .npy)
  embeddings/skill_embeddings/onet_element_ids.csv      (row order key for the .npy)
  processed/skills/esco_onet_crosswalk.csv              (top-3 matches per ESCO skill + confidence)
"""

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import os

OUT = "../Data/processed"
EMB = "../embeddings/skill_embeddings"
os.makedirs(EMB, exist_ok=True)

# ------------------------------------------------------------
# Load taxonomy tables built in Step 1
# ------------------------------------------------------------
skills = pd.read_csv(f"{OUT}/skills/skills_taxonomy.csv")
elements = pd.read_csv(f"{OUT}/skills/onet_elements.csv")

# ------------------------------------------------------------
# Build embedding input text
#   ESCO skill: label + its parent category as context
#     (context matters a lot here — "communication" alone is
#      too generic, "communication (communication, collaboration
#      and creativity)" disambiguates it)
#   O*NET element: name + official description
# ------------------------------------------------------------
def esco_text(row):
    parts = [str(row["skill_label"])]
    if pd.notna(row.get("parent_3")):
        parts.append(f"category: {row['parent_3']}")
    return " | ".join(parts)

def onet_text(row):
    desc = row["element_description"] if pd.notna(row["element_description"]) else ""
    return f"{row['element_name']}: {desc}"

skills["embed_text"] = skills.apply(esco_text, axis=1)
elements["embed_text"] = elements.apply(onet_text, axis=1)

# ------------------------------------------------------------
# Embed with a strong general-purpose sentence embedding model.
# all-mpnet-base-v2 is slower than MiniLM but noticeably better
# for this kind of short-phrase semantic matching -- worth it
# since this crosswalk only needs to run once, not per-query.
# ------------------------------------------------------------
model = SentenceTransformer("all-mpnet-base-v2")

print("Embedding ESCO skills...")
esco_emb = model.encode(skills["embed_text"].tolist(), show_progress_bar=True, normalize_embeddings=True)

print("Embedding O*NET elements...")
onet_emb = model.encode(elements["embed_text"].tolist(), show_progress_bar=True, normalize_embeddings=True)

np.save(f"{EMB}/esco_skill_embeddings.npy", esco_emb)
np.save(f"{EMB}/onet_element_embeddings.npy", onet_emb)
skills[["skill_id"]].to_csv(f"{EMB}/esco_skill_ids.csv", index=False)
elements[["element_id"]].to_csv(f"{EMB}/onet_element_ids.csv", index=False)

# ------------------------------------------------------------
# Cosine similarity matrix (normalized embeddings -> dot product
# = cosine similarity). 1981 x 120 is tiny, no FAISS needed here.
# ------------------------------------------------------------
sim_matrix = esco_emb @ onet_emb.T   # shape: (n_esco, n_onet)

TOP_K = 3
CONFIDENT_THRESHOLD = 0.45   # tune after inspecting distribution below

rows = []
for i, skill_row in skills.iterrows():
    sims = sim_matrix[i]
    top_idx = np.argsort(-sims)[:TOP_K]
    for rank, j in enumerate(top_idx, start=1):
        rows.append({
            "esco_skill_id": skill_row["skill_id"],
            "esco_skill_label": skill_row["skill_label"],
            "onet_element_id": elements.iloc[j]["element_id"],
            "onet_element_name": elements.iloc[j]["element_name"],
            "onet_element_type": elements.iloc[j]["element_type"],
            "similarity": float(sims[j]),
            "rank": rank,
            "confident": bool(sims[j] >= CONFIDENT_THRESHOLD),
        })

crosswalk = pd.DataFrame(rows)
crosswalk.to_csv(f"{OUT}/skills/esco_onet_crosswalk.csv", index=False)

# ------------------------------------------------------------
# Diagnostics -- check this before trusting the crosswalk
# ------------------------------------------------------------
top1 = crosswalk[crosswalk["rank"] == 1]
print("\n=== Similarity score distribution (rank 1 matches) ===")
print(top1["similarity"].describe())

print(f"\n% of ESCO skills with a confident (>= {CONFIDENT_THRESHOLD}) top-1 match:",
      round(100 * top1["confident"].mean(), 1), "%")

print("\n=== Sample: 15 random top-1 matches (eyeball these for sanity) ===")
print(top1.sample(15, random_state=42)[["esco_skill_label", "onet_element_name", "similarity"]])

print("\n=== Worst matches (lowest similarity -- likely unmappable / too niche) ===")
print(top1.sort_values("similarity").head(10)[["esco_skill_label", "onet_element_name", "similarity"]])