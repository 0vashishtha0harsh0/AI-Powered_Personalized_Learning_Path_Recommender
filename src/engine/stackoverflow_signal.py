import pandas as pd
import numpy as np
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

SO_PATH = (
    BASE_DIR
    / "Data"
    / "raw"
    / "surveys"
    / "stackoverflow"
    / "survey_results_public.csv"
)


def load_stackoverflow():
    return pd.read_csv(SO_PATH)


def _explode_column(df, column):
    if column not in df.columns:
        return pd.Series(dtype=str)

    return (
        df[column]
        .dropna()
        .astype(str)
        .str.split(";")
        .explode()
        .str.strip()
    )


def build_skill_demand():

    df = load_stackoverflow()

    # ---------------------------------------------------------
    # Focus on Data Scientist / ML respondents
    # ---------------------------------------------------------

    target = df[
        df["DevType"]
        .fillna("")
        .str.contains(
            "Data scientist or machine learning specialist",
            case=False,
            regex=False,
        )
    ].copy()

    print(
        f"Stack Overflow Data Scientist/ML respondents: "
        f"{len(target)}"
    )

    # ---------------------------------------------------------
    # Languages
    # ---------------------------------------------------------

    languages = _explode_column(
        target,
        "LanguageWantToWorkWith",
    )

    language_counts = languages.value_counts()

    # ---------------------------------------------------------
    # Databases
    # ---------------------------------------------------------

    databases = _explode_column(
        target,
        "DatabaseWantToWorkWith",
    )

    database_counts = databases.value_counts()

    # ---------------------------------------------------------
    # Misc technologies
    # ---------------------------------------------------------

    misc = _explode_column(
        target,
        "MiscTechWantToWorkWith",
    )

    misc_counts = misc.value_counts()

    # ---------------------------------------------------------
    # Tools
    # ---------------------------------------------------------

    tools = _explode_column(
        target,
        "ToolsTechWantToWorkWith",
    )

    tool_counts = tools.value_counts()

    # ---------------------------------------------------------
    # Combine everything
    # ---------------------------------------------------------

    all_counts = {}

    for series in [
        language_counts,
        database_counts,
        misc_counts,
        tool_counts,
    ]:

        for skill, count in series.items():

            all_counts[skill] = (
                all_counts.get(skill, 0)
                + int(count)
            )

    demand = pd.DataFrame(
        list(all_counts.items()),
        columns=[
            "technology",
            "demand_count",
        ],
    )

    # Normalize 0-1
    if not demand.empty:

        max_count = demand[
            "demand_count"
        ].max()

        demand["demand_score"] = (
            demand["demand_count"]
            / max_count
        )

    else:

        demand["demand_score"] = 0.0

    demand = demand.sort_values(
        "demand_score",
        ascending=False,
    ).reset_index(drop=True)

    return demand


if __name__ == "__main__":

    demand = build_skill_demand()

    print("\nTop Stack Overflow technologies:")
    print(
        demand.head(30).to_string(
            index=False
        )
    )

    output = (
        BASE_DIR
        / "Data"
        / "processed"
        / "stackoverflow_skill_demand.csv"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    demand.to_csv(
        output,
        index=False,
    )

    print(
        f"\nSaved: {output}"
    )