from __future__ import annotations

import argparse
import html
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Tuple

import pandas as pd

# config
COLUMN_ALIASES: Dict[str, str] = {
    "client id": "client_id", "client_id": "client_id", "id": "client_id", "clientid": "client_id",
    "full name": "full_name", "name": "full_name", "fullname": "full_name",
    "first name": "first_name", "firstname": "first_name",
    "last name": "last_name", "lastname": "last_name",
    "email": "email", "e-mail": "email", "mail": "email",
    "phone": "phone", "mobile": "phone", "telephone": "phone",
    "signup date": "signup_date", "signupdate": "signup_date",
    "created at": "signup_date", "created": "signup_date",
    "plan": "plan", "tier": "plan",
    "country": "country", "company": "company", "notes": "notes",
}

CANONICAL_COLUMNS = [
    "client_id", "first_name", "last_name", "full_name",
    "email", "email_domain", "phone", "signup_date",
    "plan", "country", "company", "notes",
]

REQUIRED_ANY_ONE_OF = [["email", "phone"]]
EMAIL_REGEX = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


@dataclass
class CleanResult:
    df: pd.DataFrame
    stats: Dict[str, int]
    issues: Dict[str, pd.DataFrame]


# helper functions
def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for c in df.columns:
        key = c.strip().lower()
        rename_map[c] = COLUMN_ALIASES.get(key, key)
    return df.rename(columns=rename_map)


def _strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    str_cols = df.select_dtypes(include=["object"]).columns
    for c in str_cols:
        df[c] = df[c].astype(str).str.strip().replace({"": pd.NA, "nan": pd.NA})
    return df


def _split_full_name(df: pd.DataFrame) -> pd.DataFrame:
    if "full_name" in df.columns:
        need_first = "first_name" not in df.columns
        need_last = "last_name" not in df.columns
        if need_first or need_last:
            parts = df["full_name"].fillna("").astype(str).str.split()
            if need_first:
                df["first_name"] = parts.apply(lambda p: p[0] if len(p) > 0 else pd.NA)
            if need_last:
                df["last_name"] = parts.apply(lambda p: " ".join(p[1:]) if len(p) > 1 else pd.NA)
    return df


def _normalize_email(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    invalid = pd.DataFrame()
    if "email" in df.columns:
        df["email"] = df["email"].str.lower()
        mask_invalid = df["email"].notna() & ~df["email"].str.match(EMAIL_REGEX)
        invalid = df.loc[mask_invalid].copy()
    return df, invalid


def _email_domain(df: pd.DataFrame) -> pd.DataFrame:
    if "email" in df.columns:
        df["email_domain"] = df["email"].str.split("@").str[-1]
    return df


def _normalize_phone(df: pd.DataFrame) -> pd.DataFrame:
    if "phone" in df.columns:
        def norm(x: str):
            if pd.isna(x): return pd.NA
            s = str(x).strip()
            if s.startswith("+"):
                digits = "+" + re.sub(r"\D", "", s[1:])
            else:
                digits = re.sub(r"\D", "", s)
            return digits if digits and digits not in {"+", ""} else pd.NA
        df["phone"] = df["phone"].apply(norm)
    return df


def _parse_dates(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    invalid = pd.DataFrame()
    if "signup_date" in df.columns:
        parsed = pd.to_datetime(df["signup_date"], errors="coerce", dayfirst=False, infer_datetime_format=True)
        invalid = df.loc[parsed.isna() & df["signup_date"].notna()].copy()
        df["signup_date"] = parsed.dt.strftime("%Y-%m-%d")
    return df, invalid


def _drop_unreachable(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    keep_mask = pd.Series(True, index=df.index)
    for group in REQUIRED_ANY_ONE_OF:
        group_present = pd.Series(False, index=df.index)
        for col in group:
            if col in df.columns:
                group_present |= df[col].notna()
        keep_mask &= group_present
    dropped = df.loc[~keep_mask].copy()
    return df.loc[keep_mask].copy(), dropped


def _deduplicate(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    dup_issues = {}
    if "email" in df.columns:
        before = len(df)
        df["_email_key"] = df["email"].fillna("").str.lower()
        dup_mask = df.duplicated("_email_key", keep="first") & df["_email_key"].ne("")
        dup_issues["duplicate_email_rows"] = df.loc[dup_mask].copy()
        df = df.loc[~dup_mask].copy()
        df.drop(columns=["_email_key"], inplace=True)
        dup_issues["duplicate_email_count"] = pd.DataFrame({"count": [before - len(df)]})
    if "client_id" in df.columns:
        before = len(df)
        dup_mask = df.duplicated("client_id", keep="first") & df["client_id"].notna()
        dup_issues["duplicate_client_id_rows"] = df.loc[dup_mask].copy()
        df = df.loc[~dup_mask].copy()
        dup_issues["duplicate_client_id_count"] = pd.DataFrame({"count": [before - len(df)]})
    return df, dup_issues


def _reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    existing = [c for c in CANONICAL_COLUMNS if c in df.columns]
    extras = [c for c in df.columns if c not in existing]
    return df[existing + extras]


def clean_dataframe(df: pd.DataFrame) -> CleanResult:
    start = datetime.now()
    original_rows = len(df)

    df = _normalize_columns(df)
    df = _strip_strings(df)
    df = _split_full_name(df)

    df, invalid_emails = _normalize_email(df)
    df = _email_domain(df)
    df = _normalize_phone(df)
    df, invalid_dates = _parse_dates(df)
    df, dropped_unreachable = _drop_unreachable(df)
    df, dup_issues = _deduplicate(df)

    df = _reorder_columns(df)
    end = datetime.now()

    stats = {
        "rows_input": original_rows,
        "rows_output": len(df),
        "rows_dropped_unreachable": len(dropped_unreachable),
        "invalid_email_count": len(invalid_emails),
        "invalid_date_count": len(invalid_dates),
        "duration_seconds": (end - start).total_seconds(),
    }
    issues = {"invalid_emails": invalid_emails, "invalid_dates": invalid_dates, "dropped_unreachable": dropped_unreachable}
    issues.update(dup_issues)

    return CleanResult(df=df, stats=stats, issues=issues)


# report
def _df_to_html_table(df: pd.DataFrame, max_rows=30) -> str:
    if df is None or df.empty: return "<em>None</em>"
    return df.head(max_rows).to_html(index=False, escape=False)


def write_validation_report(result: CleanResult, output_path: str) -> None:
    s = result.stats
    sections = [f"""
    <section><h2>Summary</h2><ul>
      <li>Rows in: <strong>{s['rows_input']}</strong></li>
      <li>Rows out: <strong>{s['rows_output']}</strong></li>
      <li>Dropped (unreachable): <strong>{s['rows_dropped_unreachable']}</strong></li>
      <li>Invalid emails: <strong>{s['invalid_email_count']}</strong></li>
      <li>Invalid signup dates: <strong>{s['invalid_date_count']}</strong></li>
      <li>Duration (s): <strong>{s['duration_seconds']:.4f}</strong></li>
    </ul></section>"""]
    for key, df in result.issues.items():
        title = key.replace("_", " ").title()
        sections.append(f"<section><h3>{html.escape(title)}</h3>{_df_to_html_table(df)}</section>")
    html_str = f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"/><title>Validation Report</title></head><body>
<h1>Validation Report</h1>
<p>Generated: {datetime.now().isoformat(timespec='seconds')}</p>
{''.join(sections)}</body></html>"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f: f.write(html_str)


# CLI
def clean_file(input_csv: str, output_csv: str, report_html: str) -> CleanResult:
    df = pd.read_csv(input_csv, dtype=str, keep_default_na=False, na_values=["", "NA", "NaN"]).replace({"": pd.NA})
    result = clean_dataframe(df)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    result.df.to_csv(output_csv, index=False)
    write_validation_report(result, report_html)
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Clean client CSV data for onboarding.")
    p.add_argument("--input", "-i", default="data/raw_clients.csv")
    p.add_argument("--output", "-o", default="data/clean_clients.csv")
    p.add_argument("--report", "-r", default="output/validation_report.html")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    result = clean_file(args.input, args.output, args.report)
    print("Cleaning complete.")
    print(f"Rows in: {result.stats['rows_input']} -> Rows out: {result.stats['rows_output']}")
    print(f"Wrote: {args.output}")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()