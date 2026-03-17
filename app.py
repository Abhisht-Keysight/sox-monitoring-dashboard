import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="SOX Control Monitoring Platform", layout="wide")

# ---------------- ONEDRIVE LINKS ---------------- #

LATEST_URL = "https://keysighttech-my.sharepoint.com/:x:/g/personal/abhisht_pandey_keysight_com/IQD8IPMXGAeaT4TJjsycGI5LASf2Zb_Cemy1F-TxdLiZyQ4?download=1"
CHANGE_URL = "https://keysighttech-my.sharepoint.com/:x:/g/personal/abhisht_pandey_keysight_com/IQDN_RRiOlGjS4Jsf81KIg8fAdmYzX0Ugw2iKb6BmgfiJr0?download=1"

# ---------------- HEADER ---------------- #

st.markdown("""
<div style="background:linear-gradient(90deg,#0f172a,#1e3a8a);
padding:30px;border-radius:12px;color:white;margin-bottom:20px;">
<h1>SOX Control Monitoring Platform</h1>
<p>Internal Audit Analytics Dashboard</p>
</div>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ---------------- #

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Page",
    ["Executive Dashboard","Change Analysis","Raw Data"]
)

uploaded_file = st.sidebar.file_uploader("Upload SOX Dashboard", type=["xlsx"])

# ---------------- VALIDATION ---------------- #

def validate_dataset(df):

    required = [
        "PROCESS_UID","CYCLE","Test Name",
        "TESTS__TEST_SECTION","TESTS__STATUS",
        "TESTS__EFFECTIVENESS","TESTS__TESTER_USER",
        "TESTS__REVIEWER_USER","TESTS__SECONDARY_REVIEWER_USER",
        "TESTS__START_DATE","TESTS__END_DATE",
        "TESTS__DUE_DATE","PWC Reliance","Audit Team"
    ]

    missing=[c for c in required if c not in df.columns]

    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()

# ---------------- COMPARE ---------------- #

def compare_versions(old_df,new_df):

    key="Test Name"

    old_df[key]=old_df[key].astype(str).str.strip()
    new_df[key]=new_df[key].astype(str).str.strip()

    old_df=old_df.set_index(key)
    new_df=new_df.set_index(key)

    changes=[]

    for test in old_df.index.intersection(new_df.index):
        for col in new_df.columns:

            old=str(old_df.loc[test,col])
            new=str(new_df.loc[test,col])

            if old!=new:
                changes.append({
                    "Test Name":test,
                    "Field Changed":col,
                    "Old Value":old,
                    "New Value":new
                })

    return pd.DataFrame(changes)

# ---------------- LOAD FROM ONEDRIVE ---------------- #

@st.cache_data
def load_latest():
    try:
        return pd.read_csv(LATEST_URL)
    except:
        return None

@st.cache_data
def load_changes():
    try:
        df = pd.read_csv(CHANGE_URL)
        if df.empty:
            return None
        return df
    except:
        return None

latest_df = load_latest()
changes_df = load_changes()

# ---------------- HANDLE UPLOAD ---------------- #

if uploaded_file:

    new_df = pd.read_excel(uploaded_file, sheet_name="IA data")
    validate_dataset(new_df)

    # First upload → set base
    if "base_df" not in st.session_state:
        st.session_state.base_df = new_df
        st.session_state.latest_df = new_df
        st.info("Base file uploaded. Upload another file to detect changes.")

    else:
        # Second upload → run comparison
        old_df = st.session_state.base_df
        changes_df = compare_versions(old_df, new_df)

        st.session_state.latest_df = new_df
        st.session_state.changes_df = changes_df

        st.success("Change analysis completed")

# Override with session data
if "latest_df" in st.session_state:
    latest_df = st.session_state.latest_df

if "changes_df" in st.session_state:
    changes_df = st.session_state.changes_df

# ---------------- EXECUTIVE DASHBOARD ---------------- #

if page=="Executive Dashboard":

    if latest_df is not None:

        col1,col2=st.columns(2)

        col1.metric("Total Tests",len(latest_df))

        open_tests=latest_df[
            latest_df["TESTS__STATUS"].astype(str)
            .str.lower()
            .str.contains("open",na=False)
        ].shape[0]

        col2.metric("Open Tests",open_tests)

        c1,c2=st.columns(2)

        with c1:
            st.plotly_chart(px.pie(latest_df,names="TESTS__STATUS",hole=0.4))

        with c2:
            st.plotly_chart(px.bar(latest_df["TESTS__STATUS"].value_counts()))

    else:
        st.warning("No data available")

# ---------------- CHANGE ANALYSIS ---------------- #

elif page=="Change Analysis":

    if changes_df is None:
        st.info("Upload two files to see change analysis")
    else:
        st.dataframe(changes_df,use_container_width=True)
        st.plotly_chart(px.bar(changes_df["Field Changed"].value_counts()))

# ---------------- RAW ---------------- #

elif page=="Raw Data":

    if latest_df is not None:
        st.dataframe(latest_df)
