import pandas as pd
from src.cleaner import clean_dataframe

def test_email_lower_and_regex():
    df = pd.DataFrame({"email": ["User@Example.com", "bad-email", None]})
    result = clean_dataframe(df)
    out = result.df
    assert "email" in out.columns
    assert out.loc[out["email"].notna(), "email"].str.contains(r"[A-Z]").sum() == 0
    assert result.stats["invalid_email_count"] == 1

def test_split_full_name():
    df = pd.DataFrame({"full_name": ["Ada Lovelace", "Prince", None]})
    result = clean_dataframe(df)
    out = result.df
    assert "first_name" in out.columns and "last_name" in out.columns
    row0 = out.iloc[0]
    assert row0["first_name"] == "Ada" and row0["last_name"] == "Lovelace"

def test_date_parse_iso():
    df = pd.DataFrame({"signup_date": ["2023/01/05", "05-01-2023", "bad"]})
    result = clean_dataframe(df)
    out = result.df
    assert result.stats["invalid_date_count"] == 1
    assert out["signup_date"].notna().sum() >= 2

def test_deduplicate_email_then_id():
    df = pd.DataFrame({
        "email": ["a@x.com", "A@x.com", None, None],
        "client_id": ["1", "1", "2", "2"]
    })
    result = clean_dataframe(df)
    assert result.stats["rows_input"] == 4
    assert result.stats["rows_output"] <= 3