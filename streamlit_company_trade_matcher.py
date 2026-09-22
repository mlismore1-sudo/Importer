import streamlit as st
import pandas as pd

st.set_page_config(page_title="CSV Column A Matcher", page_icon="📊", layout="centered")

st.title("CSV Column A Matcher")
st.write(
    "Upload two CSV files. The app will compare the first column (column A) in each "
    "file, ignoring the header row, and display any values that appear in both."
)

# File uploaders
col1, col2 = st.columns(2)
with col1:
    file1 = st.file_uploader("Upload first CSV", type=["csv"], key="file1")
with col2:
    file2 = st.file_uploader("Upload second CSV", type=["csv"], key="file2")

if file1 is not None and file2 is not None:
    try:
        # Read both files:
        # - skip the first physical row (assumed header)
        # - do not treat any row as column names
        # - skip malformed lines instead of erroring
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
        if df1.shape[1] == 0 or df2.shape[1] == 0:
            st.error("One of the CSV files has no columns.")
        else:
            # Take the first column (column index 0) from each dataframe
            colA_1 = df1.iloc[:, 0].dropna().astype(str)
            colA_2 = df2.iloc[:, 0].dropna().astype(str)

            set1 = set(colA_1)
            set2 = set(colA_2)
            matches = sorted(set1 & set2)

            st.subheader("Values present in column A of both files")

            if matches:
                st.success(f"Found {len(matches)} matching value(s) in column A.")
                result_df = pd.DataFrame({"Matching values (column A)": matches})
                st.dataframe(result_df, use_container_width=True)
            else:
                st.info("No matching values found in column A between the two files.")

            # Optional: show a preview of column A from each CSV
            with st.expander("Preview column A from each CSV"):
                st.markdown("**First CSV – column A (first 10 values)**")
                st.write(colA_1.head(10))

                st.markdown("**Second CSV – column A (first 10 values)**")
                st.write(colA_2.head(10))
else:
    st.info("Please upload both CSV files to run the comparison.")
