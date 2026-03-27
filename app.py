import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- 1. PAGE SETUP & KMC LOGO ---
st.set_page_config(page_title="Biochemistry Freezer Manager", layout="wide")

# KMC Logo Link
LOGO_URL = "https://cdn-prod.mybharats.in/organization/DL-ns-d9cbe78f-d9b2-4e20-baf0-e0747653f0bd_kmclogo.jpg"

col1, col2, col3 = st.columns([2, 2, 2])
with col2:
    st.image(LOGO_URL, width=350) 

st.markdown("<h1 style='text-align: center;'>Biochemistry Freezer Management System</h1>", unsafe_allow_html=True)
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
        # We fetch 'id' as well to ensure precise Deletion/Editing
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
        
        if not is_admin:
            u_row = user_data.iloc[0]
            st.sidebar.markdown("---")
            st.sidebar.subheader("Storage Status")
            st.sidebar.write(f"**Primary Guide:** {u_row['guide_name']}")
            try:
                expiry_str = str(u_row['last_date']).strip()
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                days_left = (expiry_date - datetime.now().date()).days
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
            st.subheader("New Freezer Entry")
            col1, col2 = st.columns(2)
            with col1:
                f_type = st.selectbox("1. Freezer Type", ["-80 Freezer", "-20 Freezer"])
            with col2:
                u_name = st.selectbox("2. Unit Name", ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["ElanPro White (Vertical)", "ElanPro Grey (Horizontal)"])

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
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "userid": selected_user, "email": u_email, "phone": u_phone,
                            "biochem_guide": b_guide, "freezer": f_type, "unit": u_name,
                            "sample_type": s_type, "box_id": box_id, "box_count": int(count)
                        }
                        conn.table("samples").insert(log_data).execute()
                        st.cache_resource.clear()
                        st.success(f"Saved to {u_name}!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Missing required fields.")

        # --- TAB 2: VIEW RECORDS & ADMIN EDIT/DELETE ---
        with tab2:
            all_samples = get_samples()
            if not all_samples.empty:
                if is_admin:
                    st.markdown("##### 🔎 Admin Search & Filter")
                    search_query = st.text_input("Search by User ID or Box ID", "").lower()
                    view_df = all_samples
                    if search_query:
                        mask = (view_df['userid'].astype(str).str.lower().str.contains(search_query) | 
                                view_df['box_id'].astype(str).str.lower().str.contains(search_query))
                        view_df = view_df[mask]
                else:
                    view_df = all_samples[all_samples['userid'] == selected_user]
                
                # Show the table
                st.dataframe(view_df.sort_values('timestamp', ascending=False), use_container_width=True)
                
                # Download Button
                if not view_df.empty:
                    csv = view_df.to_csv(index=False).encode('utf-8')
                    st.download_button(label="📥 Download CSV", data=csv, file_name="freezer_log.csv", mime="text/csv")

                # --- ADMIN EDIT & DELETE LOGIC ---
                if is_admin and not view_df.empty:
                    st.markdown("---")
                    st.subheader("✏️ Manage Entry (Admin Only)")
                    
                    edit_options = [f"{r['userid']} | {r['box_id']} | {r['timestamp']}" for _, r in view_df.iterrows()]
                    selected_manage = st.selectbox("Select entry to Edit or Delete", ["Select"] + edit_options)
                    
                    if selected_manage != "Select":
                        # Match the selected string back to the row
                        idx = edit_options.index(selected_manage)
                        target_row = view_df.iloc[idx]
                        
                        st.info(f"Managing: {target_row['userid']} | {target_row['timestamp']}")
                        col_edit, col_del = st.columns([2, 1])
                        
                        with col_edit:
                            with st.form("quick_edit_form"):
                                st.write("**Update Details**")
                                e_box = st.text_input("New Box ID", value=target_row['box_id'])
                                e_count = st.number_input("New Box Count", value=int(target_row['box_count']), min_value=1)
                                e_type = st.text_input("New Sample Type", value=target_row['sample_type'])
                                if st.form_submit_button("Save Changes"):
                                    # Use 'id' if available, otherwise filter by multiple fields
                                    query = conn.table("samples").update({
                                        "box_id": e_box, 
                                        "box_count": e_count, 
                                        "sample_type": e_type
                                    })
                                    
                                    if 'id' in target_row:
                                        query.eq("id", target_row['id']).execute()
                                    else:
                                        query.eq("timestamp", str(target_row['timestamp'])).eq("userid", target_row['userid']).execute()
                                    
                                    st.cache_resource.clear()
                                    st.success("Entry Updated!")
                                    st.rerun()
                        
                        with col_del:
                            st.write("** **")
                            if st.button("🗑️ Delete This Entry"):
                                query_del = conn.table("samples").delete()
                                
                                if 'id' in target_row:
                                    query_del.eq("id", target_row['id']).execute()
                                else:
                                    query_del.eq("timestamp", str(target_row['timestamp'])).eq("userid", target_row['userid']).execute()
                                
                                st.cache_resource.clear()
                                st.warning("Entry Deleted Permanently!")
                                st.rerun()
            else:
                st.info("No data available.")

        # --- TAB 3: ADMIN PANEL ---
        if is_admin:
            with tab3:
                st.markdown("""<style>div[data-testid="stMetric"] {background-color: #f0f2f6; border: 1px solid #dfe1e5; padding: 15px; border-radius: 10px; text-align: center;}</style>""", unsafe_allow_html=True)
                st.subheader("📊 Freezer Occupancy Summary (Latest per Student)")
                
                all_s = get_samples()
                if not all_s.empty:
                    latest_samples = all_s.sort_values('timestamp').groupby('userid').tail(1)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Boxes (-80°C)", int(latest_samples[latest_samples['freezer'] == "-80 Freezer"]['box_count'].sum()))
                    c2.metric("Boxes (-20°C)", int(latest_samples[latest_samples['freezer'] == "-20 Freezer"]['box_count'].sum()))
                    c3.metric("Grand Total", int(latest_samples['box_count'].sum()))
                    
                    st.markdown("#### 📈 Box Distribution per User (Latest Entry)")
                    chart_data = latest_samples[['userid', 'box_count']].sort_values(by='box_count', ascending=False)
                    st.bar_chart(data=chart_data, x='userid', y='box_count', color='#4f8bf9')
                
                st.markdown("---")
                col_left, col_right = st.columns(2)
                with col_left:
                    st.subheader("Add/Update Student")
                    with st.form("add_user"):
                        n_id, n_pw, n_gd, n_ex = st.text_input("User ID"), st.text_input("Pass"), st.text_input("Guide"), st.date_input("Expiry")
                        if st.form_submit_button("Authorize"):
                            conn.table("users").upsert({"userid": n_id, "password": n_pw, "guide_name": n_gd, "last_date": str(n_ex)}).execute()
                            st.cache_resource.clear()
                            st.rerun()
                with col_right:
                    st.subheader("Remove Student")
                    student_list = [u for u in USER_LIST if u != "Admin"]
                    user_to_delete = st.selectbox("Select to Delete", ["Select"] + student_list)
                    if user_to_delete != "Select" and st.button("Confirm Deletion"):
                        conn.table("users").delete().eq("userid", user_to_delete).execute()
                        st.cache_resource.clear()
                        st.rerun()

                st.markdown("---")
                st.table(user_df[['userid', 'guide_name', 'last_date']])
    else:
        st.sidebar.error("Invalid credentials.")
else:
    st.info("👋 Welcome. Please select your User ID in the sidebar to begin.")
