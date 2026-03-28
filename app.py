import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import urllib.parse

# --- 1. PAGE SETUP & KMC LOGO ---
st.set_page_config(page_title="Freezer Manager", layout="wide")

# Centering the KMC Logo at the top
LOGO_URL = "https://cdn-prod.mybharats.in/organization/DL-ns-d9cbe78f-d9b2-4e20-baf0-e0747653f0bd_kmclogo.jpg"
col_logo_1, col_logo_2, col_logo_3 = st.columns([2, 2, 2])
with col_logo_2:
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

# --- 3. DATA FETCHING (INCLUDING UNIQUE ID) ---
def get_users():
    try:
        res = conn.table("users").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame(columns=["userid", "password", "guide_name", "last_date"])

def get_samples():
    try:
        # Fetching all columns including 'id' for safe deletion/editing
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
        
        # Admin gets 4 tabs, Students get 2
        if is_admin:
            tab1, tab2, tab3, tab4 = st.tabs(["📥 Log Sample", "📋 Master Log", "📊 Analytics", "👤 Admin Panel"])
        else:
            tab1, tab2 = st.tabs(["📥 Log Sample", "📋 My History"])

        # --- TAB 1: LOG SAMPLE (WITH PHONE NUMBER) ---
        with tab1:
            st.subheader("New Freezer Entry")
            f_type = st.selectbox("1. Freezer Type", ["-80 Freezer", "-20 Freezer"])
            u_name = st.selectbox("2. Unit Name", ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["ElanPro White", "ElanPro Grey"])

            with st.form("entry_form", clear_on_submit=True):
                st.markdown("##### Details")
                col_form_1, col_form_2 = st.columns(2)
                u_email = col_form_1.text_input("Your Email ID")
                u_phone = col_form_2.text_input("Your Phone Number")
                b_guide = st.text_input("Guide Name (Biochemistry)")
                s_type = st.text_input("Sample Type")
                box_id = st.text_input("Box ID / Label (Required)")
                count = st.number_input("Total Number of Boxes", min_value=1, step=1)

                if st.form_submit_button("Submit to Cloud"):
                    if box_id and b_guide:
                        log_data = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "userid": selected_user, "email": u_email, "phone": u_phone,
                            "biochem_guide": b_guide, "freezer": f_type, "unit": u_name,
                            "sample_type": s_type, "box_id": box_id, "box_count": int(count)
                        }
                        conn.table("samples").insert(log_data).execute()
                        st.cache_resource.clear()
                        st.success("Entry Saved Successfully!")
                        st.rerun()
                    else:
                        st.error("Missing required fields: Box ID and Guide Name.")

        # --- TAB 2: MASTER LOG (SAFE EDIT/DELETE VIA UNIQUE ID) ---
        with tab2:
            df_samples = get_samples()
            if not df_samples.empty:
                view_df = df_samples if is_admin else df_samples[df_samples['userid'] == selected_user]
                
                if is_admin:
                    st.markdown("##### 🔎 Search Logs")
                    search_query = st.text_input("Filter by User or Box ID", "").lower()
                    if search_query:
                        mask = (view_df['userid'].astype(str).str.lower().str.contains(search_query) | 
                                view_df['box_id'].astype(str).str.lower().str.contains(search_query))
                        view_df = view_df[mask]
                
                # Display table (Hide ID column for neatness)
                st.dataframe(view_df.drop(columns=['id'], errors='ignore').sort_values('timestamp', ascending=False), use_container_width=True)
                
                # Download Master Log
                csv = view_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Master Log (CSV)", csv, "freezer_log.csv", "text/csv")

                # --- ADMIN MANAGE: EDIT ALL DETAILS & DELETE ---
                if is_admin and not view_df.empty:
                    st.markdown("---")
                    st.subheader("⚙️ Manage Entries (Admin Only)")
                    manage_opts = [f"{r['userid']} | {r['box_id']} | {r['timestamp']}" for _, r in view_df.iterrows()]
                    selected_manage = st.selectbox("Select entry to modify/delete", ["Select"] + manage_opts)
                    
                    if selected_manage != "Select":
                        idx = manage_opts.index(selected_manage)
                        target_row = view_df.iloc[idx - 1]
                        
                        col_edit, col_del = st.columns([2, 1])
                        with col_edit:
                            with st.form("full_edit_form"):
                                st.write("**✏️ Edit All Details**")
                                e_box = st.text_input("Box ID", value=target_row['box_id'])
                                e_count = st.number_input("Count", value=int(target_row['box_count']), min_value=1)
                                e_type = st.text_input("Sample Type", value=target_row.get('sample_type', ""))
                                e_guide = st.text_input("Guide Name", value=target_row.get('biochem_guide', ""))
                                e_phone = st.text_input("Phone", value=target_row.get('phone', ""))
                                if st.form_submit_button("Save Changes"):
                                    # Target exact ID
                                    conn.table("samples").update({"box_id": e_box, "box_count": e_count, "sample_type": e_type, "biochem_guide": e_guide, "phone": e_phone}).eq("id", target_row['id']).execute()
                                    st.cache_resource.clear()
                                    st.rerun()
                        with col_del:
                            st.write("**🗑️ Delete Entry**")
                            st.error("Caution: Permanent Action")
                            if st.button("Confirm Delete Permanently"):
                                # Target exact ID to prevent deleting others
                                conn.table("samples").delete().eq("id", target_row['id']).execute()
                                st.cache_resource.clear()
                                st.rerun()
            else:
                st.info("No data available.")

        # --- TAB 3: ANALYTICS (TOTALS & CHARTS) ---
        if is_admin:
            with tab3:
                all_d = get_samples()
                if not all_d.empty:
                    st.subheader("📊 Storage Totals & Charts")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Boxes (-80°C)", int(all_d[all_d['freezer'] == "-80 Freezer"]['box_count'].sum()))
                    m2.metric("Boxes (-20°C)", int(all_d[all_d['freezer'] == "-20 Freezer"]['box_count'].sum()))
                    m3.metric("Grand Total", int(all_d['box_count'].sum()))
                    
                    st.markdown("---")
                    c_l, c_r = st.columns(2)
                    with c_l:
                        st.write("**By Freezer Occupancy**")
                        st.bar_chart(all_d.groupby('freezer')['box_count'].sum())
                    with c_r:
                        st.write("**By User Distribution**")
                        st.bar_chart(all_d.groupby('userid')['box_count'].sum())

        # --- TAB 4: ADMIN PANEL (USER AUTHORIZATION) ---
        if is_admin:
            with tab4:
                st.subheader("👤 Student Access Management")
                col_add, col_rem = st.columns(2)
                with col_add:
                    st.markdown("##### Authorize / Update Student")
                    with st.form("auth_student"):
                        n_id, n_pw, n_gd, n_ex = st.text_input("User ID"), st.text_input("Pass"), st.text_input("Guide"), st.date_input("Expiry")
                        if st.form_submit_button("Grant Access"):
                            conn.table("users").upsert({"userid": n_id, "password": n_pw, "guide_name": n_gd, "last_date": str(n_ex)}).execute()
                            st.cache_resource.clear()
                            st.rerun()
                with col_rem:
                    st.markdown("##### Remove Student")
                    student_only = [u for u in USER_LIST if u != "Admin"]
                    to_rem = st.selectbox("Select Student", ["Select"] + student_only)
                    if to_rem != "Select" and st.button("Remove Access Permanently"):
                        conn.table("users").delete().eq("userid", to_rem).execute()
                        st.cache_resource.clear()
                        st.rerun()
                st.table(user_df[['userid', 'guide_name', 'last_date']])

    else:
        st.sidebar.error("Invalid credentials.")
else:
    st.info("Welcome. Please login in the sidebar to begin.")

# --- 5. HELP SYSTEM (CUSTOM SUBJECT & DRAFT) ---
st.sidebar.markdown("---")
for _ in range(15): st.sidebar.write("")
with st.sidebar.popover("Help"):
    st.write("### Support")
    h_uid = st.text_input("Enter User ID", key="h_uid_final")
    if h_uid:
        subj = urllib.parse.quote(f"Freezer storage issue _ {h_uid}")
        body = urllib.parse.quote(f"Hello Team,\n\nI am facing an issue with the freezer storage system. My User ID is {h_uid}.\n\nDetails of the problem:\n")
        mail_link = f"mailto:biochem@manipal.edu?subject={subj}&body={body}"
        st.markdown(f'<a href="{mail_link}" style="display:block;padding:10px;background:#4f8bf9;color:white;text-align:center;border-radius:5px;text-decoration:none;font-weight:bold;">📧 Draft Support Email</a>', unsafe_allow_html=True)
