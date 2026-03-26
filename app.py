import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- 1. PAGE SETUP & LIGHT THEME (DARK TEXT) ---
st.set_page_config(page_title="Biochemistry Freezer Manager", layout="wide")

st.markdown(
    """
    <style>
    /* 1. Main Background - Light Medical Blue */
    .stApp {
        background: #f0f2f6;
    }

    /* 2. Light Panels (Cards) with Dark Text */
    .stTabs, .stForm, [data-testid="stMetric"], .stDataFrame, [data-testid="stVerticalBlock"] > div > div {
        background-color: #ffffff !important;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border: 1px solid #d1d9e6;
    }

    /* 3. FORCE DARK TEXT EVERYWHERE */
    h1, h2, h3, h4, h5, h6, label, p, span, .stMarkdown {
        color: #1a1a1a !important; /* Deep Black/Navy */
        font-family: 'Segoe UI', Tahoma, sans-serif;
    }

    /* 4. Sidebar - White with Dark Text */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 2px solid #d1d9e6;
    }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
        color: #1a1a1a !important;
    }

    /* 5. Centered Title */
    h1 {
        text-align: center;
        font-weight: 800;
        padding-bottom: 30px;
        color: #003366 !important; /* Medical Navy */
    }
    
    /* Input Box Text Color */
    input {
        color: #000000 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


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
st.sidebar.header("Lab Authentication")
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
