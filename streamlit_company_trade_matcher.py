import streamlit as st
import pandas as pd

st.set_page_config(page_title="CSV Column A & Company Number Matcher", page_icon="📊", layout="centered")

st.title("CSV Column A & Company Number Matcher")
st.write(
    "Upload two CSV files. The app will compare the first column (column A) in each file "
    "and, for the file that has a 'company_number' column, display the matching company "
    "names together with their company numbers."
)

# File uploaders
col1, col2 = st.columns(2)
with col1:
    file1 = st.file_uploader("Upload first CSV (company names)", type=["csv"], key="file1")
with col2:
    file2 = st.file_uploader("Upload second CSV (names + company_number)", type=["csv"], key="file2")

if file1 is not None and file2 is not None:
    try:
        # First file: treat header as not needed, skip header row, focus on column A
        df1 = pd.read_csv(
            file1,
            header=None,
            skiprows=1,
            on_bad_lines="skip",
            engine="python",
        )

        # Second file: keep header so we can use 'company_number', skip malformed lines
        df2 = pd.read_csv(
            file2,
            on_bad_lines="skip",
            engine="python",
        )
    except Exception as e:
        st.error(f"Error reading one of the files: {e}")
    else:
        # Basic structural checks
        if df1.shape[1] == 0 or df2.shape[1] == 0:
            st.error("One of the CSV files has no columns.")
        elif "company_number" not in df2.columns:
            st.error(
                "The second CSV does not contain a 'company_number' column. "
                "Please upload the file that has column B titled 'company_number'."
            )
        else:
            # Column A (first column) from each dataframe
            colA_1 = df1.iloc[:, 0].dropna().astype(str)
            # For df2, use first column as company name / key
            colA_2 = df2.iloc[:, 0].dropna().astype(str)

            # Intersection of company names in column A
            matches = sorted(set(colA_1) & set(colA_2))

            st.subheader("Matched company names with company numbers")

            if matches:
                # Filter df2 for rows where column A value is in the matched list
                mask = df2.iloc[:, 0].astype(str).isin(matches)
                matched_rows = df2.loc[mask, [df2.columns[0], "company_number"]]

                # Optional: rename columns for display clarity
                matched_rows = matched_rows.rename(columns={
                    df2.columns[0]: "Company name",
                    "company_number": "Company number",
                })

                st.success(f"Found {len(matched_rows)} matching company name(s).")
                st.dataframe(matched_rows, use_container_width=True)
            else:
                st.info("No matching company names found in column A between the two files.")

            # Optional: show a preview
            with st.expander("Preview column A and company_number from second CSV"):
                preview_cols = [df2.columns[0], "company_number"]
                st.dataframe(df2[preview_cols].head(10), use_container_width=True)
else:
    st.info("Please upload both CSV files to run the comparison.")
