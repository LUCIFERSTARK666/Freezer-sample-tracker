import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import urllib.parse

# --- 1. PAGE SETUP & KMC LOGO ---
st.set_page_config(page_title="Freezer Manager", layout="wide")

# Centering the KMC Logo
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

# --- 3. DATA FETCHING ---
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
        
        # Tabs Logic
        if is_admin:
            tab1, tab2, tab3, tab4 = st.tabs(["📥 Log Sample", "📋 Master Log", "📊 Analytics", "⚙️ Admin Panel"])
        else:
            tab1, tab2 = st.tabs(["📥 Log Sample", "📋 My History"])

        # --- TAB 1: LOG SAMPLE ---
        with tab1:
            st.subheader("New Freezer Entry")
            f_type = st.selectbox("1. Freezer Type", ["-80 Freezer", "-20 Freezer"])
            u_opts = ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["ElanPro White", "ElanPro Grey"]
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
                        st.success("Entry Saved Successfully!")
                        st.rerun()

        # --- TAB 2: MASTER LOG (EDIT ALL DETAILS & DELETE) ---
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

                # --- ADMIN MANAGE: EDIT & DELETE ---
                if is_admin and not view_df.empty:
                    st.markdown("---")
                    st.subheader("⚙️ Manage Entries (Admin Only)")
                    manage_options = [f"{r['userid']} | {r['box_id']} | {r['timestamp']}" for _, r in view_df.iterrows()]
                    selected_entry = st.selectbox("Select entry to modify/remove", ["Select"] + manage_options)
                    
                    if selected_entry != "Select":
                        idx = manage_options.index(selected_entry)
                        target_row = view_df.iloc[idx - 1]
                        
                        col_edit, col_del = st.columns([2, 1])
                        with col_edit:
                            with st.form("admin_edit_full_form"):
                                st.write("**✏️ Edit All Details**")
                                e_box = st.text_input("Box ID", value=target_row['box_id'])
                                e_count = st.number_input("Box Count", value=int(target_row['box_count']), min_value=1)
                                e_type = st.text_input("Sample Type", value=target_row.get('sample_type', ""))
                                e_guide = st.text_input("Guide Name", value=target_row.get('biochem_guide', ""))
                                e_email = st.text_input("Email", value=target_row.get('email', ""))
                                
                                if st.form_submit_button("Update Everything"):
                                    conn.table("samples").update({
                                        "box_id": e_box, "box_count": e_count, "sample_type": e_type,
                                        "biochem_guide": e_guide, "email": e_email
                                    }).eq("timestamp", target_row['timestamp']).eq("userid", target_row['userid']).execute()
                                    st.cache_resource.clear()
                                    st.rerun()
                        
                        with col_del:
                            st.write("**🗑️ Remove Record**")
                            st.error("Caution: Permanent Deletion")
                            if st.button("Confirm Delete Permanently"):
                                conn.table("samples").delete().eq("timestamp", target_row['timestamp']).eq("userid", target_row['userid']).execute()
                                st.cache_resource.clear()
                                st.rerun()

        # --- TAB 3: ANALYTICS (USER & FREEZER) ---
        if is_admin:
            with tab3:
                all_data = get_samples()
                if not all_data.empty:
                    st.subheader("📊 Freezer Occupancy & Totals")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Boxes (-80°C)", int(all_data[all_data['freezer'] == "-80 Freezer"]['box_count'].sum()))
                    m2.metric("Boxes (-20°C)", int(all_data[all_data['freezer'] == "-20 Freezer"]['box_count'].sum()))
                    m3.metric("Grand Total", int(all_data['box_count'].sum()))
                    
                    st.markdown("---")
                    c_left, c_right = st.columns(2)
                    with c_left:
                        st.write("**By Freezer Type**")
                        st.bar_chart(all_data.groupby('freezer')['box_count'].sum())
                    with c_right:
                        st.write("**By User Distribution**")
                        st.bar_chart(all_data.groupby('userid')['box_count'].sum())

        # --- TAB 4: ADMIN PANEL (USER AUTHORIZATION) ---
        if is_admin:
            with tab4:
                st.subheader("👤 Student Access Management")
                col_add, col_rem = st.columns(2)
                with col_add:
                    st.markdown("##### Authorize/Update Student")
                    with st.form("auth_student_form"):
                        n_id = st.text_input("User ID")
                        n_pw = st.text_input("Password")
                        n_gd = st.text_input("Primary Guide")
                        n_ex = st.date_input("Expiry Date")
                        if st.form_submit_button("Grant Access"):
                            conn.table("users").upsert({"userid": n_id, "password": n_pw, "guide_name": n_gd, "last_date": str(n_ex)}).execute()
                            st.cache_resource.clear()
                            st.rerun()
                with col_rem:
                    st.markdown("##### Remove Student")
                    rem_list = [u for u in USER_LIST if u != "Admin"]
                    to_rem = st.selectbox("Select Student", ["Select"] + rem_list)
                    if to_rem != "Select" and st.button("Remove Permanently"):
                        conn.table("users").delete().eq("userid", to_rem).execute()
                        st.cache_resource.clear()
                        st.rerun()
                st.table(user_df[['userid', 'guide_name', 'last_date']])

    else: st.sidebar.error("Invalid credentials.")
else: st.info("Please login in the sidebar to begin.")

# --- 5. HELP POPOVER (USER ID & DRAFTED MAIL) ---
st.sidebar.markdown("---")
for _ in range(15): st.sidebar.write("")
with st.sidebar.popover("Help"):
    st.write("### Support")
    h_uid = st.text_input("Enter User ID", key="help_uid_input")
    if h_uid:
        subject = urllib.parse.quote(f"Freezer storage issue _ {h_uid}")
        body = urllib.parse.quote(f"Hello Team,\n\nI am facing an issue with the freezer storage system. My User ID is {h_uid}.\n\nDetails of the problem:\n")
        mail_link = f"mailto:biochem@manipal.edu?subject={subject}&body={body}"
        st.markdown(f'<a href="{mail_link}" style="display:block;padding:10px;background:#4f8bf9;color:white;text-align:center;border-radius:5px;text-decoration:none;font-weight:bold;">📧 Draft Support Email</a>', unsafe_allow_html=True)
