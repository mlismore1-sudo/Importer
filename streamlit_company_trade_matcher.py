import streamlit as st
import pandas as pd
import requests
from urllib.parse import quote_plus

st.set_page_config(page_title="CSV Column A Matcher + Enrichment", page_icon="📊", layout="centered")

st.title("CSV Column A Matcher + Companies House Enrichment")
st.write(
    "Upload two CSV files. The app compares column A (first column) in both files "
    "and displays the matching company names together with their company numbers "
    "from the second file. Optionally, you can enrich the matched companies using "
    "the Companies House API to retrieve director information and useful links."
)

# File uploaders
col1, col2 = st.columns(2)
with col1:
    file1 = st.file_uploader("Upload first CSV (names only)", type=["csv"], key="file1")
with col2:
    file2 = st.file_uploader("Upload second CSV (names + company_number in column B)", type=["csv"], key="file2")


def clean_company_name_for_search(name: str) -> str:
    """Remove common suffixes like Ltd/Limited and trim whitespace for Google search."""
    if not isinstance(name, str):
        return ""
    n = name.strip()
    # Case-insensitive removal of common company suffixes
    for suffix in [" LTD", " LIMITED", " Ltd", " Limited"]:
        if n.upper().endswith(suffix.strip().upper()):
            n = n[: -len(suffix)].strip()
            break
    return n


def fetch_officer_enrichment(company_number: str, api_key: str, max_directors: int = 4):
    """Fetch officer data from Companies House for one company_number.

    Returns a dict with:
      - director_count: number of active directors
      - directors: list of {name, profile_url} up to max_directors
    """
    base_url = "https://api.company-information.service.gov.uk/company/{company_number}/officers"
    url = base_url.format(company_number=company_number)

    try:
        resp = requests.get(url, auth=(api_key, ""), timeout=10)
    except Exception:
        return {"director_count": None, "directors": []}

    if resp.status_code != 200:
        return {"director_count": None, "directors": []}

    data = resp.json()
    items = data.get("items", [])

    directors = []
    for item in items:
        role = (item.get("officer_role") or "").lower()
        resigned_on = item.get("resigned_on")
        if "director" in role and not resigned_on:
            name = item.get("name")

            # Try to build a Companies House profile URL for the officer
            profile_url = None
            links = item.get("links") or {}
            officer_links = links.get("officer") or {}
            appointments_path = None
            if isinstance(officer_links, dict):
                appointments_path = officer_links.get("appointments")

            if isinstance(appointments_path, str):
                # appointments_path is like "/officers/{officer_id}/appointments"
                parts = appointments_path.strip("/").split("/")
                if len(parts) >= 2 and parts[0] == "officers":
                    officer_id = parts[1]
                    profile_url = (
                        "https://find-and-update.company-information.service.gov.uk/officer/"
                        f"{officer_id}/appointments"
                    )

            directors.append({"name": name, "profile_url": profile_url})
            if len(directors) >= max_directors:
                break

    director_count = sum(
        1
        for item in items
        if "director" in (item.get("officer_role") or "").lower()
        and not item.get("resigned_on")
    )

    return {"director_count": director_count, "directors": directors}


matched_rows = None

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
                colA_2_full = df2.iloc[:, 0].astype(str).str.strip()
                mask = colA_2_full.isin(matches)

                # Column A (index 0) and column B (index 1) from df2
                matched_rows = df2.loc[mask, [0, 1]].copy()
                matched_rows.columns = ["Company name", "Company number"]

                st.success(f"Found {len(matched_rows)} matching company name(s).")
                st.dataframe(matched_rows, use_container_width=True)
            else:
                st.info("No matching company names found in column A between the two files.")

            with st.expander("Preview column A and B from second CSV"):
                preview = df2.iloc[:, :2].copy()
                preview.columns = ["Column A", "Column B (company_number)"]
                st.dataframe(preview.head(10), use_container_width=True)
else:
    st.info("Please upload both CSV files to run the comparison.")


# --- Enrichment section ---
if matched_rows is not None and not matched_rows.empty:
    st.subheader("Enrich matched companies with Companies House data")

    api_key = st.text_input(
        "Companies House API key",
        type="password",
        help=(
            "Your Companies House REST API key (used as the username in Basic auth). "
            "You can also store this in Streamlit secrets and adapt the code accordingly."
        ),
    )

    if st.button("Enrich results"):
        if not api_key:
            st.error("Please enter your Companies House API key to enrich results.")
        else:
            total = len(matched_rows)
            progress_text = "Enrichment in progress. Please wait."
            progress_bar = st.progress(0, text=progress_text)

            enrichment_rows = []
            for idx, (_, row) in enumerate(matched_rows.iterrows(), start=1):
                company_name = str(row["Company name"])
                company_number = str(row["Company number"])

                enrichment = fetch_officer_enrichment(company_number, api_key)
                director_count = enrichment.get("director_count")
                directors = enrichment.get("directors", [])

                # Prepare up to 4 director name/profile pairs
                director_data = {}
                for i in range(4):
                    if i < len(directors):
                        director_data[f"Director {i+1} name"] = directors[i].get("name")
                        director_data[f"Director {i+1} profile"] = directors[i].get("profile_url")
                    else:
                        director_data[f"Director {i+1} name"] = None
                        director_data[f"Director {i+1} profile"] = None

                # Google search link without Ltd/Limited
                clean_name = clean_company_name_for_search(company_name)
                google_url = None
                if clean_name:
                    google_url = "https://www.google.com/search?q=" + quote_plus(clean_name)

                enrichment_rows.append(
                    {
                        "Company name": company_name,
                        "Company number": company_number,
                        "Director count": director_count,
                        **director_data,
                        "Google search": google_url,
                    }
                )

                # Update progress bar
                percent_complete = int(idx / total * 100)
                progress_bar.progress(percent_complete, text=progress_text)

            progress_bar.empty()

            enriched_df = pd.DataFrame(enrichment_rows)

            st.success("Enrichment complete.")
            st.dataframe(enriched_df, use_container_width=True)
