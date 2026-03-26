import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Biochemistry Freezer Manager", layout="wide")
st.title("Freezer Management System")

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
        
        # --- DAYS REMAINING LOGIC ---
        if not is_admin:
            u_row = user_data.iloc[0]
            st.sidebar.markdown("---")
            st.sidebar.subheader("Storage Status")
            st.sidebar.write(f"**Primary Guide:** {u_row['guide_name']}")
            try:
                expiry_str = str(u_row['last_date']).strip()
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                today = datetime.now().date()
                days_left = (expiry_date - today).days
                if days_left > 30:
                    st.sidebar.metric("Storage Days Left", f"{days_left} Days")
                elif 0 <= days_left <= 30:
                    st.sidebar.warning(f"⚠️ Only {days_left} days remaining!")
                else:
                    st.sidebar.error(f"❌ Storage Expired ({abs(days_left)} days ago)")
            except:
                st.sidebar.info("Expiry date pending.")

        # Tabs
        if is_admin:
            tab1, tab2, tab3 = st.tabs(["📥 Log Sample", "📋 Master Log", "⚙️ Admin Panel"])
        else:
            tab1, tab2 = st.tabs(["📥 Log Sample", "📋 My History"])

        # --- TAB 1: LOG SAMPLE ---
        with tab1:
            st.subheader("New Entry")
            col1, col2 = st.columns(2)
            with col1:
                f_type = st.selectbox("1. Freezer Type", ["-80 Freezer", "-20 Freezer"])
            with col2:
                u_opts = ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["ElanPro White (Vertical)", "ElanPro Grey (Horizontal)"]
                u_name = st.selectbox("2. Unit Name", u_opts)

            with st.form("entry_form", clear_on_submit=True):
                st.markdown("##### Details")
                col_a, col_b = st.columns(2)
                u_email = col_a.text_input("Your Email ID")
                u_phone = col_b.text_input("Your Phone Number")
                b_guide = st.text_input("Guide Name (Biochemistry)")
                s_type = st.text_input("Sample Type")
                col_c, col_d = st.columns(2)
                box_id = col_c.text_input("Box ID / Label (Required)")
                count = col_d.number_input("Total Number of Boxes", min_value=1, step=1)

                if st.form_submit_button("Submit to Cloud"):
                    if box_id and b_guide:
                        log_data = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "userid": selected_user, "email": u_email, "phone": u_phone,
                            "biochem_guide": b_guide, "freezer": f_type, "unit": u_name,
                            "sample_type": s_type, "box_id": box_id, "box_count": int(count)
                        }
                        conn.table("samples").insert(log_data).execute()
                        st.success(f"Saved to {u_name}!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Missing required fields.")

        # --- TAB 2: VIEW RECORDS, SEARCH & ADMIN EDIT ---
        with tab2:
            df_samples = get_samples()
            if not df_samples.empty:
                if is_admin:
                    st.markdown("##### 🔎 Admin Search & Filter")
                    search_query = st.text_input("Search by User ID or Box ID", "").lower()
                    view_df = df_samples
                    if search_query:
                        mask = (view_df['userid'].astype(str).str.lower().str.contains(search_query) | 
                                view_df['box_id'].astype(str).str.lower().str.contains(search_query))
                        view_df = view_df[mask]
                    download_label = f"📥 Download Master Log (CSV)"
                else:
                    view_df = df_samples[df_samples['userid'] == selected_user]
                    download_label = "📥 Download My Sample History (CSV)"
                
                st.dataframe(view_df, use_container_width=True)
                
                if not view_df.empty:
                    st.markdown("---")
                    csv = view_df.to_csv(index=False).encode('utf-8')
                    st.download_button(label=download_label, data=csv, file_name="freezer_log.csv", mime="text/csv")
                
                # --- NEW: ADMIN EDIT SECTION INSIDE TAB 2 ---
                if is_admin and not view_df.empty:
                    st.markdown("---")
                    st.subheader("✏️ Quick Edit Entry (Admin Only)")
                    edit_options = [f"{r['userid']} | {r['box_id']} | {r['timestamp']}" for _, r in view_df.iterrows()]
                    selected_edit = st.selectbox("Select entry from above to modify", ["Select"] + edit_options)
                    
                    if selected_edit != "Select":
                        # Match selection back to data
                        target_row = view_df.iloc[edit_options.index(selected_edit) - 1]
                        
                        with st.form("quick_edit_form"):
                            st.info(f"Modifying entry for {target_row['userid']} ({target_row['timestamp']})")
                            col_e1, col_e2 = st.columns(2)
                            new_box = col_e1.text_input("New Box ID", value=target_row['box_id'])
                            new_count = col_e2.number_input("New Box Count", value=int(target_row['box_count']), min_value=1)
                            new_type = st.text_input("New Sample Type", value=target_row['sample_type'])
                            
                            if st.form_submit_button("Save Changes"):
                                conn.table("samples").update({
                                    "box_id": new_box, 
                                    "box_count": new_count, 
                                    "sample_type": new_type
                                }).eq("timestamp", target_row['timestamp']).eq("userid", target_row['userid']).execute()
                                st.success("Database Updated!")
                                st.rerun()
            else:
                st.info("No data available.")

        # --- TAB 3: ADMIN PANEL (USERS & METRICS) ---
        if is_admin:
            with tab3:
                st.subheader("📊 Freezer Occupancy Summary")
                all_s = get_samples()
                if not all_s.empty:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Boxes (-80°C)", int(all_s[all_s['freezer'] == "-80 Freezer"]['box_count'].sum()))
                    c2.metric("Boxes (-20°C)", int(all_s[all_s['freezer'] == "-20 Freezer"]['box_count'].sum()))
                    c3.metric("Total Boxes", int(all_s['box_count'].sum()))
                
                st.markdown("---")
                col_left, col_right = st.columns(2)
                with col_left:
                    st.subheader("Add/Update Student")
                    with st.form("add_user"):
                        n_id = st.text_input("Student User ID")
                        n_pw = st.text_input("Set Password")
                        n_gd = st.text_input("Primary Guide Name")
                        n_ex = st.date_input("Storage Expiry Date")
                        if st.form_submit_button("Authorize Student"):
                            conn.table("users").upsert({"userid": n_id, "password": n_pw, "guide_name": n_gd, "last_date": str(n_ex)}).execute()
                            st.rerun()
                with col_right:
                    st.subheader("Remove Student")
                    student_list = [u for u in USER_LIST if u != "Admin"]
                    user_to_delete = st.selectbox("Select Student to Delete", ["Select"] + student_list)
                    if user_to_delete != "Select":
                        if st.button("Confirm Permanent Deletion"):
                            conn.table("users").delete().eq("userid", user_to_delete).execute()
                            st.rerun()

                st.markdown("---")
                st.write("Authorized User List:")
                st.table(user_df[['userid', 'guide_name', 'last_date']])
    else:
        st.sidebar.error("Invalid credentials.")
else:
    st.info("Please select your User ID in the sidebar.")
