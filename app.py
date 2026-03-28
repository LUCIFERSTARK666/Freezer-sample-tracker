import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- 1. PAGE SETUP & LOGO ---
st.set_page_config(page_title="Biochemistry Freezer Manager", layout="wide")

# Centering the Logo
LOGO_URL = "https://cdn-prod.mybharats.in/organization/DL-ns-d9cbe78f-d9b2-4e20-baf0-e0747653f0bd_kmclogo.jpg"
col_l, col_m, col_r = st.columns([2, 2, 2])
with col_m:
    st.image(LOGO_URL, width=350) 

st.markdown("<h1 style='text-align: center;'>Freezer Management System</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-weight: bold;'>Department of Biochemistry | KMC Manipal</p>", unsafe_allow_html=True)
st.markdown("---")

# --- 2. DATABASE CONNECTION ---
url = "https://fhfegywetoavcfwbteye.supabase.co"
key = "sb_publishable_phs0oKRBj7KBwt4NauMAFw_BttBSqCe"

@st.cache_resource
def init_connection():
    return create_client(url, key)

conn = init_connection()

# --- 3. DATA FETCHING (Ensuring it matches your DB) ---
def get_users():
    try:
        res = conn.table("users").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame(columns=["userid", "password", "guide_name", "last_date"])

def get_samples():
    try:
        # Fetching everything without filters first to ensure visibility
        res = conn.table("samples").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except:
        return pd.DataFrame()

user_df = get_users()
USER_LIST = user_df['userid'].tolist() if not user_df.empty else []

# --- 4. SIDEBAR AUTHENTICATION ---
st.sidebar.header("Authentication")
selected_user = st.sidebar.selectbox("Select User ID", ["Select"] + USER_LIST)
input_pass = st.sidebar.text_input("Enter Password", type="password")

if selected_user != "Select" and input_pass:
    is_admin = (selected_user == "Admin" and input_pass == "Biochem000")
    user_data = user_df[user_df['userid'] == selected_user]
    is_valid_user = not user_data.empty and str(user_data.iloc[0]['password']) == input_pass

    if is_admin or is_valid_user:
        st.sidebar.success(f"Verified: {selected_user}")
        
        # Admin gets 4 tabs, Students get 2
        if is_admin:
            tab1, tab2, tab3, tab4 = st.tabs(["📥 Log Sample", "📋 Master Log", "📊 Analytics", "⚙️ Admin Panel"])
        else:
            tab1, tab2 = st.tabs(["📥 Log Sample", "📋 My History"])

        # --- TAB 1: LOG SAMPLE ---
        with tab1:
            st.subheader("New Entry")
            with st.form("entry_form", clear_on_submit=True):
                f_type = st.selectbox("Freezer", ["-80 Freezer", "-20 Freezer"])
                u_name = st.selectbox("Unit", ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["ElanPro White", "ElanPro Grey"])
                b_guide = st.text_input("Guide Name")
                box_id = st.text_input("Box ID (Required)")
                count = st.number_input("Total Boxes", min_value=1, step=1)
                
                if st.form_submit_button("Submit"):
                    if box_id:
                        log_data = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "userid": selected_user, "biochem_guide": b_guide,
                            "freezer": f_type, "unit": u_name, "box_id": box_id, "box_count": int(count)
                        }
                        conn.table("samples").insert(log_data).execute()
                        st.cache_resource.clear()
                        st.success("Log Saved!")
                        st.rerun()

        # --- TAB 2: MASTER LOG (THE FIX) ---
        with tab2:
            st.subheader("📋 Freezer Records")
            all_data = get_samples()
            if not all_data.empty:
                if is_admin:
                    view_df = all_data
                    search = st.text_input("🔍 Search User or Box ID").lower()
                    if search:
                        view_df = all_data[all_data['userid'].str.lower().contains(search) | all_data['box_id'].str.lower().contains(search)]
                else:
                    view_df = all_data[all_data['userid'] == selected_user]
                
                st.dataframe(view_df.sort_values('timestamp', ascending=False) if 'timestamp' in view_df.columns else view_df, use_container_width=True)
            else:
                st.info("No data found in the database.")

        # --- TAB 3: ANALYTICS (ADMIN ONLY) ---
        if is_admin:
            with tab3:
                st.subheader("📊 Visual Summary")
                if not all_data.empty:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**By Freezer Type**")
                        st.bar_chart(all_data.groupby('freezer')['box_count'].sum())
                    with c2:
                        st.write("**By User ID**")
                        st.bar_chart(all_data.groupby('userid')['box_count'].sum())

        # --- TAB 4: ADMIN PANEL ---
        if is_admin:
            with tab4:
                st.subheader("User Management")
                st.table(user_df[['userid', 'guide_name', 'last_date']])

    else:
        st.sidebar.error("Invalid credentials.")
else:
    st.info("👋 Welcome. Please select your User ID in the sidebar to begin.")

# --- HELP POPOVER (SIDEBAR BOTTOM) ---
st.sidebar.markdown("---")
for _ in range(15): st.sidebar.write("") 
with st.sidebar.popover("Help"):
    h_id = st.text_input("Your User ID", key="h_id")
    if h_id:
        body = f"Support Request from {h_id}"
        st.markdown(f'<a href="mailto:biochem@manipal.edu?body={body}" style="display:block;padding:10px;background:#4f8bf9;color:white;text-align:center;border-radius:5px;text-decoration:none;">📧 Email Support</a>', unsafe_allow_html=True)
