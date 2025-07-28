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
from playwright.sync_api import sync_playwright

def send_email_summary(to_email, subject, body, from_email, app_password, name, daily_data):
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject

        # Extract data from daily_data dictionary
        lc_total = daily_data['leetcode_total']
        lc_diff = daily_data['leetcode_daily_increase']
        sr_total = daily_data['skillrack_total']
        sr_diff = daily_data['skillrack_daily_increase']
        cc_total = daily_data['codechef_total']
        cc_diff = daily_data['codechef_daily_increase']
        hr_total = daily_data['hackerrank_total']
        hr_diff = daily_data['hackerrank_daily_increase']
        gh_repos = daily_data['github_repos']
        gh_diff = daily_data['github_daily_increase']

        # Create the HTML version of your message
        html = f"""\
        <html>
          <head>
            <style>
              body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
              }}
              .header {{
                background-color: #f8f9fa;
                padding: 20px;
                text-align: center;
                border-radius: 8px 8px 0 0;
              }}
              .content {{
                padding: 20px;
                background-color: #ffffff;
                border-left: 1px solid #e1e4e8;
                border-right: 1px solid #e1e4e8;
              }}
              .stats {{
                margin: 20px 0;
              }}
              .stat-item {{
                margin-bottom: 15px;
                padding: 12px;
                background-color: #f6f8fa;
                border-radius: 6px;
                border-left: 4px solid #0366d6;
              }}
              .daily-progress {{
                font-size: 0.9em;
                color: #22863a;
                font-weight: bold;
                margin-left: 5px;
              }}
              .footer {{
                padding: 20px;
                text-align: center;
                font-size: 0.9em;
                color: #6a737d;
                background-color: #f8f9fa;
                border-radius: 0 0 8px 8px;
              }}
              .emoji {{
                font-size: 1.2em;
                margin-right: 8px;
              }}
              h1 {{
                color: #24292e;
                margin-top: 0;
              }}
              .highlight {{
                background-color: #fff8c5;
                padding: 2px 4px;
                border-radius: 4px;
              }}
            </style>
          </head>
          <body>
            <div class="header">
              <h1>🚀 Daily Coding Report</h1>
              <p>Your personalized progress update for {datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            
            <div class="content">
              <p>Hi <strong>{name}</strong>, 👋</p>
              <p>Here's your coding progress since yesterday. Keep up the great work!</p>
              
              <div class="stats">
                <div class="stat-item">
                  <span class="emoji">🧠</span> <strong>LeetCode:</strong> {lc_total} total problems
                  <span class="daily-progress">(+{lc_diff} today)</span>
                </div>
                <div class="stat-item">
                  <span class="emoji">🎯</span> <strong>SkillRack:</strong> {sr_total} total programs
                  <span class="daily-progress">(+{sr_diff} today)</span>
                </div>
                <div class="stat-item">
                  <span class="emoji">🥇</span> <strong>CodeChef:</strong> {cc_total} total problems
                  <span class="daily-progress">(+{cc_diff} today)</span>
                </div>
                <div class="stat-item">
                  <span class="emoji">🏅</span> <strong>HackerRank:</strong> {hr_total} total badges
                  <span class="daily-progress">(+{hr_diff} today)</span>
                </div>
                <div class="stat-item">
                  <span class="emoji">💻</span> <strong>GitHub:</strong> {gh_repos} total repositories
                  <span class="daily-progress">(+{gh_diff} today)</span>
                </div>
              </div>
              
              <p>Your <span class="highlight">daily total: {lc_diff + sr_diff + cc_diff + hr_diff + gh_diff}</span> problems solved across all platforms! 🎉</p>
              
              <p>Every problem you solve makes you a better developer. Keep pushing forward! 💪</p>
              
              <p><em>"The expert in anything was once a beginner."</em> - Helen Hayes</p>
            </div>
            
            <div class="footer">
              <p>Happy coding,<br>Your <strong>Code Tracking Team</strong></p>
              <p>✨ You're making progress every day!</p>
            </div>
          </body>
        </html>
        """

        # Plain text version
        text = f"""\
Hi {name},

Here's your daily coding progress report for {datetime.now().strftime('%B %d, %Y')}:

📊 Today's Progress:
- LeetCode: +{lc_diff} problems (Total: {lc_total})
- SkillRack: +{sr_diff} programs (Total: {sr_total})
- CodeChef: +{cc_diff} problems (Total: {cc_total})
- HackerRank: +{hr_diff} badges (Total: {hr_total})
- GitHub: +{gh_diff} repositories (Total: {gh_repos})

🎯 Daily Total: {lc_diff + sr_diff + cc_diff + hr_diff + gh_diff} problems solved!

Keep up the great work! Every problem you solve brings you closer to mastery.

Happy coding,
Your Code Tracking Team
"""

        # Create both plain and HTML versions
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')

        # Attach both versions
        msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, app_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"⚠ Failed to send email to {to_email}: {e}")

# ————— FIREBASE SETUP —————
cred = credentials.Certificate("coding-team-profiles-2b0b4df65b4a.json")
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred)
db = firestore.client()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.google.com/"
}

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
        url = f"https://www.hackerrank.com/rest/hackers/{username}/badges"
        params = {
            'limit': '1000',  # Increase limit to get all badges
            'filter': 'categories:problem_solving'
        }
        
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        # Count solved problems from badges data
        solved = 0
        if data and 'models' in data:
            for badge in data['models']:
                if badge['solved']:  # Only count badges where problems were solved
                    solved += badge['solved']
        
        return solved
        
    except Exception as e:
        print(f"⚠ Error scraping HackerRank ({username}): {e}")
        return 0
    
def get_github_repo_count(username):
    if not username:
        return 0
    try:
        headers = HEADERS.copy()
        if os.getenv('GITHUB_TOKEN'):
            headers['Authorization'] = f"token {os.getenv('GITHUB_TOKEN')}"
            
        url = f"https://api.github.com/users/{username}/repos?per_page=100"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return len(data)
        elif r.status_code == 403:
            print("⚠ GitHub API rate limit exceeded")
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

def get_skillrack_total(url, max_retries=3, initial_delay=2, backoff_factor=2):
    """
    Improved Skillrack scraper with:
    - Better error handling
    - Exponential backoff retry mechanism
    - More robust element selection
    - Debug logging
    - Session persistence
    """
    if not url:
        print("⚠ No Skillrack URL provided")
        return 0

    session = requests.Session()
    session.headers.update(HEADERS)
    
    # Clean the URL (remove trailing slash if present)
    url = url.rstrip('/')
    
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            # Add delay between retries (except first attempt)
            if attempt > 0:
                print(f"🔄 Retry #{attempt} after {delay} seconds...")
                time.sleep(delay)
                delay *= backoff_factor  # Exponential backoff

            print(f"🌐 Fetching Skillrack profile (attempt {attempt + 1}): {url}")
            
            # First request to get session cookies
            response = session.get(url, timeout=15)
            response.raise_for_status()
            
            # Check if we got redirected to login page
            if 'login' in response.url.lower():
                raise Exception("Redirected to login page - profile may be private")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Method 1: New layout (statistics cards)
            stats = soup.select('div.ui.statistic')
            if stats:
                print("🔍 Found statistics cards layout")
                for stat in stats:
                    label = stat.select_one('div.label')
                    value = stat.select_one('div.value')
                    if label and value and 'programs solved' in label.get_text().lower():
                        count_text = value.get_text().strip()
                        count = int(''.join(filter(str.isdigit, count_text)))
                        print(f"✅ Found programs solved: {count}")
                        return count
            
            # Method 2: Old layout (progress bar)
            progress_div = soup.find('div', class_='ui indicating progress')
            if progress_div:
                print("🔍 Found progress bar layout")
                progress_data = progress_div.get('data-value', '0')
                try:
                    count = int(float(progress_data))
                    print(f"✅ Found programs solved: {count}")
                    return count
                except ValueError:
                    pass
            
            # Method 3: Direct text search (fallback)
            page_text = soup.get_text().lower()
            if 'programs solved' in page_text:
                print("🔍 Using text search fallback")
                match = re.search(r'programs solved[\s:]*(\d+)', page_text)
                if match:
                    count = int(match.group(1))
                    print(f"✅ Found programs solved: {count}")
                    return count
            
            raise Exception("Could not find programs solved count in page")
            
        except Exception as e:
            last_exception = e
            print(f"⚠ Attempt {attempt + 1} failed: {str(e)}")
            continue
    
    print(f"❌ All {max_retries} attempts failed. Last error: {str(last_exception)}")
    return 0

# ————— MAIN DAILY SCRAPE —————
def daily_scrape_all():
    print("✅ Starting daily scrape…")
    df = read_google_sheet("coding_team_profiles")
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

        # Get current totals
        lc_total = get_leetcode_total(lc_url)
        sr_total = get_skillrack_total(sr_url)
        cc_total = get_codechef_solved(cc_id)
        hr_total = get_hackerrank_solved(hr_id)
        gh_repos = get_github_repo_count(gh_user)

        # Get yesterday's data from Firestore
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Initialize daily differences as 0 (in case no yesterday data exists)
        lc_diff = sr_diff = cc_diff = hr_diff = gh_diff = 0
        
        # Try to get yesterday's data
        try:
            coll = db.collection('users').document(name).collection('daily_totals')
            y_doc = coll.document(yesterday).get()
            
            if y_doc.exists:
                y_data = y_doc.to_dict()
                lc_diff = lc_total - y_data.get('leetcode_total', 0)
                sr_diff = sr_total - y_data.get('skillrack_total', 0)
                cc_diff = cc_total - y_data.get('codechef_total', 0)
                hr_diff = hr_total - y_data.get('hackerrank_total', 0)
                gh_diff = gh_repos - y_data.get('github_repos', 0)
        except Exception as e:
            print(f"⚠ Error fetching yesterday's data for {name}: {e}")

        # Prepare daily_data dictionary
        daily_data = {
            'leetcode_total': lc_total,
            'leetcode_daily_increase': lc_diff,
            'skillrack_total': sr_total,
            'skillrack_daily_increase': sr_diff,
            'codechef_total': cc_total,
            'codechef_daily_increase': cc_diff,
            'hackerrank_total': hr_total,
            'hackerrank_daily_increase': hr_diff,
            'github_repos': gh_repos,
            'github_daily_increase': gh_diff
            }


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

Here's your 🚀 *Daily Coding Snapshot* — you're doing great!

📊 **Progress Overview**:
- 🧠 LeetCode problems solved: **{lc_total}**
- 🎯 SkillRack programs solved: **{sr_total}**
- 🥇 CodeChef problems solved: **{cc_total}**
- 🏅 HackerRank badges: **{hr_total}**
- 💻 GitHub repositories: **{gh_repos}**

Keep pushing forward — every line of code makes you stronger! 💪  
You're building something amazing. See you tomorrow with more wins! 🔥

Happy coding,  
✨ *Your Daily Code Tracker*

"""

        subject = "📊 Your Daily Coding Summary"
        if email:
            send_email_summary(email, subject, body, from_email, app_password, name, daily_data)
        else:
            print(f"⚠ No email found for {name}, skipping email.")

        #save_daily_totals_with_increase(name, lc_total, sr_total, cc_total, hr_total, gh_repos)

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

