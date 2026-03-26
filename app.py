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

        # --- TAB 2: VIEW RECORDS & DOWNLOAD ---
        with tab2:
            df_samples = get_samples()
            if not df_samples.empty:
                if is_admin:
                    view_df = df_samples
                    download_label = "📥 Download Master Log (CSV)"
                    file_name = f"freezer_master_log_{datetime.now().strftime('%Y-%m-%d')}.csv"
                else:
                    view_df = df_samples[df_samples['userid'] == selected_user]
                    download_label = "📥 Download My Sample History (CSV)"
                    file_name = f"my_freezer_samples_{selected_user}_{datetime.now().strftime('%Y-%m-%d')}.csv"
                
                st.dataframe(view_df, use_container_width=True)
                
                if not view_df.empty:
                    st.markdown("---")
                    csv = view_df.to_csv(index=False).encode('utf-8')
                    st.download_button(label=download_label, data=csv, file_name=file_name, mime="text/csv")
                else:
                    st.info("You haven't logged any samples yet.")
            else:
                st.info("No data available.")

        # --- TAB 3: ADMIN PANEL ---
        if is_admin:
            with tab3:
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
                st.table(user_df[['userid', 'guide_name', 'last_date']])
    else:
        st.sidebar.error("Invalid credentials.")
        # --- NEW: EDIT ENTRY SECTION ---
                st.markdown("---")
                st.subheader("✏️ Edit Existing Entry")
                
                df_samples = get_samples()
                if not df_samples.empty:
                    # Create a list of labels for the dropdown (Timestamp + User + Box ID)
                    sample_labels = [
                        f"{row['timestamp']} | {row['userid']} | Box: {row['box_id']}" 
                        for _, row in df_samples.iterrows()
                    ]
                    
                    selected_label = st.selectbox("Select Entry to Edit", ["Select Entry"] + sample_labels)
                    
                    if selected_label != "Select Entry":
                        # Get the original row index
                        idx = sample_labels.index(selected_label)
                        target_row = df_samples.iloc[idx]
                        
                        st.info(f"Editing entry for {target_row['userid']} logged on {target_row['timestamp']}")
                        
                        with st.form("edit_form"):
                            col_e1, col_e2 = st.columns(2)
                            new_box = col_e1.text_input("Update Box ID", value=str(target_row['box_id']))
                            new_count = col_e2.number_input("Update Box Count", value=int(target_row['box_count']), min_value=1)
                            
                            new_type = st.text_input("Update Sample Type", value=str(target_row['sample_type']))
                            new_guide = st.text_input("Update Biochem Guide", value=str(target_row['biochem_guide']))
                            
                            if st.form_submit_button("Save Changes to Database"):
                                try:
                                    # Update Supabase using the unique timestamp and userid as the filter
                                    conn.table("samples").update({
                                        "box_id": new_box,
                                        "box_count": new_count,
                                        "sample_type": new_type,
                                        "biochem_guide": new_guide
                                    }).eq("timestamp", target_row['timestamp']).eq("userid", target_row['userid']).execute()
                                    
                                    st.success("Changes saved successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating entry: {e}")
                else:
                    st.write("No samples available to edit.")
