import streamlit as st
import pandas as pd

st.set_page_config(page_title="CSV Column A Matcher", page_icon="📊", layout="centered")

st.title("CSV Column A Matcher (Name + Company Number)")
st.write(
    "Upload two CSV files. The app compares column A (first column) in both files "
    "and displays the matching company names together with their company numbers "
    "from the second file (assumed in column B)."
)

# File uploaders
col1, col2 = st.columns(2)
with col1:
    file1 = st.file_uploader("Upload first CSV (names only)", type=["csv"], key="file1")
with col2:
    file2 = st.file_uploader("Upload second CSV (names + company_number in column B)", type=["csv"], key="file2")

if file1 is not None and file2 is not None:
    try:
        # Read BOTH files in the same way:
        # - skip header row
        # - treat all remaining rows as data (no column names)
        # - skip malformed lines
        df1 = pd.read_csv(
            file1,
            header=None,
            skiprows=1,
            on_bad_lines="skip",
            engine="python",
        )
        df2 = pd.read_csv(
            file2,
            header=None,
            skiprows=1,
            on_bad_lines="skip",
            engine="python",
        )
    except Exception as e:
        st.error(f"Error reading one of the files: {e}")
    else:
        # Ensure both files have at least two columns (A and B for the second file)
        if df1.shape[1] == 0 or df2.shape[1] < 2:
            st.error("One of the CSV files does not have the expected columns.")
        else:
            # Column A (index 0) from each dataframe
            colA_1 = df1.iloc[:, 0].dropna().astype(str).str.strip()
            colA_2 = df2.iloc[:, 0].dropna().astype(str).str.strip()

            # Intersection of company names in column A
            matches = sorted(set(colA_1) & set(colA_2))

            st.subheader("Matched company names with company numbers")

            if matches:
                # Filter df2 for rows where column A value is in the matched list
                colA_2_full = df2.iloc[:, 0].astype(str).str.strip()
                mask = colA_2_full.isin(matches)

                # Select column A (index 0) and column B (index 1) from df2
                matched_rows = df2.loc[mask, [0, 1]].copy()
                matched_rows.columns = ["Company name", "Company number"]

                st.success(f"Found {len(matched_rows)} matching company name(s).")
                st.dataframe(matched_rows, use_container_width=True)
            else:
                st.info("No matching company names found in column A between the two files.")

            # Optional: show a preview of the second file's columns A and B
            with st.expander("Preview column A and B from second CSV"):
                preview = df2.iloc[:, :2].copy()
                preview.columns = ["Column A", "Column B (company_number)"]
                st.dataframe(preview.head(10), use_container_width=True)
else:
    st.info("Please upload both CSV files to run the comparison.")
