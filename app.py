import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- 1. PAGE SETUP & KMC LOGO ---
st.set_page_config(page_title="Freezer Manager", layout="wide")

# Centering the Logo
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

# --- 3. DATA FETCHING (STABLE & FRESH) ---
def get_users():
    try:
        res = conn.table("users").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame(columns=["userid", "password", "guide_name", "last_date"])

def get_samples():
    try:
        # No @st.cache here to prevent data from "disappearing"
        res = conn.table("samples").select("*").execute()
        return pd.DataFrame(res.data)
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
        
        # Tabs - Preserving all 4 features
        if is_admin:
            tab1, tab2, tab3, tab4 = st.tabs(["📥 Log Sample", "📋 Master Log", "📊 Analytics", "⚙️ Admin Panel"])
        else:
            tab1, tab2 = st.tabs(["📥 Log Sample", "📋 My History"])

        # --- TAB 1: LOG SAMPLE ---
        with tab1:
            st.subheader("New Freezer Entry")
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                f_type = st.selectbox("1. Freezer Type", ["-80 Freezer", "-20 Freezer"])
            with f_col2:
                u_opts = ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["ElanPro White (Vertical)", "ElanPro Grey (Horizontal)"]
                u_name = st.selectbox("2. Unit Name", u_opts)

            with st.form("entry_form", clear_on_submit=True):
                st.markdown("##### Details")
                u_email = st.text_input("Your Email ID")
                b_guide = st.text_input("Guide Name (Biochemistry)")
                s_type = st.text_input("Sample Type")
                box_id = st.text_input("Box ID / Label (Required)")
                count = st.number_input("Total Number of Boxes", min_value=1, step=1)

                if st.form_submit_button("Submit to Cloud"):
                    if box_id and b_guide:
                        log_data = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "userid": selected_user, "email": u_email,
                            "biochem_guide": b_guide, "freezer": f_type, "unit": u_name,
                            "sample_type": s_type, "box_id": box_id, "box_count": int(count)
                        }
                        conn.table("samples").insert(log_data).execute()
                        st.cache_resource.clear()
                        st.success("Data Uploaded Successfully!")
                        st.rerun()

        # --- TAB 2: MASTER LOG (EDIT/DELETE ALL DETAILS) ---
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
                
                # Download
                csv = view_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Log (CSV)", csv, "freezer_log.csv", "text/csv")

                # DUAL EDIT/DELETE OPTIONS
                if is_admin and not view_df.empty:
                    st.markdown("---")
                    st.subheader("⚙️ Manage Entries (Edit All Details or Delete)")
                    manage_opts = [f"{r['userid']} | {r['box_id']} | {r['timestamp']}" for _, r in view_df.iterrows()]
                    selected_entry = st.selectbox("Select entry to manage", ["Select"] + manage_opts)
                    
                    if selected_entry != "Select":
                        idx = manage_opts.index(selected_entry)
                        target = view_df.iloc[idx - 1]
                        
                        e_col, d_col = st.columns([2, 1])
                        with e_col:
                            with st.form("edit_all_details"):
                                st.write("**✏️ Edit All Details**")
                                new_box = st.text_input("Box ID", value=target['box_id'])
                                new_count = st.number_input("Box Count", value=int(target['box_count']), min_value=1)
                                new_stype = st.text_input("Sample Type", value=target['sample_type'] if 'sample_type' in target else "")
                                new_unit = st.text_input("Unit Name", value=target['unit'] if 'unit' in target else "")
                                if st.form_submit_button("Update Everything"):
                                    conn.table("samples").update({"box_id": new_box, "box_count": new_count, "sample_type": new_stype, "unit": new_unit}).eq("timestamp", target['timestamp']).eq("userid", target['userid']).execute()
                                    st.cache_resource.clear()
                                    st.rerun()
                        with d_col:
                            st.write("**🗑️ Delete Entry**")
                            if st.button("Confirm Permanent Deletion"):
                                conn.table("samples").delete().eq("timestamp", target['timestamp']).eq("userid", target['userid']).execute()
                                st.cache_resource.clear()
                                st.rerun()
            else:
                st.info("No data found.")

        # --- TAB 3: ANALYTICS (BY USER & BY FREEZER) ---
        if is_admin:
            with tab3:
                st.subheader("📊 Analytics Dashboard")
                if not df_samples.empty:
                    c_left, c_right = st.columns(2)
                    with c_left:
                        st.write("**Total Occupancy by Freezer Type**")
                        st.bar_chart(df_samples.groupby('freezer')['box_count'].sum())
                    with c_right:
                        st.write("**Box Distribution by User**")
                        st.bar_chart(df_samples.groupby('userid')['box_count'].sum())
                else:
                    st.info("No data available for charts.")

        # --- TAB 4: ADMIN PANEL (AUTHORIZE & REMOVE STUDENTS) ---
        if is_admin:
            with tab4:
                st.subheader("👤 User Management")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("##### Authorize / Update Student")
                    with st.form("auth_student"):
                        n_id, n_pw, n_gd, n_ex = st.text_input("User ID"), st.text_input("Set Password"), st.text_input("Guide Name"), st.date_input("Expiry Date")
                        if st.form_submit_button("Authorize Student"):
                            conn.table("users").upsert({"userid": n_id, "password": n_pw, "guide_name": n_gd, "last_date": str(n_ex)}).execute()
                            st.cache_resource.clear()
                            st.rerun()
                with col_b:
                    st.markdown("##### Remove Student")
                    students = [u for u in USER_LIST if u != "Admin"]
                    to_remove = st.selectbox("Select Student to Remove", ["Select"] + students)
                    if to_remove != "Select" and st.button("Delete Student Permanently"):
                        conn.table("users").delete().eq("userid", to_remove).execute()
                        st.cache_resource.clear()
                        st.rerun()
                st.markdown("---")
                st.write("**Current User List:**")
                st.table(user_df[['userid', 'guide_name', 'last_date']])

    else:
        st.sidebar.error("Invalid credentials.")
else:
    st.info("Please login in the sidebar.")

# --- 5. HELP BUTTON (USER ID REQ + DRAFTED EMAIL) ---
st.sidebar.markdown("---")
for _ in range(15): st.sidebar.write("")
with st.sidebar.popover("Help"):
    st.markdown("### System Support")
    h_id = st.text_input("Please enter your User ID first", key="help_id")
    if h_id:
        subject = f"Freezer%20storage%20issue%20_%20{h_id}"
        body = f"Hello%20Team,%0A%0AI%20am%20facing%20the%20following%20issue%20with%20the%20Freezer%20System:%0A%0A---%0AUser%20ID:%20{h_id}%0AIssue%20Description:%20"
        st.markdown(f'<a href="mailto:biochem@manipal.edu?subject={subject}&body={body}" style="display:block;padding:10px;background:#4f8bf9;color:white;text-align:center;border-radius:5px;text-decoration:none;font-weight:bold;">📧 Email Support Now</a>', unsafe_allow_html=True)
    else:
        st.caption("Provide ID to enable the email link.")
