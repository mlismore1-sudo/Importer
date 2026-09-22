import streamlit as st
import pandas as pd

st.set_page_config(page_title="CSV First Column Matcher", page_icon="📊", layout="centered")

st.title("CSV First Column Matcher")
st.write(
    "Upload two CSV files. The app will compare the first column in each file and "
    "display any values that appear in both."
)

# File uploaders
col1, col2 = st.columns(2)
with col1:
    file1 = st.file_uploader("Upload first CSV", type=["csv"], key="file1")
with col2:
    file2 = st.file_uploader("Upload second CSV", type=["csv"], key="file2")

if file1 is not None and file2 is not None:
    try:
        df1 = pd.read_csv(file1)
        df2 = pd.read_csv(file2)
    except Exception as e:
        st.error(f"Error reading one of the files: {e}")
    else:
        if df1.shape[1] == 0 or df2.shape[1] == 0:
            st.error("One of the CSV files has no columns.")
        else:
            # Take the first column from each dataframe
            col1_values = df1.iloc[:, 0].dropna().astype(str)
            col2_values = df2.iloc[:, 0].dropna().astype(str)

            set1 = set(col1_values)
            set2 = set(col2_values)
            matches = sorted(set1 & set2)

            st.subheader("Matching values in first columns")

            if matches:
                st.success(f"Found {len(matches)} matching value(s).")
                result_df = pd.DataFrame({"Matching values": matches})
                st.dataframe(result_df, use_container_width=True)
            else:
                st.info("No matching values found between the first columns.")

            # Optional: show a preview of the uploaded files
            with st.expander("Preview first few rows of each CSV"):
                st.markdown("**First CSV preview**")
                st.dataframe(df1.head(), use_container_width=True)

                st.markdown("**Second CSV preview**")
                st.dataframe(df2.head(), use_container_width=True)
else:
    st.info("Please upload both CSV files to run the comparison.")
