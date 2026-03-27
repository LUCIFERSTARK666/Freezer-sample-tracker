import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Biochemistry Freezer Manager", layout="wide")
st.title("Freezer Management System")
st.markdown("Department of Biochemistry | KMC Manipal")

# --- 2. DATABASE CONNECTION ---
url = "https://fhfegywetoavcfwbteye.supabase.co"
key = "sb_publishable_phs0oKRBj7KBwt4NauMAFw_BttBSqCe"

@st.cache_resource
def init_connection():
    return create_client(url, key)

conn = init_connection()

def get_users():
    try:
        res = conn.table("users").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame(columns=["userid", "password", "guide_name", "last_date"])

def get_samples():
    try:
        res = conn.table("samples").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except:
        return pd.DataFrame()

user_df = get_users()
USER_LIST = user_df['userid'].tolist() if not user_df.empty else []

# --- 3. SIDEBAR AUTHENTICATION ---
st.sidebar.header("Authentication")
selected_user = st.sidebar.selectbox("Select User ID", ["Select"] + USER_LIST)
input_pass = st.sidebar.text_input("Enter Password", type="password")

if selected_user != "Select" and input_pass:
    is_admin = (selected_user == "Admin" and input_pass == "Biochem000")
    user_data = user_df[user_df['userid'] == selected_user]
    is_valid_user = not user_data.empty and str(user_data.iloc[0]['password']) == input_pass

    if is_admin or is_valid_user:
        st.sidebar.success(f"Verified: {selected_user}")
        
        # --- TAB NAVIGATION ---
        if is_admin:
            tab1, tab2, tab3, tab4 = st.tabs(["📥 Log Sample", "📋 Master Log", "📊 Analytics", "⚙️ Admin Panel"])
        else:
            tab1, tab2 = st.tabs(["📥 Log Sample", "📋 My History"])

        # --- TAB 1: LOG SAMPLE ---
        with tab1:
            st.subheader("New Entry")
            with st.form("entry_form", clear_on_submit=True):
                f_type = st.selectbox("Freezer Type", ["-80 Freezer", "-20 Freezer"])
                u_name = st.selectbox("Unit Name", ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["ElanPro White", "ElanPro Grey"])
                b_guide = st.text_input("Guide Name (Biochemistry)")
                box_id = st.text_input("Box ID / Label")
                count = st.number_input("Total Number of Boxes", min_value=1)
                if st.form_submit_button("Submit"):
                    log_data = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "userid": selected_user, "biochem_guide": b_guide,
                        "freezer": f_type, "unit": u_name, "box_id": box_id, "box_count": int(count)
                    }
                    conn.table("samples").insert(log_data).execute()
                    st.cache_resource.clear()
                    st.success("Log Saved!")
                    st.rerun()

        # --- TAB 2: MASTER LOG (THE LOST SECTION) ---
        with tab2:
            df_samples = get_samples()
            if not df_samples.empty:
                if is_admin:
                    st.subheader("Master Log (All Users)")
                    search = st.text_input("Search Box/User ID").lower()
                    view_df = df_samples
                    if search:
                        view_df = df_samples[df_samples['box_id'].str.lower().contains(search) | df_samples['userid'].str.lower().contains(search)]
                else:
                    st.subheader("My Sample History")
                    view_df = df_samples[df_samples['userid'] == selected_user]
                
                st.dataframe(view_df.sort_values('timestamp', ascending=False), use_container_width=True)
                csv = view_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Log (CSV)", csv, "freezer_log.csv", "text/csv")
            else:
                st.info("No logs found in the database.")

        # --- TAB 3: ANALYTICS ---
        if is_admin:
            with tab3:
                st.subheader("📊 Graphical View")
                all_s = get_samples()
                if not all_s.empty:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("Occupancy by Freezer")
                        st.bar_chart(all_s.groupby('freezer')['box_count'].sum())
                    with c2:
                        st.write("User-wise Distribution")
                        st.bar_chart(all_s.groupby('userid')['box_count'].sum())

        # --- TAB 4: ADMIN PANEL ---
        if is_admin:
            with tab4:
                st.subheader("User Management")
                st.table(user_df[['userid', 'guide_name', 'last_date']])
    else:
        st.sidebar.error("Invalid credentials.")
else:
    st.info("Please login to access the logs.")

# --- HELP POPOVER ---
st.sidebar.markdown("---")
for _ in range(15): st.sidebar.write("")
with st.sidebar.popover("Help"):
    h_id = st.text_input("User ID for Support")
    if h_id:
        st.markdown(f'<a href="mailto:biochem@manipal.edu?subject=Support&body=User:{h_id}" style="display:block;padding:10px;background:#4f8bf9;color:white;text-align:center;border-radius:5px;text-decoration:none;">📧 Email Support</a>', unsafe_allow_html=True)
