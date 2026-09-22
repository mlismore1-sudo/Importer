import io
import re
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Company Name Matcher", page_icon="🔎", layout="wide")


@st.cache_data(show_spinner=False)
def read_csv_bytes(raw: bytes) -> pd.DataFrame:
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
                on_bad_lines="warn",
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

if second_dataframe.shape[1] < 1:
    st.error("The second CSV must contain at least one column.")
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
