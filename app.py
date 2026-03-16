import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

st.set_page_config(page_title="SOX Control Monitoring Platform", layout="wide")

UPLOAD_DIR = "data/uploads"
LOG_FILE = "data/upload_log.csv"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------

if "df" not in st.session_state:
    st.session_state.df = None

if "changes" not in st.session_state:
    st.session_state.changes = pd.DataFrame()

# ---------------------------------------------------
# HEADER
# ---------------------------------------------------

st.markdown("""
<div style="background:linear-gradient(90deg,#0f172a,#1e3a8a);
padding:30px;border-radius:12px;color:white;margin-bottom:20px;">
<h1>SOX Control Monitoring Platform</h1>
<p>Internal Audit Analytics Dashboard</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Page",
    ["Executive Dashboard","Change Analysis","Upload History","Raw Data"]
)

uploaded_file = st.sidebar.file_uploader(
    "Upload SOX Dashboard",
    type=["xlsx"]
)

# ---------------------------------------------------
# DATASET VALIDATION
# ---------------------------------------------------

def validate_dataset(df):

    required = [
        "Project",
        "Task",
        "Status",
        "Assignee",
        "Reviewer",
        "ID",
        "Reliance",
        "Due Date"
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()

# ---------------------------------------------------
# SAVE FILE
# ---------------------------------------------------

def save_file(uploaded_file):

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    filename = f"{timestamp}_sox_dashboard.xlsx"

    path = os.path.join(UPLOAD_DIR, filename)

    with open(path,"wb") as f:
        f.write(uploaded_file.getbuffer())

    return filename,path

# ---------------------------------------------------
# UPLOAD LOG
# ---------------------------------------------------

def update_log(filename,df):

    entry = {
        "Upload Time":datetime.now(),
        "File Name":filename,
        "Tasks":len(df)
    }

    new_row = pd.DataFrame([entry])

    if os.path.exists(LOG_FILE):

        log = pd.read_csv(LOG_FILE)
        log = pd.concat([log,new_row],ignore_index=True)

    else:

        log = new_row

    log.to_csv(LOG_FILE,index=False)

# ---------------------------------------------------
# LOAD FILES
# ---------------------------------------------------

def load_latest_files():

    files = sorted(os.listdir(UPLOAD_DIR))

    files = [f for f in files if f.endswith(".xlsx")]

    if len(files)==0:
        return None,None

    latest_file = os.path.join(UPLOAD_DIR,files[-1])
    latest_df = pd.read_excel(latest_file,sheet_name="IA data")

    previous_df = None

    if len(files)>1:

        previous_file = os.path.join(UPLOAD_DIR,files[-2])
        previous_df = pd.read_excel(previous_file,sheet_name="IA data")

    return latest_df,previous_df

# ---------------------------------------------------
# CHANGE DETECTION
# ---------------------------------------------------

def compare_versions(old_df,new_df):

    key="Task"

    old_df[key]=old_df[key].astype(str).str.strip()
    new_df[key]=new_df[key].astype(str).str.strip()

    old_df=old_df.set_index(key)
    new_df=new_df.set_index(key)

    fields=[
        "Project",
        "Status",
        "Assignee",
        "Reviewer",
        "ID",
        "Reliance",
        "Due Date"
    ]

    changes=[]

    common=old_df.index.intersection(new_df.index)

    for task in common:

        for field in fields:

            old_val=old_df.loc[task,field]
            new_val=new_df.loc[task,field]

            if isinstance(old_val,pd.Series):
                old_val=old_val.iloc[0]

            if isinstance(new_val,pd.Series):
                new_val=new_val.iloc[0]

            if str(old_val).strip()!=str(new_val).strip():

                changes.append({
                    "Task":task,
                    "Field Changed":field,
                    "Old Value":old_val,
                    "New Value":new_val
                })

    new_tasks=new_df.index.difference(old_df.index)

    for task in new_tasks:

        changes.append({
            "Task":task,
            "Field Changed":"New Task",
            "Old Value":"N/A",
            "New Value":"Added"
        })

    removed_tasks=old_df.index.difference(new_df.index)

    for task in removed_tasks:

        changes.append({
            "Task":task,
            "Field Changed":"Removed Task",
            "Old Value":"Removed",
            "New Value":"N/A"
        })

    return pd.DataFrame(changes)

# ---------------------------------------------------
# HANDLE UPLOAD
# ---------------------------------------------------

if uploaded_file:

    filename,path=save_file(uploaded_file)

    df=pd.read_excel(path,sheet_name="IA data")

    validate_dataset(df)

    update_log(filename,df)

# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------

latest_df,previous_df=load_latest_files()

if latest_df is not None:
    st.session_state.df=latest_df

if latest_df is not None and previous_df is not None:
    st.session_state.changes=compare_versions(previous_df,latest_df)

# ---------------------------------------------------
# EXECUTIVE DASHBOARD
# ---------------------------------------------------

if page=="Executive Dashboard":

    df=st.session_state.df

    if df is not None:

        total=len(df)

        status_counts=df["Status"].value_counts()

        complete=status_counts.get("Complete",0)
        review_complete=status_counts.get("Review Complete",0)

        col1,col2,col3=st.columns(3)

        col1.metric("Total Tasks",total)
        col2.metric("Complete",complete)
        col3.metric("Review Complete",review_complete)

        st.divider()

        colA,colB=st.columns(2)

        with colA:

            fig=px.pie(
                df,
                names="Status",
                hole=0.45,
                title="Task Status Distribution"
            )

            st.plotly_chart(fig,use_container_width=True)

        with colB:

            status_counts=status_counts.reset_index()

            fig2=px.bar(
                status_counts,
                x="Status",
                y="count",
                color="Status",
                title="Status Breakdown"
            )

            st.plotly_chart(fig2,use_container_width=True)

    else:

        st.info("Upload dashboard to begin analysis")

# ---------------------------------------------------
# CHANGE ANALYSIS
# ---------------------------------------------------

elif page=="Change Analysis":

    changes=st.session_state.changes

    st.subheader("Changes Since Last Upload")

    if not changes.empty:

        col1,col2=st.columns(2)

        col1.metric("Total Changes",len(changes))
        col2.metric("Affected Tasks",changes["Task"].nunique())

        st.dataframe(changes)

        change_counts=changes["Field Changed"].value_counts()

        chart_df=pd.DataFrame({
            "Change Type":change_counts.index,
            "Count":change_counts.values
        })

        fig=px.bar(
            chart_df,
            x="Change Type",
            y="Count",
            color="Change Type",
            title="Detected Changes"
        )

        st.plotly_chart(fig,use_container_width=True)

    else:

        st.info("Upload at least two dashboards to detect changes")

# ---------------------------------------------------
# UPLOAD HISTORY
# ---------------------------------------------------

elif page=="Upload History":

    st.subheader("Upload History")

    if os.path.exists(LOG_FILE):

        log=pd.read_csv(LOG_FILE)

        st.dataframe(log)

        for _,row in log.iterrows():

            path=os.path.join(UPLOAD_DIR,row["File Name"])

            if os.path.exists(path):

                with open(path,"rb") as f:

                    st.download_button(
                        label=f"Download {row['File Name']}",
                        data=f,
                        file_name=row["File Name"]
                    )

    else:

        st.info("No uploads recorded")

# ---------------------------------------------------
# RAW DATA
# ---------------------------------------------------

elif page=="Raw Data":

    df=st.session_state.df

    if df is not None:

        st.dataframe(df)

    else:

        st.info("Upload dashboard to view raw data")
