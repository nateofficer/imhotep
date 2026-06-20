"""
Patch: redesign the public homepage.

- "/" becomes a company landing page: big "Request a Quote" button up top,
  a short About blurb, and small footer links (View Jobs / Admin Login /
  Trainee Login) for visitors who aren't logged in.
- The old job listing page moves from "/" to "/jobs".
- "View Jobs" links and the post-job redirect are updated to point at /jobs.
- Logged-in admins/trainees who land on "/" still see their normal nav
  (admin_nav / trainee_nav) at the top, same as before.

Run from your project root (same folder as app.py):
    python patch_homepage_redesign.py
"""

import shutil
from datetime import datetime

FILE = "app.py"

REPLACEMENTS = []

# 1. public_nav(): "View Jobs" now points to /jobs instead of /
REPLACEMENTS.append((
"""def public_nav():
    return '''
    <div class="nav">
        <a href="/">View Jobs</a>
        <a href="/quote">Request a Quote</a>
        <a href="/login">Admin Login</a>
        <a href="/trainee-login">Trainee Login</a>
    </div>
    '''""",
"""def public_nav():
    return '''
    <div class="nav">
        <a href="/jobs">View Jobs</a>
        <a href="/quote">Request a Quote</a>
        <a href="/login">Admin Login</a>
        <a href="/trainee-login">Trainee Login</a>
    </div>
    '''"""
))

# 2. Move the jobs route to /jobs, add a new "/" company landing page
REPLACEMENTS.append((
"""@app.route('/')
def show_jobs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM jobs ORDER BY posted_date DESC')
    jobs = cursor.fetchall()
    conn.close()

    html = STYLE + get_nav() + "<h1>Casey's Cleaning Company - Open Positions</h1>\"""",
"""@app.route('/')
def home():
    if session.get('logged_in'):
        top_nav = admin_nav()
    elif session.get('trainee_id'):
        top_nav = trainee_nav()
    else:
        top_nav = ''

    html = STYLE + top_nav + '''
    <style>
    .hero { text-align:center; padding: 60px 20px 30px; }
    .hero h1 { font-size: 34px; color:#2c3e50; margin-bottom: 10px; }
    .hero p { color:#555; font-size:16px; margin-bottom: 28px; }
    .quote-btn-large { display:inline-block; background:#3498db; color:#fff; font-size:20px; font-weight:bold; padding:18px 50px; border-radius:8px; text-decoration:none; }
    .quote-btn-large:hover { background:#2980b9; }
    .about { max-width:680px; margin: 0 auto 50px; text-align:center; color:#444; line-height:1.7; padding: 0 20px; }
    .footer-nav { text-align:center; padding:24px; border-top:1px solid #eee; }
    .footer-nav a { font-size:13px; color:#888; margin:0 14px; text-decoration:none; }
    .footer-nav a:hover { color:#3498db; text-decoration:underline; }
    </style>

    <div class="hero">
        <h1>Casey's Cleaning Company</h1>
        <p>Reliable, detail-oriented residential &amp; commercial cleaning, proudly serving Las Vegas.</p>
        <a class="quote-btn-large" href="/quote">Request a Quote</a>
    </div>

    <div class="about">
        <p>Casey's Cleaning Company keeps Las Vegas homes and businesses spotless with a trained, background-checked team you can trust. Whether it's a one-time deep clean, a recurring service, or a short-term rental turnover, we treat every property like it's our own. (Placeholder text -- Nate, edit this paragraph to say whatever you'd like about the company.)</p>
    </div>
    '''

    if not session.get('logged_in') and not session.get('trainee_id'):
        html += '''
    <div class="footer-nav">
        <a href="/jobs">View Jobs</a>
        <a href="/login">Admin Login</a>
        <a href="/trainee-login">Trainee Login</a>
    </div>
    '''

    return html


@app.route('/jobs')
def show_jobs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM jobs ORDER BY posted_date DESC')
    jobs = cursor.fetchall()
    conn.close()

    html = STYLE + get_nav() + "<h1>Casey's Cleaning Company - Open Positions</h1>\""""
))

# 3. After posting a new job, send the admin to the jobs list (not the new homepage)
REPLACEMENTS.append((
"""                        request.form['location']))
        conn.commit()
        conn.close()
        return redirect('/')""",
"""                        request.form['location']))
        conn.commit()
        conn.close()
        return redirect('/jobs')"""
))

# 4. "Back to Jobs" / "Back" links on the apply page should point to /jobs now
REPLACEMENTS.append((
"""        return STYLE + public_nav() + '''
        <h1>Thank You!</h1>
        <p>Your application has been submitted successfully. We will review it and be in touch soon.</p>
        <a class="btn" href="/">Back to Jobs</a>
        '''

    conn.close()

    if not job:
        return STYLE + public_nav() + '<h1>Job not found</h1><a href="/">Back</a>'""",
"""        return STYLE + public_nav() + '''
        <h1>Thank You!</h1>
        <p>Your application has been submitted successfully. We will review it and be in touch soon.</p>
        <a class="btn" href="/jobs">Back to Jobs</a>
        '''

    conn.close()

    if not job:
        return STYLE + public_nav() + '<h1>Job not found</h1><a href="/jobs">Back</a>'"""
))


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    for i, (old, new) in enumerate(REPLACEMENTS, start=1):
        if old not in content:
            print(f"[{i}/4] Could not find expected block — app.py may have changed since this patch was written.")
            print("Aborting before making any changes.")
            return
        if content.count(old) != 1:
            print(f"[{i}/4] Found {content.count(old)} matches, expected exactly 1 — aborting to be safe.")
            return

    backup_name = f"{FILE}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(FILE, backup_name)
    print(f"Backup saved as {backup_name}")

    for old, new in REPLACEMENTS:
        content = content.replace(old, new)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("Done. Changes:")
    print(" - '/' is now the company landing page (big Request a Quote button + about blurb)")
    print(" - Job listings moved to '/jobs'")
    print(" - Footer nav (View Jobs / Admin Login / Trainee Login) added for public visitors")
    print(" - Post-job redirect and 'Back to Jobs' links updated to point at /jobs")


if __name__ == "__main__":
    main()
