# Companies House / UK Trade Info Matcher

A Streamlit app that compares a Companies House CSV with a UK Trade Info CSV, identifies companies appearing in both files, and optionally enriches the results with director information from the Companies House API.

## Features

- Upload a Companies House CSV.
- Upload a UK Trade Info CSV.
- Match `company_name` against `CompanyName`.
- Normalise case, punctuation, `&`/`AND`, and `LTD`/`LIMITED` differences.
- Display `company_name` and `company_number`.
- Retrieve up to four directors per company.
- Display the total number of directors.
- Link to the Companies House profile.
- Link to a Google search with `Ltd` or `Limited` removed.
- Download the matched and enriched results as CSV.

## Repository structure

```text
.
├── streamlit_company_trade_matcher.py
├── requirements.txt
├── .gitignore
├── .streamlit
│   └── config.toml
└── README.md
```

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
streamlit run streamlit_company_trade_matcher.py
```

## Input files

The Companies House upload must contain:

- `company_name`
- `company_number`

The UK Trade Info upload must contain:

- `CompanyName`

Other columns are allowed and are ignored for matching.

## Companies House API key

Enter the API key in the app sidebar. The key is used for the current session and is not included in downloaded results.

Never commit an API key to GitHub. Do not place it directly in Python code, CSV files, `README.md`, or Streamlit configuration committed to the repository.

## Deploy on Streamlit Community Cloud

1. Push the repository to GitHub.
2. Open Streamlit Community Cloud.
3. Create a new app.
4. Select the repository and branch.
5. Set the main file to `streamlit_company_trade_matcher.py`.
6. Deploy the app.
7. Enter your Companies House API key in the application sidebar.

The application does not require a database or server-side secret for the current implementation.

## API behaviour

The app requests officer data from:

```text
https://api.company-information.service.gov.uk/company/{company_number}/officers
```

API calls are made only for matched companies. Results are cached during the current enrichment operation to avoid repeated requests for duplicate company numbers.

## Matching behaviour

The app performs deterministic matching. It:

- Converts names to uppercase.
- Replaces `&` with `AND`.
- Removes punctuation.
- Removes `LTD` and `LIMITED` tokens.
- Collapses repeated whitespace.

It does not perform fuzzy matching. This reduces the risk of incorrectly combining separate companies with similar names.

## Security note

The API key is entered into a password-type field and is not saved to the repository. For a production deployment, consider using Streamlit secrets or another server-side secret-management system instead of asking each user to enter the key.
