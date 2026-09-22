import re
from typing import Any

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Company Name Matcher",
    page_icon="🔎",
    layout="wide",
)


def normalise_name(value: Any) -> str:
    """
    Create a comparison key for a company name.

    This keeps the original values unchanged for display but makes matching
    tolerant of case, punctuation, LTD/LIMITED, ampersands, and whitespace.
    """
    if pd.isna(value):
        return ""

    text = str(value)
    text = text.replace("\u00a0", " ")
    text = text.strip().upper()
    text = text.replace("&", " AND ")
    text = re.sub(r"\bLIMITED\b|\bLTD\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


st.title("Company Name Matcher")

st.write(
    "This app compares the complete first column of the first uploaded CSV "
    "with the complete first column of the second uploaded CSV. Matching "
    "companies are returned from the first file."
)


with st.sidebar:
    st.header("Upload files")

    first_file = st.file_uploader(
        "1. Companies House CSV",
        type=["csv"],
        help=(
            "The first column must contain company names. "
            "The second column must contain company numbers."
        ),
    )

    second_file = st.file_uploader(
        "2. UK Trade Info CSV",
        type=["csv"],
        help="The first column must contain company names.",
    )


if first_file is None or second_file is None:
    st.info("Upload both CSV files in the sidebar to begin.")
    st.stop()


try:
    first_dataframe = pd.read_csv(
        first_file,
        engine="python",
        on_bad_lines="warn",
    )

    second_dataframe = pd.read_csv(
        second_file,
        engine="python",
        on_bad_lines="warn",
    )

except Exception as exc:
    st.error(f"Could not read the uploaded CSV: {exc}")
    st.stop()


if first_dataframe.shape[1] < 2:
    st.error(
        "The first CSV must contain at least two columns. "
        "Column A must contain company names and column B must contain "
        "company numbers."
    )
    st.stop()


if second_dataframe.shape[1] < 1:
    st.error(
        "The second CSV must contain at least one column. "
        "Column A must contain company names."
    )
    st.stop()


first_name_column = first_dataframe.columns[0]
first_number_column = first_dataframe.columns[1]
second_name_column = second_dataframe.columns[0]


first_name_values = first_dataframe.iloc[:, 0].map(normalise_name)
second_name_values = second_dataframe.iloc[:, 0].map(normalise_name)


second_column_values = {
    value
    for value in second_name_values.tolist()
    if value
}


match_mask = first_name_values.isin(second_column_values)


matches = first_dataframe.loc[
    match_mask,
    [first_name_column, first_number_column],
].copy()


matches.columns = [
    "company_name",
    "company_number",
]


matches = matches.drop_duplicates(
    subset=["company_number"]
)


col1, col2, col3 = st.columns(3)

col1.metric(
    "Rows in first file",
    f"{len(first_dataframe):,}",
)

col2.metric(
    "Rows in second file",
    f"{len(second_dataframe):,}",
)

col3.metric(
    "Matched companies",
    f"{len(matches):,}",
)


st.caption(
    f"Comparing the complete first column "
    f"'{first_name_column}' from the first file with the complete first "
    f"column '{second_name_column}' from the second file."
)


if matches.empty:
    st.warning(
        "No matching company names were found between the two columns."
    )

else:
    st.subheader("Matching companies")

    st.dataframe(
        matches,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download matches as CSV",
        data=matches.to_csv(index=False).encode("utf-8-sig"),
        file_name="matching_companies.csv",
        mime="text/csv",
    )


with st.expander("Matching logic"):
    st.write(
        "The entire first column of each uploaded file is used. Every "
        "non-empty value in the second file's first column is placed into "
        "a set. Every value in the first file's first column is then checked "
        "against that set. If it exists, that first-file row is returned."
    )

    st.write(
        "Matching ignores differences in capitalisation, punctuation, "
        "LTD/LIMITED, ampersands, and repeated spaces."
    )
