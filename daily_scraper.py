import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
from read_google_sheet import read_google_sheet
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import json

def send_email_summary(to_email, subject, body, from_email, app_password):
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, app_password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"⚠ Failed to send email to {to_email}: {e}")

# ————— FIREBASE SETUP —————
firebase_key_json = os.environ.get("FIREBASE_CREDENTIALS")

if firebase_key_json is None:
    raise ValueError("❌ FIREBASE_CREDENTIALS environment variable not found.")

# Write the string content to a temporary JSON file
with open("firebase_temp_key.json", "w") as f:
    f.write(firebase_key_json)

# Initialize Firebase
cred = credentials.Certificate("firebase_temp_key.json")
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ————— NEW SCRAPERS —————
"""
def get_codechef_solved(username):
    if not username:
        return 0
    try:
        url = f"https://www.codechef.com/users/{username}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        solved_span = soup.find("section", class_="rating-data-section problems-solved").find("h5")
        if solved_span:
            m = re.search(r"\((\d+)\)", solved_span.text)
            if m:
                return int(m.group(1))
    except Exception as e:
        print(f"⚠ Error scraping CodeChef ({username}): {e}")
    return 0
"""
def get_codechef_solved(username):
    if not username:
        print("⚠ No CodeChef username provided")
        return 0
    try:
        url = f"https://www.codechef.com/users/{username}"
        print(f"🔍 Fetching CodeChef profile: {url}")
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        section = soup.find("section", class_="rating-data-section problems-solved")
        if section:
            print("✅ Found problems-solved section:")
            print(section.prettify())  # debug: see what’s inside

            # Look for all <h3> tags and match text like "Total Problems Solved: 1"
            h3_tags = section.find_all("h3")
            for tag in h3_tags:
                text = tag.get_text(strip=True)
                print(f"🪄 Found h3 text: {text}")
                m = re.search(r"Total Problems Solved:\s*(\d+)", text)
                if m:
                    print(f"✅ Parsed solved count: {m.group(1)}")
                    return int(m.group(1))
            print("⚠ 'Total Problems Solved' h3 not found or regex didn't match")
        else:
            print("⚠ problems-solved section not found")
    except Exception as e:
        print(f"⚠ Error scraping CodeChef ({username}): {e}")
    return 0



def get_hackerrank_solved(username):
    if not username:
        return 0
    try:
        url = f"https://www.hackerrank.com/profile/{username}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        badges = soup.find_all("div", class_="badge-title")
        return len(badges)
    except Exception as e:
        print(f"⚠ Error scraping HackerRank ({username}): {e}")
    return 0

def get_github_repo_count(username):
    if not username:
        return 0
    try:
        url = f"https://api.github.com/users/{username}/repos"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return len(data)
    except Exception as e:
        print(f"⚠ Error scraping GitHub ({username}): {e}")
    return 0

# ————— SAVE TO FIRESTORE —————
def save_daily_totals_with_increase(user, lc_total, sr_total, cc_total, hr_total, gh_repos):
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    coll = db.collection('users').document(user).collection('daily_totals')
    today_ref = coll.document(today)
    y_ref = coll.document(yesterday)

    # Default yesterday totals
    lc_y = sr_y = cc_y = hr_y = gh_y = 0

    y_doc = y_ref.get()
    if y_doc.exists:
        y_data = y_doc.to_dict()
        lc_y = y_data.get('leetcode_total', 0)
        sr_y = y_data.get('skillrack_total', 0)
        cc_y = y_data.get('codechef_total', 0)
        hr_y = y_data.get('hackerrank_total', 0)
        gh_y = y_data.get('github_repos', 0)

    # Compute daily increases
    lc_diff = lc_total - lc_y
    sr_diff = sr_total - sr_y
    cc_diff = cc_total - cc_y
    hr_diff = hr_total - hr_y
    gh_diff = gh_repos - gh_y

    # Prepare data payload
    data = {
        "date": today,
        "leetcode_total": lc_total,
        "skillrack_total": sr_total,
        "codechef_total": cc_total,
        "hackerrank_total": hr_total,
        "github_repos": gh_repos,

        "leetcode_daily_increase": lc_diff,
        "skillrack_daily_increase": sr_diff,
        "codechef_daily_increase": cc_diff,
        "hackerrank_daily_increase": hr_diff,
        "github_daily_increase": gh_diff
    }

    # Save to Firestore
    today_ref.set(data)

    print(f"✅ Saved for {user} on {today}: "
          f"LC={lc_total}(+{lc_diff}), SR={sr_total}(+{sr_diff}), "
          f"CC={cc_total}(+{cc_diff}), HR={hr_total}(+{hr_diff}), GH={gh_repos}(+{gh_diff})")


# ————— EXISTING SCRAPERS (leetcode & skillrack) —————
def extract_leetcode_username(url):
    if not url:
        return None
    url = url.strip()
    if not url.startswith("http"):
        return url
    m = re.search(r"/u/([^/]+)/?", url)
    return m.group(1) if m else None

def get_leetcode_total(profile_url):
    uname = extract_leetcode_username(profile_url)
    if not uname:
        return 0

    query = """
    query userStats($username: String!) {
      matchedUser(username: $username) {
        submitStats {
          acSubmissionNum {
            difficulty
            count
          }
        }
      }
    }
    """
    payload = {"query": query, "variables": {"username": uname}}
    try:
        r = requests.post("https://leetcode.com/graphql", json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        r.raise_for_status()
        arr = (r.json().get("data", {}).get("matchedUser", {}).get("submitStats", {}).get("acSubmissionNum", []))
        for entry in arr:
            if entry.get("difficulty", "").lower() == "all":
                return entry.get("count", 0)
    except Exception:
        pass
    # fallback page scrape
    try:
        r2 = requests.get(f"https://leetcode.com/u/{uname}/", headers=HEADERS, timeout=10)
        r2.raise_for_status()
        m = re.search(r'"totalSolved":\s*(\d+)', r2.text)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return 0

def get_skillrack_total(url, retries=2, delay=2):
    if not url:
        return 0
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Referer": "https://www.skillrack.com/",
        "Accept-Language": "en-US,en;q=0.9"
    }

    for attempt in range(1, retries + 2):
        try:
            print(f"🔄 Attempt {attempt} to fetch SkillRack data...")
            time.sleep(delay)
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                for stat in soup.select("div.ui.six.small.statistics > div.statistic"):
                    lbl = stat.find("div", class_="label")
                    if lbl and lbl.get_text(strip=True) == "PROGRAMS SOLVED":
                        val = stat.find("div", class_="value")
                        nums = re.findall(r"\d+", val.get_text()) if val else []
                        return int(nums[0]) if nums else 0
            else:
                print(f"❌ SkillRack request failed with status code {response.status_code}")
        except Exception as e:
            print(f"❌ Exception occurred during SkillRack scrape: {e}")
    
    print("❌ All SkillRack attempts failed.")
    return None
# ————— MAIN DAILY SCRAPE —————
def daily_scrape_all():
    print("✅ Starting daily scrape…")
    df = read_google_sheet("coding_team_profiles")
    if df is None:
        print("❌ Failed to read Google Sheet. `df` is None.")
        return
    else:
        df.columns = df.columns.str.strip()
    print(f"✅ Read {len(df)} rows")

        # your Gmail
    from_email = "bytebreakers04@gmail.com"
    app_password = "mtdb asem sbat apah"  # app password from Googl

    results = []

    for _, row in df.iterrows():
        name = row.get('Name')
        email = row.get('Email IDd')
        lc_url = row.get("LeetCode ID (eg: Gfz6n0WdOg or https://leetcode.com/u/Gfz6n0WdOg/)", "")
        sr_url = row.get("Skillrack Profile URL", "")
        cc_id = row.get("CodeChef Profile URL", "")
        hr_id = row.get("Hackerrank Profile URL", "")
        gh_user = row.get("GitHub Profile URL", "")

        print(f"\n👤 {name}")
        lc_total = get_leetcode_total(lc_url)
        print(f" LeetCode: {lc_total}")

        sr_total = get_skillrack_total(sr_url)
        print(f" Skillrack: {sr_total}")

        cc_total = get_codechef_solved(cc_id)
        print(f" CodeChef: {cc_total}")

        hr_total = get_hackerrank_solved(hr_id)
        print(f" HackerRank badges: {hr_total}")

        gh_repos = get_github_repo_count(gh_user)
        print(f" GitHub repos: {gh_repos}")

        # personalize email body
        body = f"""
Hi {name} 👋,

Here is your daily coding summary:

✅ LeetCode solved: {lc_total}
✅ Skillrack solved: {sr_total}
✅ CodeChef problems solved: {cc_total}
✅ HackerRank badges: {hr_total}
✅ GitHub repos: {gh_repos}

Keep going! 🚀
"""

        subject = "📊 Your Daily Coding Summary"
        if email:
            send_email_summary(email, subject, body, from_email, app_password)
        else:
            print(f"⚠ No email found for {name}, skipping email.")

        # save_daily_totals_with_increase(name, lc_total, sr_total, cc_total, hr_total, gh_repos)

        results.append({
            'Name': name,
            'LeetCode Total': lc_total,
            'Skillrack Total': sr_total,
            'CodeChef Total': cc_total,
            'HackerRank Badges': hr_total,
            'GitHub Repos': gh_repos
        })

    print("\n📊 Daily scrape complete.")
    for r in results:
        print(r)

if __name__ == "__main__":
    daily_scrape_all()
