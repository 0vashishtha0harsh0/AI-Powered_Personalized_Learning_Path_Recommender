from pathlib import Path

RAW_DIR = Path("Data/raw/onet/db_29_0_text")

for fname in ["Skills.txt", "Knowledge.txt", "Abilities.txt"]:
    path = RAW_DIR / fname
    with open(path, encoding="utf-8", errors="ignore") as f:
        lines = [l for l in f if l.startswith("15-2051.00")]
    print(f"{fname}: {len(lines)} rows for 15-2051.00")
