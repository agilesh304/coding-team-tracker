import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.grid import grid

# Custom CSS for enhanced styling
st.set_page_config(
    page_title="Coding Team Tracker", 
    page_icon="🚀", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS injection
st.markdown("""
<style>
    /* Main styling */
    .main {
        background-color: #f8f9fa;
    }
    
    /* Title styling */
    .title-wrapper {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    
    /* Card styling */
    .card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
        border-left: 5px solid #667eea;
    }
    
    .metric {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 4px solid #667eea;
        color: #333333 !important;
    }
    
    .metric div {
        color: #333333 !important;
    }
    
    .progress-bar {
        color: white !important;
        text-shadow: 1px 1px 1px rgba(0,0,0,0.3);
    }
    
    .metric:hover {
        transform: translateY(-3px);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        padding: 0 24px;
        background-color: #f8f9fa;
        border-radius: 8px 8px 0 0 !important;
        border: 1px solid #e9ecef !important;
        font-weight: 500;
        transition: all 0.3s;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #667eea !important;
        color: white !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Custom badges */
    .badge {
        display: inline-block;
        padding: 0.35em 0.65em;
        font-size: 0.75em;
        font-weight: 700;
        line-height: 1;
        text-align: center;
        white-space: nowrap;
        vertical-align: baseline;
        border-radius: 12px;
        margin-right: 6px;
        margin-bottom: 6px;
        color: white !important;
    }
    
    /* Animation for streak */
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    
    .streak-animation {
        animation: pulse 1.5s infinite;
    }
    
    /* Platform specific colors */
    .lc-badge { background: #667eea !important; }
    .sk-badge { background: #9c27b0 !important; }
    .cc-badge { background: #9b51e0 !important; }
    .hr-badge { background: #3498db !important; }
    .gh-badge { background: #2ecc71 !important; }
</style>
""", unsafe_allow_html=True)

# Initialize Firebase
try:
    firebase_key_dict = {
        "type": st.secrets["firebase"]["type"],
        "project_id": st.secrets["firebase"]["project_id"],
        "private_key_id": st.secrets["firebase"]["private_key_id"],
        "private_key": st.secrets["firebase"]["private_key"],
        "client_email": st.secrets["firebase"]["client_email"],
        "client_id": st.secrets["firebase"]["client_id"],
        "auth_uri": st.secrets["firebase"]["auth_uri"],
        "token_uri": st.secrets["firebase"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"],
        "universe_domain": st.secrets["firebase"]["universe_domain"]
    }

    # st.success("✅ Firebase secrets loaded successfully!")
    # st.write("🔑 Keys available:", list(firebase_key_dict.keys()))

except Exception as e:
    st.error(f"❌ Failed to load Firebase secrets: {e}")

# Initialize Firebase app only once
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_key_dict)
    firebase_admin.initialize_app(cred)

# ✅ Now define Firestore client
db = firestore.client()

# Title with gradient background
st.markdown("""
<div class="title-wrapper">
    <h1 style="color:white; margin:0; padding:0;">🚀 Byte Breakers' Performance Dashboard</h1>
    <p style="color:white; margin:0; padding:0; opacity:0.9; font-size:1.1rem;">Track daily progress, streaks, and leaderboards in real-time</p>
</div>
""", unsafe_allow_html=True)

# Load Data
@st.cache_data(ttl=3600)
def load_data():
    rows = []
    users = db.collection('users').list_documents()
    for u in users:
        user_id = u.id
        docs = u.collection('daily_totals').stream()
        for doc in docs:
            d = doc.to_dict()
            d['user'] = user_id
            rows.append(d)
    return pd.DataFrame(rows)

with st.spinner('🔥 Loading team data from Firestore...'):
    df = load_data()
    
if df.empty:
    st.error("⚠ No data found in Firestore. Please run the data collection script first.")
    st.stop()

# Data Preprocessing
df = df.sort_values(['user', 'date']).reset_index(drop=True)
df['date'] = pd.to_datetime(df['date'])

platforms = {
    'leetcode': {'total': 'leetcode_total', 'daily': 'leetcode_daily_increase'},
    'skillrack': {'total': 'skillrack_total', 'daily': 'skillrack_daily_increase'},
    'codechef': {'total': 'codechef_total', 'daily': 'codechef_daily_increase'},
    'hackerrank': {'total': 'hackerrank_total', 'daily': 'hackerrank_daily_increase'},
    'github': {'total': 'github_repos', 'daily': 'github_daily_increase'}
}

# Ensure all columns exist and calculate daily increases
for platform, cols in platforms.items():
    if cols['total'] not in df.columns:
        df[cols['total']] = 0
    if cols['daily'] not in df.columns:
        df[cols['daily']] = 0
    df[cols['daily']] = df.groupby('user')[cols['total']].diff().fillna(0).astype(int)

df['total_solved'] = df['leetcode_total'] + df['skillrack_total'] + df['codechef_total'] + df['hackerrank_total']
df['total_daily_increase'] = df['leetcode_daily_increase'] + df['skillrack_daily_increase'] + df['codechef_daily_increase'] + df['hackerrank_daily_increase']

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["🏆 Leaderboard", "📅 Weekly Summary", "📈 Individual Progress", "🔍 Raw Data"])

with tab1:
    # Leaderboard Section
    st.markdown("### 🏆 Coding Champions Leaderboard")
    
    latest = df.sort_values('date').groupby('user').last().reset_index()
    latest['total_solved'] = latest['leetcode_total'] + latest['skillrack_total'] + latest['codechef_total'] + latest['hackerrank_total']
    leaderboard = latest.sort_values('total_solved', ascending=False)
    
    # Top performer metrics
    top_performer = leaderboard.iloc[0]
    st.markdown(f"#### 🏅 Current Leader: **{top_performer['user']}** with {int(top_performer['total_solved'])} total solutions")
    
    # Metrics grid
    cols = st.columns(5)
    metric_data = [
        ("Total Solutions", top_performer['total_solved'], "#764ba2"),
        ("LeetCode", top_performer['leetcode_total'], "#667eea"),
        ("Skillrack", top_performer['skillrack_total'], "#9c27b0"),
        ("CodeChef", top_performer['codechef_total'], "#9b51e0"),
        ("HackerRank", top_performer['hackerrank_total'], "#3498db")
    ]
    
    for i, (label, value, color) in enumerate(metric_data):
        cols[i].markdown(
            f"""
            <div class="metric" style="border-left: 4px solid {color};">
                <div style="font-size:0.9rem; color:#6c757d;">{label}</div>
                <div style="font-size:1.5rem; font-weight:bold;">{int(value)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Leaderboard table
    st.markdown("### 📊 Detailed Performance Metrics")
    st.dataframe(
        leaderboard[['user', 'leetcode_total', 'skillrack_total', 'codechef_total', 'hackerrank_total', 'github_repos', 'total_solved']],
        column_config={
            "user": "Team Member",
            "leetcode_total": st.column_config.NumberColumn("LeetCode", format="%d"),
            "skillrack_total": st.column_config.NumberColumn("Skillrack", format="%d"),
            "codechef_total": st.column_config.NumberColumn("CodeChef", format="%d"),
            "hackerrank_total": st.column_config.NumberColumn("HackerRank", format="%d"),
            "github_repos": st.column_config.NumberColumn("GitHub Repos", format="%d"),
            "total_solved": st.column_config.ProgressColumn(
                "Total Solutions",
                format="%d",
                min_value=0,
                max_value=leaderboard['total_solved'].max()
            ),
        },
        hide_index=True,
        use_container_width=True,
        height=min(len(leaderboard) * 35 + 38, 600)
    )
    
    # Platform distribution
    st.markdown("### 🥧 Platform Distribution Among Team")
    platform_totals = leaderboard[['leetcode_total', 'skillrack_total', 'codechef_total', 'hackerrank_total']].sum().reset_index()
    platform_totals.columns = ['Platform', 'Total']
    platform_totals['Platform'] = platform_totals['Platform'].str.replace('_total', '').str.capitalize()
    
    fig_pie = px.pie(
        platform_totals,
        values='Total',
        names='Platform',
        hole=0.4,
        color_discrete_sequence=['#667eea', '#9c27b0', '#9b51e0', '#3498db']
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    # Weekly Summary Section
    st.markdown("### 📅 Weekly Performance Summary")
    
    today = df['date'].max()
    week_ago = today - timedelta(days=7)
    week_df = df[df['date'] > week_ago]
    
    weekly = week_df.groupby('user').agg({
        'leetcode_daily_increase': 'sum',
        'skillrack_daily_increase': 'sum',
        'codechef_daily_increase': 'sum',
        'hackerrank_daily_increase': 'sum',
        'github_daily_increase': 'sum'
    }).reset_index()
    
    weekly['total_weekly_increase'] = weekly['leetcode_daily_increase'] + weekly['skillrack_daily_increase'] + weekly['codechef_daily_increase'] + weekly['hackerrank_daily_increase'] + weekly['github_daily_increase']
    
    # Top performers
    st.markdown("#### 🚀 Top Performers This Week")
    top_weekly = weekly.sort_values('total_weekly_increase', ascending=False).head(3)
    
    cols = st.columns(3)
    for i, (_, row) in enumerate(top_weekly.iterrows()):
        with cols[i]:
            st.markdown(
                f"""
                <div class="card" style="border-left-color: {'#FFD700' if i==0 else '#C0C0C0' if i==1 else '#CD7F32'};">
                    <div style="display:flex; align-items:center; margin-bottom:1rem;">
                        <h3 style="margin:0; color:{'#FFD700' if i==0 else '#C0C0C0' if i==1 else '#CD7F32'};">#{i+1}</h3>
                        <h4 style="margin:0 0 0 1rem; color:#333333;">{row['user']}</h4>
                    </div>
                    <div style="font-size:1.8rem; font-weight:bold; margin-bottom:1rem; color:#333333;">
                        {int(row['total_weekly_increase'])} <span style="font-size:1rem; color:#666666;">activities</span>
                    </div>
                    <div style="display:flex; flex-wrap:wrap;">
                        <span class="badge lc-badge">LC: {int(row['leetcode_daily_increase'])}</span>
                        <span class="badge sk-badge">SK: {int(row['skillrack_daily_increase'])}</span>
                        <span class="badge cc-badge">CC: {int(row['codechef_daily_increase'])}</span>
                        <span class="badge hr-badge">HR: {int(row['hackerrank_daily_increase'])}</span>
                        <span class="badge gh-badge">GH: {int(row['github_daily_increase'])}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # Weekly activity chart
    st.markdown("#### 📈 Weekly Activity Breakdown")
    weekly_melted = weekly.melt(
        id_vars=['user'],
        value_vars=['leetcode_daily_increase', 'skillrack_daily_increase', 'codechef_daily_increase', 'hackerrank_daily_increase', 'github_daily_increase'],
        var_name='Platform',
        value_name='Activity'
    )
    weekly_melted['Platform'] = weekly_melted['Platform'].str.replace('_daily_increase', '').str.capitalize()
    
    fig_weekly = px.bar(
        weekly_melted.sort_values('Activity', ascending=False),
        x='user',
        y='Activity',
        color='Platform',
        color_discrete_map={
            'Leetcode': '#667eea',
            'Skillrack': '#9c27b0',
            'Codechef': '#9b51e0',
            'Hackerrank': '#3498db',
            'Github': '#2ecc71'
        },
        height=500
    )
    fig_weekly.update_layout(
        xaxis_title="Team Member",
        yaxis_title="Total Activity",
        legend_title="Platform",
        barmode='stack'
    )
    st.plotly_chart(fig_weekly, use_container_width=True)
    
    # Weekly comparison table
    st.markdown("#### 📋 Detailed Weekly Stats")
    st.dataframe(
        weekly.sort_values('total_weekly_increase', ascending=False),
        column_config={
            "user": "Team Member",
            "leetcode_daily_increase": st.column_config.NumberColumn("LeetCode", format="%d"),
            "skillrack_daily_increase": st.column_config.NumberColumn("Skillrack", format="%d"),
            "codechef_daily_increase": st.column_config.NumberColumn("CodeChef", format="%d"),
            "hackerrank_daily_increase": st.column_config.NumberColumn("HackerRank", format="%d"),
            "github_daily_increase": st.column_config.NumberColumn("GitHub", format="%d"),
            "total_weekly_increase": st.column_config.NumberColumn("Total Activity", format="%d")
        },
        hide_index=True,
        use_container_width=True
    )


@st.cache_data
def load_profile_data():
    # This would come from your database or CSV
    profiles = {
        "Dinesh Kumar ": {
            "leetcode_url": "https://leetcode.com/u/H0NMwD8pgx/",
            "skillrack_url": "http://www.skillrack.com/profile/470460/a23770d067e4cbf60eaa99c5f47397c8fc43ea3e",
            "github_url": "https://github.com/dineshkumar-cmd",
            "codechef_url": "https://www.codechef.com/users/many_bees_88",
            "hackerrank_url": "https://www.hackerrank.com/dineshkumarnov30"
        },
        "Pravin": {
            "leetcode_url": "https://leetcode.com/u/pravin_5905/",
            "skillrack_url": "http://www.skillrack.com/profile/470477/21b5f47d2a322c8474c9a34362b21f976633fa1e",
            "github_url": "",
            "codechef_url": "",
            "hackerrank_url": ""
        },
        "vijaianandhan": {
            "leetcode_url": "https://leetcode.com/u/vijaianandhan/",
            "skillrack_url": "http://www.skillrack.com/profile/470496/ec60f77f7a1571e0d809e14dfbb2e6450cb8f0a9",
            "github_url": "",
            "codechef_url": "",
            "hackerrank_url": ""
        },
        "Agilesh S": {
            "leetcode_url": "https://leetcode.com/u/Gfz6n0WdOg/",
            "skillrack_url": "https://www.skillrack.com/faces/resume.xhtml?id=470448&key=c9270c3cd7d74cb9454fb74943194b4ae48b4016",
            "github_url": "https://github.com/itz-ask916",
            "codechef_url": "https://www.codechef.com/users/agilesh304",
            "hackerrank_url": "https://www.hackerrank.com/agilesh304"
        },
        "Bharathi G ": {
            "leetcode_url": "https://leetcode.com/u/Bharathi205/",
            "skillrack_url": "http://www.skillrack.com/profile/470456/d33cc0a558937e9431c83b1ed2eb328d15edca7a",
            "github_url": "",
            "codechef_url": "",
            "hackerrank_url": ""
        },
        "Jai Akash.S": {
            "leetcode_url": "https://leetcode.com/u/Jai18/",
            "skillrack_url": "http://www.skillrack.com/profile/470463/862aee4b3a65ba0bdb7de48292660009c4406c7a",
            "github_url": "",
            "codechef_url": "",
            "hackerrank_url": ""
        },
        "Santhosh": {
            "leetcode_url": "https://leetcode.com/u/Sandy@2005/",
            "skillrack_url": "http://www.skillrack.com/profile/470486/fe68318010bade92eb1942794abb41511f332e87",
            "github_url": "https://github.com/santhosh-1110",
            "codechef_url": "https://www.codechef.com/users/santhosh_1110",
            "hackerrank_url": "https://www.hackerrank.com/santhoshdeiva705"
        },
        "Yash S": {
            "leetcode_url": "https://leetcode.com/u/yash_6003/",
            "skillrack_url": "https://www.skillrack.com/faces/resume.xhtml?id=470498&key=1a3a809579fb0112d792aaee2056e264572d308b",
            "github_url": "https://github.com/yash-6003",
            "codechef_url": "https://www.codechef.com/users/yash_6003",
            "hackerrank_url": "https://www.hackerrank.com/yashsurya5454"
        },
        "V N Akash": {
            "leetcode_url": "https://leetcode.com/u/VNAkash/",
            "skillrack_url": "https://www.skillrack.com/faces/resume.xhtml?id=470449&key=845ba0ccf1e7e75af3d453f7b194364ee316cc2e",
            "github_url": "",
            "codechef_url": "",
            "hackerrank_url": ""
        },
        "Vignesh K": {
            "leetcode_url": "",
            "skillrack_url": "https://www.skillrack.com/faces/resume.xhtml?id=470495&key=914b3969fff544b6c4d4b37feb99b146c391afee",
            "github_url": "",
            "codechef_url": "",
            "hackerrank_url": ""
        },
        
    }
    return profiles

with tab3:
    # Custom CSS for this tab with improved contrast and readability
    st.markdown("""
    <style>
        .profile-header {
            background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            color: white;
        }
        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 1.2rem;
            transition: all 0.3s ease;
            border-left: 4px solid;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .platform-link {
            transition: transform 0.3s;
            text-decoration: none !important;
        }
        .platform-link:hover {
            transform: scale(1.05);
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .streak-pulse {
            animation: pulse 1.5s infinite;
        }
        /* Improved contrast for text */
        .metric-value {
            color: #2d3748 !important;  /* Dark gray for better readability */
        }
        .metric-label {
            color: #4a5568 !important;  /* Medium gray */
        }
        /* Better error visibility */
        .error-container {
            background: #fff5f5 !important;
            border-left: 4px solid #e53e3e !important;
        }
        .error-title {
            color: #c53030 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- Header Section ---
    st.markdown(f"""
    <div class="profile-header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2 style="color: white; margin: 0; font-size: 1.8rem;">👨‍💻 Individual Performance Dashboard</h2>
                <p style="color: rgba(255,255,255,0.95); margin: 0.5rem 0 0; font-size: 1rem; font-weight: 400;">
                    Track detailed coding activity and progress metrics
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- User Selection ---
    user = st.selectbox(
        "Select team member:", 
        df['user'].unique(),
        key="user_select_tab3",
        help="Select a team member to view their detailed progress",
        format_func=lambda x: f"👤 {x}"
    )
    
    # --- Data Preparation with Error Handling ---
    try:
        user_df = df[df['user']==user].sort_values('date').copy()
        
        # Calculate totals with fallback for missing columns
        platforms = {
            'leetcode': {'total': 0, 'daily': 0},
            'skillrack': {'total': 0, 'daily': 0},
            'codechef': {'total': 0, 'daily': 0},
            'hackerrank': {'total': 0, 'daily': 0},
            'github': {'total': 0, 'daily': 0}
        }
        
        for platform in platforms:
            total_col = f"{platform}_total"
            daily_col = f"{platform}_daily_increase"
            
            if total_col in user_df.columns:
                platforms[platform]['total'] = user_df[total_col].iloc[-1] if len(user_df[total_col]) > 0 else 0
            if daily_col in user_df.columns:
                platforms[platform]['daily'] = user_df[daily_col]
        
        user_df['total_solved'] = (
            user_df.get('leetcode_total', 0) + 
            user_df.get('skillrack_total', 0) + 
            user_df.get('codechef_total', 0) + 
            user_df.get('hackerrank_total', 0)
        )
        
        user_df['total_daily_increase'] = (
            user_df.get('leetcode_daily_increase', 0) + 
            user_df.get('skillrack_daily_increase', 0) + 
            user_df.get('codechef_daily_increase', 0) + 
            user_df.get('hackerrank_daily_increase', 0)
        )
        
        latest_user = user_df.iloc[-1] if len(user_df) > 0 else None
        
        if latest_user is None:
            raise ValueError("No data available for selected user")
            
    except Exception as e:
        st.markdown(f"""
        <div class="error-container" style="padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem;">
            <h4 class="error-title" style="margin-top: 0;">⚠️ Data Processing Error</h4>
            <p style="color: #4a5568;">{str(e)}</p>
            <p style="color: #718096; font-size: 0.9rem;">Please check your data and try again.</p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # --- Profile Links ---
    profile_data = load_profile_data()
    current_profile = profile_data.get(user, {})
    
    st.markdown("### 🌐 Platform Profiles")
    cols = st.columns(5)
    platform_info = [
        ("LeetCode", current_profile.get("leetcode_url"), "#ffa116", "💻"),
        ("Skillrack", current_profile.get("skillrack_url"), "#8a2be2", "📊"),
        ("GitHub", current_profile.get("github_url"), "#24292e", "🐙"),
        ("CodeChef", current_profile.get("codechef_url"), "#7b7b7b", "🍛"),
        ("HackerRank", current_profile.get("hackerrank_url"), "#2ec866", "⭐")
    ]
    
    for i, (platform, url, color, icon) in enumerate(platform_info):
        with cols[i]:
            if url:
                st.markdown(f"""
                <a href="{url}" target="_blank" class="platform-link">
                    <div style="background: {color}; color: white; padding: 1rem; 
                                border-radius: 10px; text-align: center; height: 100%;">
                        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{icon}</div>
                        <div style="font-weight: 600; font-size: 0.9rem;">{platform}</div>
                    </div>
                </a>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background: #f8f9fa; color: #4a5568; padding: 1rem; 
                            border-radius: 10px; text-align: center; height: 100%;">
                    <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">{icon}</div>
                    <div style="font-weight: 600; font-size: 0.9rem;">{platform}</div>
                    <div style="font-size: 0.75rem; color: #718096;">No profile</div>
                </div>
                """, unsafe_allow_html=True)

    # --- Metrics Cards ---
    st.markdown("### 📊 Current Stats")
    metric_cols = st.columns(3)
    
    metric_data = [
        ("Total Solved", latest_user.get('total_solved', 0), "#6a11cb", "🧮"),
        ("LeetCode", latest_user.get('leetcode_total', 0), "#2575fc", "💻"),
        ("Skillrack", latest_user.get('skillrack_total', 0), "#9c27b0", "📊"),
        ("CodeChef", latest_user.get('codechef_total', 0), "#9b51e0", "🍛"),
        ("HackerRank", latest_user.get('hackerrank_total', 0), "#3498db", "⭐"),
        ("GitHub Repos", latest_user.get('github_repos', 0), "#2ecc71", "🐙")
    ]
    
    for i, (label, value, color, icon) in enumerate(metric_data):
        with metric_cols[i % 3]:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: {color};">
                <div style="display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.8rem;">
                    <div style="background: {color}; width: 36px; height: 36px; border-radius: 50%;
                                display: flex; align-items: center; justify-content: center;
                                color: white; font-size: 1rem;">
                        {icon}
                    </div>
                    <div class="metric-label" style="font-size: 0.95rem; font-weight: 600;">{label}</div>
                </div>
                <div class="metric-value" style="font-size: 1.5rem; font-weight: 700; text-align: center;">
                    {int(value) if pd.notna(value) else 0}
                </div>
            </div>
            """, unsafe_allow_html=True)

    

# --- Activity Heatmap ---

    # --- Streak Counter ---
    user_df['active'] = (
        (user_df.get('leetcode_daily_increase', 0) > 0) |
        (user_df.get('skillrack_daily_increase', 0) > 0) |
        (user_df.get('codechef_daily_increase', 0) > 0) |
        (user_df.get('hackerrank_daily_increase', 0) > 0) |
        (user_df.get('github_daily_increase', 0) > 0)
    )
    
    streak = 0
    max_streak = 0
    current_streak_start = None
    
    for _, row in user_df.iterrows():
        if row['active']:
            if current_streak_start is None:
                current_streak_start = row['date']
                streak = 1
            else:
                streak += 1
            max_streak = max(max_streak, streak)
        else:
            current_streak_start = None
            streak = 0
    
    # Calculate insights with fallback for empty data
    avg_daily = user_df['total_daily_increase'].mean() if len(user_df) > 0 else 0
    best_day = user_df.loc[user_df['total_daily_increase'].idxmax()] if len(user_df) > 0 else None
    
    insights = [
        f"📊 <strong>Average daily activity:</strong> {round(avg_daily, 1) if pd.notna(avg_daily) else 0} problems",
        f"🚀 <strong>Best day:</strong> {best_day['date'].strftime('%b %d') if best_day is not None else 'N/A'} with {best_day['total_daily_increase'] if best_day is not None else 0} problems",
        f"🔥 <strong>Current streak:</strong> {streak} day{'s' if streak != 1 else ''}",
        f"🏆 <strong>Longest streak:</strong> {max_streak} day{'s' if max_streak != 1 else ''}"
    ]

    st.markdown("### 📈 Activity Insights")
    for insight in insights:
        st.markdown(f"""
        <div style="background: #f8f9fa;
                    padding: 0.75rem 1rem;
                    border-left: 4px solid #667eea;
                    border-radius: 4px;
                    margin-bottom: 0.5rem;
                    color: #2d3748;">
            {insight}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ff8e53 100%);
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(255,107,107,0.3);
                margin: 1.5rem 0;
                color: white;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h3 style="margin: 0 0 0.5rem; color: white; font-size: 1.4rem;">🔥 Current Coding Streak</h3>
                <div style="display: flex; align-items: baseline; gap: 1rem;">
                    <div style="font-size: 3.5rem; font-weight: 800; {'animation: pulse 1.5s infinite;' if streak >= 3 else ''}">
                        {streak}
                    </div>
                    <div style="font-size: 1.2rem;">day{'s' if streak != 1 else ''}</div>
                </div>
                <div style="margin-top: 0.5rem; font-size: 0.95rem;">
                    🏆 Longest streak: {max_streak} days
                </div>
            </div>
            <div style="width: 50%;">
                <div style="background: rgba(255,255,255,0.3); height: 24px; border-radius: 12px; overflow: hidden;">
                    <div style="background: white; height: 100%; width: {min(100, (streak/max(1,max_streak))*100)}%;
                            border-radius: 12px; transition: width 1s ease-in-out;"></div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Performance Charts ---
    tab1, tab2 = st.tabs(["📈 Cumulative Progress", "📊 Daily Activity"])
    
    with tab1:
        try:
            fig = px.line(
                user_df,
                x='date',
                y=['leetcode_total', 'skillrack_total', 'codechef_total', 'hackerrank_total'],
                color_discrete_sequence=['#ffa116', '#8a2be2', '#7b7b7b', '#2ec866'],
                height=400,
                labels={'value': 'Problems Solved', 'date': 'Date'}
            )
            fig.update_layout(
                title=f"{user}'s Cumulative Progress",
                plot_bgcolor='black',
                paper_bgcolor='black',
                hovermode="x unified",
                legend_title_text='Platform',
                font=dict(color='#2d3748')
            )
            fig.update_xaxes(gridcolor='#e2e8f0')
            fig.update_yaxes(gridcolor='#e2e8f0')
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Could not generate cumulative progress chart: {str(e)}")
    
    with tab2:
        try:
            fig = px.bar(
                user_df,
                x='date',
                y=['leetcode_daily_increase', 'skillrack_daily_increase', 
                   'codechef_daily_increase', 'hackerrank_daily_increase'],
                color_discrete_sequence=['#ffa116', '#8a2be2', '#7b7b7b', '#2ec866'],
                height=400,
                labels={'value': 'Problems Solved', 'date': 'Date'}
            )
            fig.update_layout(
                title=f"{user}'s Daily Activity",
                plot_bgcolor='black',
                paper_bgcolor='black',
                barmode='stack',
                legend_title_text='Platform',
                font=dict(color='#2d3748')
            )
            fig.update_xaxes(gridcolor='#e2e8f0')
            fig.update_yaxes(gridcolor='#e2e8f0')
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Could not generate daily activity chart: {str(e)}")

    # --- Recent Activity Table ---
    st.markdown("### 📋 Recent Activity (Last 10 Days)")
    try:
        recent_df = user_df.sort_values('date', ascending=False).head(10).copy()
        
        # Format numeric columns
        for col in recent_df.columns:
            if 'total' in col or 'increase' in col:
                recent_df[col] = recent_df[col].fillna(0).astype(int)
        
        st.dataframe(
            recent_df[['date', 'leetcode_daily_increase', 'skillrack_daily_increase',
                      'codechef_daily_increase', 'hackerrank_daily_increase', 'total_daily_increase']],
            column_config={
                "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "leetcode_daily_increase": st.column_config.NumberColumn("LeetCode", format="%d"),
                "skillrack_daily_increase": st.column_config.NumberColumn("Skillrack", format="%d"),
                "codechef_daily_increase": st.column_config.NumberColumn("CodeChef", format="%d"),
                "hackerrank_daily_increase": st.column_config.NumberColumn("HackerRank", format="%d"),
                "total_daily_increase": st.column_config.NumberColumn("Total", format="%d")
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
    except Exception as e:
        st.error(f"Could not display recent activity: {str(e)}")

with tab4:
    # Raw Data Explorer
    st.markdown("### 🔍 Raw Data Explorer")
    st.markdown("Explore and filter the complete dataset")
    
    filtered_df = df.copy()
    
    # Add filters
    cols = st.columns(3)
    with cols[0]:
        user_filter = st.multiselect("Filter by User", options=df['user'].unique())
    with cols[1]:
        date_range = st.date_input("Date Range", 
                                  value=[df['date'].min(), df['date'].max()],
                                  min_value=df['date'].min(),
                                  max_value=df['date'].max())
    with cols[2]:
        platform_filter = st.multiselect("Filter by Platform Activity", 
                                      options=['leetcode', 'skillrack', 'codechef', 'hackerrank', 'github'])
    
    # Apply filters
    if user_filter:
        filtered_df = filtered_df[filtered_df['user'].isin(user_filter)]
    if date_range and len(date_range) == 2:
        filtered_df = filtered_df[
            (filtered_df['date'] >= pd.to_datetime(date_range[0])) & 
            (filtered_df['date'] <= pd.to_datetime(date_range[1]))]
    if platform_filter:
        platform_cols = [f"{p}_daily_increase" for p in platform_filter]
        filtered_df = filtered_df[filtered_df[platform_cols].sum(axis=1) > 0]
    
    # Display data
    st.dataframe(
        filtered_df,
        column_config={
            "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
            "user": "Team Member",
            "leetcode_total": st.column_config.NumberColumn("LeetCode Total", format="%d"),
            "leetcode_daily_increase": st.column_config.NumberColumn("LeetCode Daily", format="%d"),
            "skillrack_total": st.column_config.NumberColumn("Skillrack Total", format="%d"),
            "skillrack_daily_increase": st.column_config.NumberColumn("Skillrack Daily", format="%d"),
            "codechef_total": st.column_config.NumberColumn("CodeChef Total", format="%d"),
            "codechef_daily_increase": st.column_config.NumberColumn("CodeChef Daily", format="%d"),
            "hackerrank_total": st.column_config.NumberColumn("HackerRank Total", format="%d"),
            "hackerrank_daily_increase": st.column_config.NumberColumn("HackerRank Daily", format="%d"),
            "github_repos": st.column_config.NumberColumn("GitHub Repos", format="%d"),
            "github_daily_increase": st.column_config.NumberColumn("GitHub Daily", format="%d"),
            "total_solved": st.column_config.NumberColumn("Total Solved", format="%d"),
            "total_daily_increase": st.column_config.NumberColumn("Total Daily", format="%d")
        },
        hide_index=True,
        use_container_width=True,
        height=600
    )
    
    # Download button
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download filtered data as CSV",
        data=csv,
        file_name='filtered_coding_activity.csv',
        mime='text/csv'
    )
    
    # Data summary with improved visibility
st.markdown("""
<div style="background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            margin-top: 2rem;">
    <h3 style="color: #2d3436; margin-top: 0; border-bottom: 1px solid #eee; padding-bottom: 0.5rem;">📊 Data Summary</h3>
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
""", unsafe_allow_html=True)

# Custom metric cards with improved visibility
metric_data = [
    ("Team Members", df['user'].nunique(), "#6a11cb", "👥"),
    ("Total Records", len(df), "#2575fc", "📝"),
    ("Date Range", f"{df['date'].min().date()} to {df['date'].max().date()}", "#9c27b0", "📅"),
    ("Total Solutions", int(df.groupby('user').last()['total_solved'].sum()), "#2ecc71", "✅")
]

for label, value, color, icon in metric_data:
    st.markdown(
        f"""
        <div style="background: {color}11;
                    border-left: 4px solid {color};
                    border-radius: 8px;
                    padding: 1rem;
                    transition: all 0.3s ease;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <div style="font-size: 1.2rem;">{icon}</div>
                <div style="font-size: 0.9rem; color: #555; font-weight: 600;">{label}</div>
            </div>
            <div style="font-size: 1.5rem; font-weight: 700; color: {color};">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("</div></div>", unsafe_allow_html=True)

# Add this CSS to your existing style section
st.markdown("""
<style>
    /* Improve metric card visibility */
    .stMetric {
        background-color: white;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .stMetric label {
        color: #555 !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
    }
    
    .stMetric div {
        color: #222 !important;
        font-size: 1.4rem !important;
        font-weight: 700 !important;
    }
    
    /* Improve select box visibility */
    .stSelectbox label {
        color: #555 !important;
        font-weight: 500 !important;
    }
    
    /* Improve date input visibility */
    .stDateInput label {
        color: #555 !important;
        font-weight: 500 !important;
    }
</style>
""", unsafe_allow_html=True)
# Footer
st.markdown("""
<div class="footer">
    <p>Made with ❤️ using Streamlit & Firestore | Last updated: {}</p>
    <p style="font-size:0.8rem; margin-top:0.5rem;">© {year} Coding Team Tracker | All rights reserved</p>
</div>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), year=datetime.now().year), 
unsafe_allow_html=True)
