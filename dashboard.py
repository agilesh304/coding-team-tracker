import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

st.set_page_config(page_title="Coding Team Tracker", page_icon="📊", layout="wide")

# 🔥 Initialize Firebase Admin once
if not firebase_admin._apps:
    firebase_key_dict = json.loads(st.secrets["firebase_json"])
    cred = credentials.Certificate(firebase_key_dict)
    initialize_app(cred)


st.title("📊 Coding Team Daily & Weekly Tracker")

# ————— Load Data —————
@st.cache_data
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

df = load_data()
if df.empty:
    st.warning("⚠ No data found in Firestore. Run the scraper first.")
    st.stop()

# ————— Preprocess —————
df = df.sort_values(['user', 'date']).reset_index(drop=True)
df['date'] = pd.to_datetime(df['date'])

# Ensure daily increase columns
increase_cols = [
    ('leetcode_total', 'leetcode_daily_increase'),
    ('skillrack_total', 'skillrack_daily_increase'),
    ('codechef_total', 'codechef_daily_increase'),
    ('hackerrank_total', 'hackerrank_daily_increase'),
    ('github_repos', 'github_daily_increase'),
]
for total, diff in increase_cols:
    if total in df.columns:
        df[diff] = df.groupby('user')[total].diff().fillna(0).astype(int)
    else:
        df[diff] = 0

# ————— Raw Data Tab —————
with st.expander("🧾 Raw Firestore Data"):
    st.dataframe(df.sort_values(['user','date']))

# ————— Leaderboard (Latest Totals) —————
st.subheader("🏆 Leaderboard (Latest Totals)")
latest = df.sort_values('date').groupby('user').last().reset_index()
latest['total_solved'] = (
    latest.get('leetcode_total', 0)
    + latest.get('skillrack_total', 0)
    + latest.get('codechef_total', 0)
    + latest.get('hackerrank_total', 0)
)
leaderboard = latest.sort_values('total_solved', ascending=False)
st.table(leaderboard[['user','leetcode_total','skillrack_total','codechef_total','hackerrank_total','github_repos','total_solved']])

# ————— Weekly Summary —————
st.subheader("📅 This Week’s Totals (Last 7 Days)")
today = df['date'].max()
week_ago = today - timedelta(days=7)
week_df = df[df['date'] > week_ago]

weekly = week_df.groupby('user').agg(
    leetcode_weekly=('leetcode_daily_increase','sum'),
    skillrack_weekly=('skillrack_daily_increase','sum'),
    codechef_weekly=('codechef_daily_increase','sum'),
    hackerrank_weekly=('hackerrank_daily_increase','sum'),
    github_weekly=('github_daily_increase','sum')
).reset_index()
weekly['total_weekly_increase'] = (
    weekly['leetcode_weekly']
    + weekly['skillrack_weekly']
    + weekly['codechef_weekly']
    + weekly['hackerrank_weekly']
    + weekly['github_weekly']
)
st.table(weekly.sort_values('total_weekly_increase', ascending=False))

# ————— Daily Trend & Increases —————
st.subheader("📈 Daily Trend & Increases")
user = st.selectbox("Select user:", df['user'].unique())
user_df = df[df['user']==user].sort_values('date').copy()
user_df['total_solved'] = (
    user_df.get('leetcode_total',0)
    + user_df.get('skillrack_total',0)
    + user_df.get('codechef_total',0)
    + user_df.get('hackerrank_total',0)
)

# Trend line chart
fig_trend = px.line(
    user_df,
    x='date',
    y=['leetcode_total','skillrack_total','codechef_total','hackerrank_total','github_repos','total_solved'],
    markers=True,
    title=f"Daily Totals for {user}"
)
st.plotly_chart(fig_trend, use_container_width=True)

# Daily increase bar chart
fig_inc = px.bar(
    user_df,
    x='date',
    y=['leetcode_daily_increase','skillrack_daily_increase','codechef_daily_increase','hackerrank_daily_increase','github_daily_increase'],
    title=f"Daily Increase for {user}"
)
st.plotly_chart(fig_inc, use_container_width=True)

# ————— Streak Counter (based on activity) —————
st.subheader("🔥 Current Streak")

streak = 0
max_streak = 0  # optional: track longest streak too

# Compute daily "active" flag: did user code something that day?
user_df['active'] = (
    (user_df['leetcode_daily_increase'] > 0) |
    (user_df['skillrack_daily_increase'] > 0) |
    (user_df['codechef_daily_increase'] > 0) |
    (user_df['hackerrank_daily_increase'] > 0) |
    (user_df['github_daily_increase'] > 0)
)

# sort by date just in case
user_df = user_df.sort_values('date')

last_date = None
for _, row in user_df.iterrows():
    if row['active']:
        if last_date is not None and (row['date'] - last_date).days == 1:
            streak += 1
        else:
            streak = 1
        last_date = row['date']
    else:
        # inactive day breaks streak
        streak = 0
        last_date = None
    max_streak = max(max_streak, streak)

st.metric(label=f"{user}'s Current Streak (active days)", value=streak)

st.markdown("---")
st.caption("Made with ❤️ using Streamlit & Firestore")
