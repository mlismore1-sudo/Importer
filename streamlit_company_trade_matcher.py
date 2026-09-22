import io
import re
from typing import Any
from urllib.parse import quote_plus

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Companies House / UK Trade Matcher",
    page_icon="🏢",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def read_csv_bytes(raw: bytes) -> pd.DataFrame:
    attempts = [
        {"sep": ",", "encoding": "utf-8-sig"},
        {"sep": None, "engine": "python", "encoding": "utf-8-sig"},
        {"sep": ",", "encoding": "cp1252"},
    ]
    last_error = None
    for kwargs in attempts:
        try:
            df = pd.read_csv(io.BytesIO(raw), **kwargs)
            if len(df.columns) > 1:
                return df
        except Exception as exc:
            last_error = exc
    raise ValueError(f"Could not read the uploaded CSV: {last_error}")


def read_upload(uploaded_file) -> pd.DataFrame:
    return read_csv_bytes(uploaded_file.getvalue())


def normalise_name(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).upper().strip()
    text = text.replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\bLIMITED\b|\bLTD\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def display_search_name(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return re.sub(r"\s+(LIMITED|LTD)\.?$", "", text, flags=re.IGNORECASE).strip()


def companies_house_profile(company_number: Any) -> str:
    number = str(company_number).strip()
    return (
        f"https://find-and-update.company-information.service.gov.uk/company/{number}"
        if number and number.lower() != "nan"
        else ""
    )


def google_search(company_name: Any) -> str:
    name = display_search_name(company_name)
    return f"https://www.google.com/search?q={quote_plus(name)}" if name else ""


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_directors(api_key: str, company_number: str) -> tuple[str, ...]:
    url = f"https://api.company-information.service.gov.uk/company/{company_number}/officers"
    response = requests.get(url, auth=(api_key, ""), timeout=20)
    if response.status_code == 404:
        return tuple()
    response.raise_for_status()
    names = []
    for officer in response.json().get("items", []):
        name = officer.get("name")
        if name and name not in names:
            names.append(name)
    return tuple(names)


def enrich_matches(matches: pd.DataFrame, api_key: str, max_directors: int) -> pd.DataFrame:
    enriched = matches.copy()
    director_columns = [f"director_{i}" for i in range(1, max_directors + 1)]
    for column in director_columns:
        enriched[column] = ""
    enriched["total_directors"] = 0
    enriched["companies_house_profile"] = enriched["company_number"].map(companies_house_profile)
    enriched["google_search"] = enriched["company_name"].map(google_search)

    progress = st.progress(0, text="Enriching matched companies…")
    errors = []

    for position, (index, row) in enumerate(enriched.iterrows(), start=1):
        company_number = str(row["company_number"]).strip()
        try:
            directors = fetch_directors(api_key, company_number)
            enriched.at[index, "total_directors"] = len(directors)
            for director_position, name in enumerate(directors[:max_directors], start=1):
                enriched.at[index, f"director_{director_position}"] = name
        except requests.RequestException as exc:
            errors.append(f"{company_number}: {exc}")
        progress.progress(
            position / len(enriched),
            text=f"Enriching company {position} of {len(enriched)}…",
        )

    progress.empty()
    if errors:
        st.warning(f"{len(errors)} Companies House API request(s) failed.")
        with st.expander("View API errors"):
            st.code("\n".join(errors))
    return enriched


st.title("Companies House / UK Trade Info Matcher")
st.caption("Upload two CSV files to find companies present in both datasets.")

with st.sidebar:
    st.header("1. Upload files")
    companies_file = st.file_uploader(
        "Companies House CSV",
        type=["csv"],
        help="Required columns: company_name and company_number.",
    )
    trade_file = st.file_uploader(
        "UK Trade Info CSV",
        type=["csv"],
        help="Required column: CompanyName.",
    )

    st.header("2. Enrichment")
    api_key = st.text_input(
        "Companies House API key",
        type="password",
        help="The key is used for this session and is not included in the downloaded CSV.",
    )
    max_directors = st.number_input(
        "Maximum directors to display",
        min_value=1,
        max_value=4,
        value=4,
        step=1,
    )
    enrich = st.checkbox("Enrich with Companies House", value=True)

if not companies_file or not trade_file:
    st.info("Upload both CSV files using the sidebar.")
    st.stop()

try:
    companies = read_upload(companies_file)
    trade = read_upload(trade_file)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

required_companies_columns = {"company_name", "company_number"}
missing_companies_columns = required_companies_columns.difference(companies.columns)
if missing_companies_columns:
    st.error(
        "The Companies House CSV is missing: "
        + ", ".join(sorted(missing_companies_columns))
    )
    st.stop()

if "CompanyName" not in trade.columns:
    st.error("The UK Trade Info CSV must contain a column named 'CompanyName'.")
    st.stop()

companies = companies.copy()
trade = trade.copy()
companies["_match_key"] = companies["company_name"].map(normalise_name)
trade["_match_key"] = trade["CompanyName"].map(normalise_name)
trade_keys = set(trade.loc[trade["_match_key"].ne(""), "_match_key"])

matches = companies[companies["_match_key"].isin(trade_keys)].copy()
matches = matches.drop_duplicates(subset=["company_number"])
matches = matches.drop(columns=["_match_key"])

metric_1, metric_2, metric_3 = st.columns(3)
metric_1.metric("Companies House rows", f"{len(companies):,}")
metric_2.metric("UK Trade Info rows", f"{len(trade):,}")
metric_3.metric("Matched companies", f"{len(matches):,}")

if matches.empty:
    st.warning("No matches found after name normalisation.")
    st.stop()

if enrich:
    if not api_key:
        st.warning("Enter a Companies House API key to retrieve director information.")
        matches["companies_house_profile"] = matches["company_number"].map(companies_house_profile)
        matches["google_search"] = matches["company_name"].map(google_search)
    else:
        matches = enrich_matches(matches, api_key, int(max_directors))
else:
    matches["companies_house_profile"] = matches["company_number"].map(companies_house_profile)
    matches["google_search"] = matches["company_name"].map(google_search)

st.subheader("Matched companies")
st.dataframe(
    matches,
    use_container_width=True,
    hide_index=True,
    column_config={
        "companies_house_profile": st.column_config.LinkColumn(
            "Companies House profile",
            display_text="Open profile",
        ),
        "google_search": st.column_config.LinkColumn(
            "Google search",
            display_text="Search Google",
        ),
    },
)

st.download_button(
    "Download matched companies CSV",
    data=matches.to_csv(index=False).encode("utf-8-sig"),
    file_name="matched_companies_enriched.csv",
    mime="text/csv",
)

with st.expander("Matching method"):
    st.write(
        "Names are converted to uppercase, punctuation is removed, '&' is converted "
        "to 'AND', LTD/LIMITED is removed, and repeated spaces are collapsed. "
        "The app uses deterministic matching rather than fuzzy matching."
    )
