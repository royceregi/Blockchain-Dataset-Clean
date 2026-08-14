import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw")
OUT_DIR = Path("reports")
OUT_DIR.mkdir(parents=True, exist_ok=True)

RAW_FILES = sorted(RAW_DIR.glob("*.csv"))

if not RAW_FILES:
    raise FileNotFoundError(f"No CSV files found in {RAW_DIR}")

summary_rows = []

print("=" * 60)
print("RAW DATA PROFILE")
print("=" * 60)

for raw_file in RAW_FILES:
    df = pd.read_csv(raw_file, low_memory=False)
    print(f"\n--- {raw_file.name} ---")
    print(f"Rows    : {len(df):,}")
    print(f"Columns : {len(df.columns)}")
    print(f"Memory  : {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    print(f"Columns : {df.columns.tolist()}")
    print(f"Exact duplicate rows: {df.duplicated().sum():,}")

    missing = pd.DataFrame({
        "missing_count": df.isna().sum(),
        "missing_percent": (df.isna().mean() * 100).round(2),
    }).sort_values("missing_count", ascending=False)
    missing_file = OUT_DIR / f"missing_values_{raw_file.stem}.csv"
    missing.to_csv(missing_file)

    date_col = next(
        (c for c in ["instance_date", "Timestamp", "timestamp", "Registration_Date", "Block_Timestamp"]
         if c in df.columns),
        None,
    )
    min_date = max_date = invalid_dates = None
    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
        invalid_dates = int(dates.isna().sum())
        min_date = dates.min()
        max_date = dates.max()
        print(f"Date column: {date_col}")
        print(f"Invalid dates: {invalid_dates:,}")
        print(f"Range: {min_date} -> {max_date}")

    summary_rows.append({
        "file": raw_file.name,
        "rows": len(df),
        "columns": len(df.columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "date_column": date_col,
        "invalid_dates": invalid_dates,
        "min_date": min_date,
        "max_date": max_date,
    })

pd.DataFrame(summary_rows).to_csv(OUT_DIR / "raw_profile_summary.csv", index=False)
print("\nProfile complete. Reports saved in:", OUT_DIR)
