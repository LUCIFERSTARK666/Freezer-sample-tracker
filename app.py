import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- 1. PAGE SETUP & KMC LOGO ---
st.set_page_config(page_title="Freezer Manager", layout="wide")

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
        
        # Tabs Logic
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

                if st.form_submit_button("Submit to Cloud"):
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

        # --- TAB 2: MASTER LOG (EDIT/DELETE LOGS) ---
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

                # ADMIN DUAL EDIT/DELETE LOG ENTRIES
                if is_admin and not view_df.empty:
                    st.markdown("---")
                    st.subheader("⚙️ Manage Log Entries")
                    manage_options = [f"{r['userid']} | {r['box_id']} | {r['timestamp']}" for _, r in view_df.iterrows()]
                    selected_entry = st.selectbox("Select a log to edit/delete", ["Select"] + manage_options)
                    if selected_entry != "Select":
                        idx = manage_options.index(selected_entry)
                        target_row = view_df.iloc[idx - 1]
                        c_edit, c_del = st.columns([2, 1])
                        with c_edit:
                            with st.form("edit_log_form"):
                                e_box = st.text_input("Edit Box ID", value=target_row['box_id'])
                                e_count = st.number_input("Edit Count", value=int(target_row['box_count']), min_value=1)
                                if st.form_submit_button("Update Log"):
                                    conn.table("samples").update({"box_id": e_box, "box_count": e_count}).eq("timestamp", target_row['timestamp']).eq("userid", target_row['userid']).execute()
                                    st.cache_resource.clear()
                                    st.rerun()
                        with c_del:
                            if st.button("🗑️ Delete Log Entry"):
                                conn.table("samples").delete().eq("timestamp", target_row['timestamp']).eq("userid", target_row['userid']).execute()
                                st.cache_resource.clear()
                                st.rerun()
            else:
                st.info("No logs found.")

        # --- TAB 3: ANALYTICS ---
        if is_admin:
            with tab3:
                st.subheader("📊 Analytics")
                if not df_samples.empty:
                    st.bar_chart(df_samples.groupby('userid')['box_count'].sum())

        # --- TAB 4: ADMIN PANEL (RESTORED USER AUTHORIZATION) ---
        if is_admin:
            with tab4:
                st.subheader("👤 User Access Management")
                col_left, col_right = st.columns(2)
                
                with col_left:
                    st.markdown("##### Add/Update Student")
                    with st.form("add_user_form"):
                        n_id = st.text_input("Student User ID")
                        n_pw = st.text_input("Set Password")
                        n_gd = st.text_input("Primary Guide Name")
                        n_ex = st.date_input("Storage Expiry Date")
                        if st.form_submit_button("Authorize Student"):
                            conn.table("users").upsert({"userid": n_id, "password": n_pw, "guide_name": n_gd, "last_date": str(n_ex)}).execute()
                            st.cache_resource.clear()
                            st.success(f"User {n_id} Authorized!")
                            st.rerun()
                
                with col_right:
                    st.markdown("##### Remove Access")
                    student_only = [u for u in USER_LIST if u != "Admin"]
                    user_to_del = st.selectbox("Select Student to Remove", ["Select"] + student_only)
                    if user_to_del != "Select" and st.button("Confirm Permanent Removal"):
                        conn.table("users").delete().eq("userid", user_to_del).execute()
                        st.cache_resource.clear()
                        st.warning(f"User {user_to_del} removed.")
                        st.rerun()
                
                st.markdown("---")
                st.write("**Authorized User List:**")
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
