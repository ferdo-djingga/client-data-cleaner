# Client Data Onboarding Cleaner

## Introduction
Client data often comes in messy spreadsheets with inconsistent column names, invalid emails, differently formatted phone numbers, or duplicate entries.  
This project provides a simple Python-based tool to automatically clean and standardize such data, making it ready for use in applications like CRMs, customer success platforms, or analytics tools.  

The cleaner reads a raw CSV file of client information, fixes common issues, removes duplicates, and produces:
- A **clean, standardized CSV file** ready for use.  
- A **human-readable HTML validation report** showing what was cleaned, flagged, or dropped.  

---

## Project Structure

Client-Data-Onboarding-Cleaner/
├─ src/
│  └─ cleaner.py            # main cleaning logic & CLI
├─ data/
│  ├─ raw_clients.csv       # sample messy data (input)
│  └─ clean_clients.csv     # cleaned dataset (output)
├─ output/
│  └─ validation_report.html # generated quality report
├─ tests/
│  └─ test_cleaner.py       # automated tests
├─ README.md
└─ benchmark.md

---

## Instructions
1. **Set up the environment**  
   Create and activate a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate     # On Windows: .venv\Scripts\activate
   pip install pandas

2. **Run the Cleaner**
  By default, the tool uses the sample file data/raw_clients.csv:
  python -m src.cleaner
  You can also provide your own file paths:
  python -m src.cleaner -i data/raw_clients.csv -o data/clean_clients.csv -r output/validation_report.html

3. **Check the Outputs**
  Open data/clean_clients.csv in any text editor or Excel to view the cleaned dataset.