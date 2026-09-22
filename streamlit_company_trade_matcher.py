import io
import re
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Company Name Matcher",
    page_icon="🔎",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def read_csv_bytes(raw: bytes) -> pd.DataFrame:
    """Read a normal CSV, with a small fallback for common delimiters."""
    attempts = [
        {"sep": ",", "encoding": "utf-8-sig"},
        {"sep": ";", "encoding": "utf-8-sig"},
        {"sep": "\t", "encoding": "utf-8-sig"},
        {"sep": "|", "encoding": "utf-8-sig"},
        {"sep": ",", "encoding": "cp1252"},
    ]

    errors = []

    for options in attempts:
        try:
            dataframe = pd.read_csv(
                io.BytesIO(raw),
                engine="python",
                on_bad_lines="error",
                **options,
            )
            if len(dataframe.columns) >= 1:
                return dataframe
        except Exception as exc:
            errors.append(str(exc))

    raise ValueError(
        "Could not read the uploaded CSV. Please check that it is a valid CSV file. "
        + " | ".join(errors[-2:])
    )


def read_upload(uploaded_file) -> pd.DataFrame:
    return read_csv_bytes(uploaded_file.getvalue())


def normalise_name(value: Any) -> str:
    """Normalise names for comparison while retaining the original display value."""
    if pd.isna(value):
        return ""

    text = str(value).upper().strip()
    text = text.replace("&", " AND ")
    text = re.sub(r"\bLIMITED\b|\bLTD\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


st.title("Company Name Matcher")
st.write(
    "Upload two CSV files. The app compares column A in each file and displays "
    "the matching company name and company number from the first file."
)

with st.sidebar:
    st.header("Upload files")
    first_file = st.file_uploader(
        "1. Companies House CSV",
        type=["csv"],
        help="Column A should contain company names. Column B should contain company numbers.",
    )
    second_file = st.file_uploader(
        "2. UK Trade Info CSV",
        type=["csv"],
        help="Column A should contain company names.",
    )

if not first_file or not second_file:
    st.info("Upload both CSV files in the sidebar to begin.")
    st.stop()

try:
    first_dataframe = read_upload(first_file)
    second_dataframe = read_upload(second_file)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

if first_dataframe.shape[1] < 2:
    st.error(
        "The first CSV must contain at least two columns: column A for company name "
        "and column B for company number."
    )
    st.stop()

if first_dataframe.shape[1] < 1 or second_dataframe.shape[1] < 1:
    st.error("Both CSV files must contain at least one column.")
    st.stop()

first_name_column = first_dataframe.columns[0]
company_number_column = first_dataframe.columns[1]
second_name_column = second_dataframe.columns[0]

first = first_dataframe.copy()
second = second_dataframe.copy()

first["_match_key"] = first[first_name_column].map(normalise_name)
second["_match_key"] = second[second_name_column].map(normalise_name)

second_names = set(second.loc[second["_match_key"].ne(""), "_match_key"])

matches = first[first["_match_key"].isin(second_names)].copy()
matches = matches.drop_duplicates(subset=[company_number_column])
matches = matches[[first_name_column, company_number_column]]
matches.columns = ["company_name", "company_number"]

col1, col2, col3 = st.columns(3)
col1.metric("Rows in first file", f"{len(first_dataframe):,}")
col2.metric("Rows in second file", f"{len(second_dataframe):,}")
col3.metric("Matches", f"{len(matches):,}")

st.caption(
    f"Comparing column A: '{first_name_column}' against column A: '{second_name_column}'."
)

if matches.empty:
    st.warning("No matching company names were found.")
else:
    st.subheader("Matching companies")
    st.dataframe(matches, use_container_width=True, hide_index=True)

    st.download_button(
        "Download matches as CSV",
        data=matches.to_csv(index=False).encode("utf-8-sig"),
        file_name="matching_companies.csv",
        mime="text/csv",
    )
        {"sep": ",", "encoding": "cp1252", "engine": "python"},
    ]
    errors = []

    for kwargs in attempts:
        try:
            df = pd.read_csv(io.BytesIO(raw), **kwargs, on_bad_lines="error")
            if len(df.columns) > 1:
                return df
        except Exception as exc:
            errors.append(f"{kwargs}: {exc}")

    fallback_attempts = [
        {"sep": ",", "encoding": "utf-8-sig"},
        {"sep": ";", "encoding": "utf-8-sig"},
        {"sep": "\t", "encoding": "utf-8-sig"},
        {"sep": "|", "encoding": "utf-8-sig"},
        {"sep": None, "encoding": "utf-8-sig"},
        {"sep": ",", "encoding": "cp1252"},
    ]

    for kwargs in fallback_attempts:
        try:
            df = pd.read_csv(
                io.BytesIO(raw),
                engine="python",
                **kwargs,
                on_bad_lines="warn",
            )
            if len(df.columns) > 1:
                st.warning(
                    "The uploaded CSV contains malformed rows. Those rows were "
                    "skipped during import. Check the source file if matches are missing."
                )
                return df
        except Exception as exc:
            errors.append(f"fallback {kwargs}: {exc}")

    raise ValueError(
        "Could not read the uploaded CSV. The file has inconsistent columns, "
        "an incorrect delimiter, or malformed quoting. Last errors: "
        + " | ".join(errors[-3:])
    )


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


def get_api_key() -> str:
    try:
        api_key = st.secrets["COMPANIES_HOUSE_API_KEY"]
    except KeyError:
        st.error(
            "The Companies House API key is not configured. Add "
            "COMPANIES_HOUSE_API_KEY to Streamlit Secrets."
        )
        st.stop()
    except FileNotFoundError:
        st.error("Streamlit Secrets are not available in this environment.")
        st.stop()

    if not isinstance(api_key, str) or not api_key.strip():
        st.error("COMPANIES_HOUSE_API_KEY is empty in Streamlit Secrets.")
        st.stop()
    return api_key.strip()


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
    for number in range(1, max_directors + 1):
        enriched[f"director_{number}"] = ""
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
st.caption("Match trade importers against Companies House results and SIC codes.")

with st.sidebar:
    st.header("1. Upload files")
    companies_file = st.file_uploader(
        "Companies House CSV",
        type=["csv"],
        help="Required columns include company_name, company_number and nature_of_business.",
    )
    trade_file = st.file_uploader(
        "UK Trade Info CSV",
        type=["csv"],
        help="Required column: CompanyName.",
    )

    st.header("2. Filters")
    sic_filter = st.text_input(
        "SIC code filter",
        value="",
        help="Optional. Enter one or more SIC codes separated by commas, e.g. 46380, 46230.",
    )
    include_all_sic = st.checkbox(
        "Require all SIC codes",
        value=False,
        help="When selected, a company must contain every entered SIC code. Otherwise, any entered code is sufficient.",
    )

    st.header("3. Enrichment")
    st.info("The Companies House API key is managed through Streamlit Secrets.")
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

companies_name_column = _find_column(companies.columns, "company_name")
companies_number_column = _find_column(companies.columns, "company_number")
companies_sic_column = _find_column(companies.columns, "nature_of_business")
trade_name_column = _find_column(trade.columns, "CompanyName")

missing = []
if not companies_name_column:
    missing.append("company_name")
if not companies_number_column:
    missing.append("company_number")
if not companies_sic_column:
    missing.append("nature_of_business")
if not trade_name_column:
    missing.append("CompanyName")

if missing:
    st.error("The uploaded files are missing required columns: " + ", ".join(missing))
    st.write("Companies House columns detected:", list(companies.columns))
    st.write("UK Trade Info columns detected:", list(trade.columns))
    st.stop()

companies = companies.copy()
trade = trade.copy()
companies["_match_key"] = companies[companies_name_column].map(normalise_name)
trade["_match_key"] = trade[trade_name_column].map(normalise_name)
trade_keys = set(trade.loc[trade["_match_key"].ne(""), "_match_key"])

matches = companies[companies["_match_key"].isin(trade_keys)].copy()

sic_codes = [
    code.strip()
    for code in re.split(r"[,;\s]+", sic_filter)
    if code.strip()
]

if sic_codes:
    def sic_matches(value: Any) -> bool:
        text = "" if pd.isna(value) else str(value)
        company_codes = set(re.findall(r"\d{5}", text))
        if include_all_sic:
            return set(sic_codes).issubset(company_codes)
        return bool(company_codes.intersection(sic_codes))

    matches = matches[matches[companies_sic_column].map(sic_matches)]

matches = matches.drop_duplicates(subset=[companies_number_column])
matches = matches.rename(
    columns={
        companies_name_column: "company_name",
        companies_number_column: "company_number",
        companies_sic_column: "nature_of_business",
    }
)
matches = matches.drop(columns=["_match_key"])

metric_1, metric_2, metric_3 = st.columns(3)
metric_1.metric("Companies House rows", f"{len(companies):,}")
metric_2.metric("UK Trade Info rows", f"{len(trade):,}")
metric_3.metric("Matched companies", f"{len(matches):,}")

if sic_codes:
    st.caption(
        f"SIC filter: {', '.join(sic_codes)} — "
        + ("all codes required" if include_all_sic else "any code accepted")
    )

if matches.empty:
    st.warning("No matches found after company-name and SIC-code filtering.")
    st.stop()

if enrich:
    api_key = get_api_key()
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
        "Company names are converted to uppercase, punctuation is removed, '&' is "
        "converted to 'AND', LTD/LIMITED is removed, and repeated spaces are collapsed. "
        "SIC codes are extracted as five-digit codes from nature_of_business. "
        "The app uses deterministic matching rather than fuzzy matching."
    )
            if len(df.columns) > 1:
                return df
        except Exception as exc:
            errors.append(f"{kwargs}: {exc}")

    fallback_attempts = [
        {"sep": ",", "encoding": "utf-8-sig"},
        {"sep": ";", "encoding": "utf-8-sig"},
        {"sep": "\t", "encoding": "utf-8-sig"},
        {"sep": "|", "encoding": "utf-8-sig"},
        {"sep": None, "encoding": "utf-8-sig"},
        {"sep": ",", "encoding": "cp1252"},
    ]

    for kwargs in fallback_attempts:
        try:
            df = pd.read_csv(
                io.BytesIO(raw),
                engine="python",
                **kwargs,
                on_bad_lines="warn",
            )
            if len(df.columns) > 1:
                st.warning(
                    "The uploaded CSV contains one or more malformed rows. "
                    "Those rows were skipped during import. Please check the "
                    "original file if matches appear to be missing."
                )
                return df
        except Exception as exc:
            errors.append(f"fallback {kwargs}: {exc}")

    raise ValueError(
        "Could not read the uploaded CSV. The file has inconsistent columns, "
        "an incorrect delimiter, or malformed quoting. Last errors: "
        + " | ".join(errors[-3:])
    )


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


def get_api_key() -> str:
    try:
        api_key = st.secrets["COMPANIES_HOUSE_API_KEY"]
    except KeyError:
        st.error(
            "The Companies House API key is not configured. Add "
            "COMPANIES_HOUSE_API_KEY to Streamlit Secrets."
        )
        st.stop()
    except FileNotFoundError:
        st.error("Streamlit Secrets are not available in this environment.")
        st.stop()

    if not isinstance(api_key, str) or not api_key.strip():
        st.error("COMPANIES_HOUSE_API_KEY is empty in Streamlit Secrets.")
        st.stop()
    return api_key.strip()


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
    st.info("The Companies House API key is managed through Streamlit Secrets.")
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
    api_key = get_api_key()
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
