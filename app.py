import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- 1. PAGE SETUP & KMC LOGO ---
st.set_page_config(page_title="Freezer Manager", layout="wide")

# Centering the Logo at the top
LOGO_URL = "https://cdn-prod.mybharats.in/organization/DL-ns-d9cbe78f-d9b2-4e20-baf0-e0747653f0bd_kmclogo.jpg"
c1, c2, c3 = st.columns([2, 2, 2])
with c2:
    st.image(LOGO_URL, width=350)

st.markdown("<h1 style='text-align: center;'>Freezer Management System</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-weight: bold;'>Department of Biochemistry | Kasturba Medical College, Manipal</p>", unsafe_allow_html=True)
st.markdown("---")

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
        return pd.DataFrame(res.data)
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
        
        # Tabs - Admin gets Analytics, Students get My History
        if is_admin:
            tab1, tab2, tab3, tab4 = st.tabs(["📥 Log Sample", "📋 Master Log", "📊 Analytics", "⚙️ Admin Panel"])
        else:
            tab1, tab2 = st.tabs(["📥 Log Sample", "📋 My History"])

        # --- TAB 1: LOG SAMPLE ---
        with tab1:
            st.subheader("New Entry")
            f_type = st.selectbox("1. Freezer Type", ["-80 Freezer", "-20 Freezer"])
            u_opts = ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["ElanPro White", "ElanPro Grey"]
            u_name = st.selectbox("2. Unit Name", u_opts)

            with st.form("entry_form", clear_on_submit=True):
                st.markdown("##### Details")
                u_email = st.text_input("Your Email ID")
                b_guide = st.text_input("Guide Name (Biochemistry)")
                box_id = st.text_input("Box ID / Label (Required)")
                count = st.number_input("Total Number of Boxes", min_value=1, step=1)

                if st.form_submit_button("Submit"):
                    if box_id and b_guide:
                        log_data = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "userid": selected_user, "email": u_email,
                            "biochem_guide": b_guide, "freezer": f_type, "unit": u_name,
                            "box_id": box_id, "box_count": int(count)
                        }
                        conn.table("samples").insert(log_data).execute()
                        st.cache_resource.clear()
                        st.success("Log Saved!")
                        st.rerun()

        # --- TAB 2: MASTER LOG (WITH DELETE) ---
        with tab2:
            df_samples = get_samples()
            if not df_samples.empty:
                if is_admin:
                    st.markdown("##### 🔎 Admin Search")
                    search_q = st.text_input("Search Box ID or User ID", "").lower()
                    view_df = df_samples
                    if search_q:
                        mask = (view_df['userid'].astype(str).str.lower().str.contains(search_q) | 
                                view_df['box_id'].astype(str).str.lower().str.contains(search_q))
                        view_df = view_df[mask]
                else:
                    view_df = df_samples[df_samples['userid'] == selected_user]
                
                st.dataframe(view_df.sort_values('timestamp', ascending=False) if 'timestamp' in view_df.columns else view_df, use_container_width=True)
                
                # Download Button
                csv = view_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Log (CSV)", csv, "freezer_log.csv", "text/csv")

                # --- ADMIN DELETE SECTION ---
                if is_admin and not view_df.empty:
                    st.markdown("---")
                    st.subheader("🗑️ Delete Individual Entry (Admin Only)")
                    # Create a list of entries to choose from
                    delete_options = [f"{r['userid']} | {r['box_id']} | {r['timestamp']}" for _, r in view_df.iterrows()]
                    selected_to_delete = st.selectbox("Select entry to remove permanently", ["Select"] + delete_options)
                    
                    if selected_to_delete != "Select":
                        # Get the specific data for the selected entry
                        idx = delete_options.index(selected_to_delete)
                        target_row = view_df.iloc[idx - 1]
                        
                        st.warning(f"Are you sure you want to delete the entry for {target_row['userid']} (Box: {target_row['box_id']})?")
                        if st.button("Confirm Permanent Deletion"):
                            conn.table("samples").delete().eq("timestamp", target_row['timestamp']).eq("userid", target_row['userid']).execute()
                            st.cache_resource.clear()
                            st.success("Entry Deleted!")
                            st.rerun()
            else:
                st.info("No logs found.")

        # --- TAB 3: ANALYTICS ---
        if is_admin:
            with tab3:
                st.subheader("📊 Analytics")
                if not df_samples.empty:
                    st.bar_chart(df_samples.groupby('userid')['box_count'].sum())

        # --- TAB 4: ADMIN PANEL ---
        if is_admin:
            with tab4:
                st.subheader("⚙️ User Management")
                st.table(user_df[['userid', 'guide_name', 'last_date']])

    else:
        st.sidebar.error("Invalid credentials.")
else:
    st.info("Please login in the sidebar.")

# --- HELP POPOVER ---
st.sidebar.markdown("---")
for _ in range(15): st.sidebar.write("")
with st.sidebar.popover("Help"):
    h_user = st.text_input("User ID", key="help_id")
    if h_user:
        st.markdown(f'<a href="mailto:biochem@manipal.edu?body=User:{h_user}" style="display:block;padding:10px;background:#4f8bf9;color:white;text-align:center;border-radius:5px;text-decoration:none;">📧 Email Support</a>', unsafe_allow_html=True)
