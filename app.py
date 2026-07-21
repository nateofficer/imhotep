from flask import Flask, render_template, request, redirect, send_from_directory, session, url_for
from urllib.parse import quote
import cloudinary
import cloudinary.uploader
import pymysql
import pymysql.cursors
import os
import time
import random
import string
import json
from functools import wraps
from dotenv import load_dotenv
from datetime import datetime, timedelta
import calendar

load_dotenv()

app = Flask(__name__)

# Secret key for sessions
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 28800  # 8 hours  SESSION_HARDENING_V1

# Cloudinary config
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

# Admin password
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme')

# Upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# MySQL connection string from Railway
MYSQL_URL = os.environ.get('MYSQL_URL', '')


def get_db():
    """Connect to MySQL using the Railway URL."""
    # Parse mysql://user:password@host:port/dbname
    url = MYSQL_URL
    url = url.replace('mysql://', '')
    user_pass, rest = url.split('@')
    user, password = user_pass.split(':', 1)
    host_port, dbname = rest.split('/', 1)
    if ':' in host_port:
        host, port = host_port.split(':')
        port = int(port)
    else:
        host = host_port
        port = 3306

    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=dbname,
        cursorclass=pymysql.cursors.DictCursor,
        charset='utf8mb4',
        autocommit=False
    )
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            pay VARCHAR(100),
            location VARCHAR(255),
            posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(50),
            resume_filename VARCHAR(255),
            applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            job_id INT,
            license_filename VARCHAR(255),
            ok_toilets VARCHAR(10),
            ok_kneel VARCHAR(10),
            ok_adult VARCHAR(10),
            ok_background VARCHAR(10),
            ok_teamwork VARCHAR(10),
            ok_parttime VARCHAR(10),
            tech_level INT,
            has_transportation VARCHAR(10),
            has_supplies VARCHAR(10),
            score INT,
            flagged INT DEFAULT 0,
            hired INT DEFAULT 0,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_modules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            video_url VARCHAR(500),
            content TEXT,
            required INT DEFAULT 1,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            module_id INT NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT,
            option_d TEXT,
            correct_answer VARCHAR(1) NOT NULL,
            FOREIGN KEY (module_id) REFERENCES training_modules(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trainees (
            id INT AUTO_INCREMENT PRIMARY KEY,
            candidate_id INT NOT NULL,
            email VARCHAR(255) NOT NULL,
            access_code VARCHAR(20) NOT NULL UNIQUE,
            hired_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS module_progress (
            id INT AUTO_INCREMENT PRIMARY KEY,
            trainee_id INT NOT NULL,
            module_id INT NOT NULL,
            passed INT DEFAULT 0,
            attempts INT DEFAULT 0,
            completed_date DATETIME,
            FOREIGN KEY (trainee_id) REFERENCES trainees(id),
            FOREIGN KEY (module_id) REFERENCES training_modules(id),
            UNIQUE KEY unique_progress (trainee_id, module_id)
        )
    ''')

    # Insert default job if table is empty
    cursor.execute('SELECT COUNT(*) as cnt FROM jobs')
    row = cursor.fetchone()
    if row['cnt'] == 0:
        cursor.execute('''INSERT INTO jobs (title, description, pay, location)
                          VALUES (%s, %s, %s, %s)''',
                       ('Part-Time Cleaner',
                        "Join Casey's Cleaning Company! We are hiring reliable, detail-oriented part-time cleaners for residential and commercial cleaning in Las Vegas.",
                        '$15-17/hr DOE',
                        'Las Vegas, NV'))

    # --- grade columns (safe if they already exist) ---
    try:
        cursor.execute('SELECT score FROM module_progress LIMIT 1')
    except Exception:
        try:
            cursor.execute('ALTER TABLE module_progress ADD COLUMN score INT')
        except Exception:
            pass
    try:
        cursor.execute('SELECT pass_percent FROM training_modules LIMIT 1')
    except Exception:
        try:
            cursor.execute('ALTER TABLE training_modules ADD COLUMN pass_percent INT DEFAULT 100')
        except Exception:
            pass

    # --- seed the Cleaning Procedures Test once ---
    try:
        cursor.execute('SELECT id FROM training_modules WHERE title = %s', ('Cleaning Procedures Test',))
        _existing_mod = cursor.fetchone()
        if not _existing_mod:
            import json as _qjson
            _questions = _qjson.loads(r'''[["In the three-person plan, what are the three roles?", "Cleaner, floor person, and bathroom person", "Manager, cleaner, and driver", "Duster, mopper, and windexer", "Two cleaners and a supervisor", "a"], ["In the two-person method, where does the \"cleaner\" begin?", "The kitchen", "The master bathroom (sink, toilet, mirrors) but NOT the shower", "The living room", "The laundry room", "b"], ["In the two-person method, who takes the master shower and washes the bathroom floors?", "The \"cleaner\"", "The \"floor\" person", "The client", "Nobody", "b"], ["Why should you avoid jumping in to \"help\" someone else's assigned job?", "It's against company policy", "It slows everything down, and jobs get repeated or forgotten", "It wastes cleaning solution", "It doesn't matter", "b"], ["Whoever is first into the kitchen should start with...", "Mopping the floor", "Counters, stove top, microwave, toaster - anything that makes crumbs", "Windexing the windows", "Emptying the fridge", "b"], ["When you clean a bedroom or living area, where do you start?", "In the middle of the room", "At one end, and work your way around", "At the ceiling", "Wherever looks dirtiest", "b"], ["What do you dust with?", "A dry rag", "Clean towels and a bucket of water with cleaner and bleach", "A feather duster only", "Window cleaner", "b"], ["In the bathroom, what comes right after gathering supplies?", "Clean the toilet first", "Clear everything out (toiletries, rugs, towels), then dust vents and cabinets", "Wash the floor", "Start the kitchen", "b"], ["At the end of the kitchen, instead of a second person coming in to windex, that person should...", "Wait outside", "Put down mats, turn off lights, put away supplies, take out garbage, load the car", "Re-dust the counters", "Start another bathroom", "b"], ["What is the very last thing you do when finishing a house?", "Dust the ceiling fans", "Sweep, mop, and vacuum your way out the door", "Wipe the windows again", "Take a break", "b"]]''')
            _content = _qjson.loads(r'''"This test checks that you understand our cleaning routine after completing your training. Review the Routine, the room-by-room cleaning steps, and the training video, then answer all questions. You need 80% (8 of 10) to pass. You can retake it as many times as you need."''')
            cursor.execute("SELECT video_url FROM training_modules WHERE video_url IS NOT NULL AND video_url != '' ORDER BY id LIMIT 1")
            _vrow = cursor.fetchone()
            _video = _vrow['video_url'] if _vrow else ''
            cursor.execute('INSERT INTO training_modules (title, description, video_url, content, required, pass_percent) VALUES (%s,%s,%s,%s,%s,%s)',
                           ('Cleaning Procedures Test', "Final test on Casey's cleaning procedures and team routine.", _video, _content, 1, 80))
            _mod_id = cursor.lastrowid
            for _q in _questions:
                cursor.execute('INSERT INTO quiz_questions (module_id, question, option_a, option_b, option_c, option_d, correct_answer) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                               (_mod_id, _q[0], _q[1], _q[2], _q[3], _q[4], _q[5]))
    except Exception as _seed_err:
        print('seed warning:', _seed_err)

    conn.commit()
    conn.close()


# Initialize database on startup
try:
    init_db()
except Exception as e:
    print(f"DB init warning: {e}")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def trainee_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('trainee_id'):
            return redirect(url_for('trainee_login'))
        return f(*args, **kwargs)
    return decorated_function


def generate_access_code(length=8):
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace('0', '').replace('O', '').replace('1', '').replace('I', '').replace('L', '')
    return ''.join(random.choices(chars, k=length))


def calculate_score_and_flag(answers):
    score = 0
    flagged = 0
    knockouts = ['ok_toilets', 'ok_kneel', 'ok_adult', 'ok_background']
    for q in knockouts:
        if answers.get(q) == 'yes':
            score += 15
        else:
            flagged = 1
    if answers.get('ok_teamwork') == 'yes':
        score += 10
    if answers.get('ok_parttime') == 'yes':
        score += 10
    try:
        tech = int(answers.get('tech_level') or 0)
        tech = max(0, min(5, tech))
        score += tech * 2
    except (ValueError, TypeError):
        pass
    if answers.get('has_transportation') == 'yes':
        score += 5
    if answers.get('has_supplies') == 'yes':
        score += 5
    return min(score, 100), flagged


STYLE = '''
<style>
    body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; background: #f5f5f5; }
    h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
    h2 { color: #34495e; }
    .job { background: white; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .btn { background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px; border: none; cursor: pointer; font-size: 16px; }
    .btn:hover { background: #2980b9; }
    .btn-danger { background: #e74c3c; }
    .btn-danger:hover { background: #c0392b; }
    .btn-success { background: #27ae60; }
    .btn-success:hover { background: #229954; }
    form { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    input, textarea, select { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; font-size: 16px; }
    label { display: block; margin-top: 10px; font-weight: bold; color: #34495e; }
    .application { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .application.flagged { border-left: 5px solid #e74c3c; }
    .nav { margin-bottom: 20px; }
    .nav a { margin-right: 15px; color: #3498db; text-decoration: none; font-weight: bold; }
    .error { background: #ffe6e6; color: #c0392b; padding: 10px; border-radius: 5px; margin: 10px 0; }
    .success { background: #d4edda; color: #155724; padding: 10px; border-radius: 5px; margin: 10px 0; }
    .info { background: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 5px; margin: 10px 0; }
    .admin-badge { background: #2ecc71; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; margin-left: 10px; }
    .trainee-badge { background: #9b59b6; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; margin-left: 10px; }
    .flag-badge { background: #e74c3c; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; margin-left: 10px; font-weight: bold; }
    .hired-badge { background: #27ae60; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; margin-left: 10px; font-weight: bold; }
    .cert-badge { background: #f39c12; color: white; padding: 6px 14px; border-radius: 4px; font-size: 14px; margin-left: 10px; font-weight: bold; }
    .score-badge { background: #2c3e50; color: white; padding: 4px 10px; border-radius: 4px; font-size: 14px; margin-left: 10px; font-weight: bold; }
    .score-high { background: #27ae60; }
    .score-mid { background: #f39c12; }
    .score-low { background: #95a5a6; }
    .screening-section { background: #ecf0f1; padding: 15px; border-radius: 5px; margin-top: 15px; }
    .screening-section h3 { margin-top: 0; color: #2c3e50; }
    .answer-row { padding: 4px 0; }
    .answer-yes { color: #27ae60; font-weight: bold; }
    .answer-no { color: #e74c3c; font-weight: bold; }
    .radio-group { background: #f9f9f9; padding: 10px; border-radius: 5px; margin: 5px 0; }
    .radio-group label { display: inline-block; margin-right: 15px; font-weight: normal; }
    .radio-group input[type="radio"] { width: auto; margin-right: 5px; }
    .form-note { font-size: 13px; color: #7f8c8d; font-style: italic; }
    .module-card { background: white; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 5px solid #95a5a6; }
    .module-card.passed { border-left-color: #27ae60; }
    .module-card.failed { border-left-color: #e74c3c; }
    .status-label { display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; }
    .status-not-started { background: #ecf0f1; color: #7f8c8d; }
    .status-passed { background: #d4edda; color: #155724; }
    .status-failed { background: #f8d7da; color: #721c24; }
    .access-code-display { font-family: monospace; font-size: 24px; background: #2c3e50; color: white; padding: 15px; border-radius: 5px; text-align: center; letter-spacing: 4px; margin: 10px 0; }
    iframe { width: 100%; max-width: 700px; height: 400px; border: 0; border-radius: 5px; margin: 10px 0; }
    .quiz-question { background: #f9f9f9; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #3498db; }
    .quiz-question p { font-weight: bold; margin-top: 0; }
</style>
'''


def public_nav():
    return '''
    <div class="nav">
        <a href="/jobs">View Jobs</a>
        <a href="/quote">Request a Quote</a>
        <a href="/login">Admin Login</a>
        <a href="/trainee-login">Trainee Login</a>
    </div>
    '''


def admin_nav():
    return '''
<style>
nav{background:#5C3D2E;padding:0 20px;height:56px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.navbar-brand{font-family:'Lora',serif;font-size:20px;color:#FFF9F0;font-weight:600;letter-spacing:0.5px;text-decoration:none;flex-shrink:0;}
.navbar-brand span{color:#D4A843;}
.navbar-links{display:flex;align-items:center;gap:2px;flex:1 1 auto;min-width:0;overflow-x:auto;justify-content:flex-start;scrollbar-width:thin;}
.navbar-links a{font-size:13px;font-weight:700;color:rgba(255,249,240,0.72);text-decoration:none;padding:6px 9px;border-radius:6px;white-space:nowrap;flex-shrink:0;}
.navbar-links a:hover{background:rgba(255,249,240,0.12);color:#FFF9F0;}
</style>
<nav>
  <a href="/" class="navbar-brand">Casey's<span>Cleaning</span></a>
  <div class="navbar-links">
    <a href="/dashboard">Dashboard</a>
    <a href="/applications">Applications</a>
    <a href="/staff">Staff</a>
    <a href="/crm">CRM</a>
    <a href="/customers">Customers</a>
    <a href="/post-job">Post a Job</a>
    
    <a href="/trainees">Trainees</a>
    <a href="/admin/documents">Documents</a>
    <a href="/schedule">Scheduling</a>
    <a href="/schedule/calendar">Calendar</a>
    <a href="/compliance">Compliance</a>
    <a href="/logout">Logout</a>
  </div>
</nav>
'''



def trainee_nav():
    return '''
    <div class="nav">
        <a href="/training">My Training</a>
        <a href="/trainee/documents">My Documents</a>
        <a href="/timeclock">&#9200; Time Clock</a>
        <a href="/trainee-logout">Logout</a>
        <span class="trainee-badge">TRAINEE</span>
    </div>
    '''


def get_nav():
    if session.get('logged_in'):
        return admin_nav()
    if session.get('trainee_id'):
        return trainee_nav()
    return public_nav()


def yes_no(value):
    if value == 'yes':
        return '<span class="answer-yes">Yes</span>'
    elif value == 'no':
        return '<span class="answer-no">No</span>'
    return '<span style="color:#7f8c8d;">Not answered</span>'


def score_class(score):
    if score is None:
        return 'score-low'
    if score >= 75:
        return 'score-high'
    if score >= 50:
        return 'score-mid'
    return 'score-low'


def extract_youtube_id(url):
    if not url:
        return None
    url = url.strip()
    if 'youtu.be/' in url:
        return url.split('youtu.be/')[-1].split('?')[0].split('&')[0]
    if 'youtube.com/watch' in url and 'v=' in url:
        return url.split('v=')[-1].split('&')[0]
    if 'youtube.com/embed/' in url:
        return url.split('embed/')[-1].split('?')[0].split('&')[0]
    return None


def youtube_embed(url):
    vid = extract_youtube_id(url)
    if not vid:
        return ''
    return f'<iframe src="https://www.youtube.com/embed/{vid}" allowfullscreen></iframe>'


# ============ PUBLIC ROUTES ============


# ── DB Migration ──────────────────────────────────────────────────────────────
def run_doc_library_migration():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            doc_type ENUM('signable', 'admin_verified') NOT NULL DEFAULT 'signable',
            drive_link TEXT,
            description TEXT,
            active INT DEFAULT 1,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS trainee_documents (
            id INT AUTO_INCREMENT PRIMARY KEY,
            trainee_id INT NOT NULL,
            document_id INT NOT NULL,
            assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status ENUM('pending', 'signed', 'verified') DEFAULT 'pending',
            signed_date TIMESTAMP NULL,
            signature_data LONGTEXT,
            verified_by VARCHAR(255),
            verified_date TIMESTAMP NULL,
            notes TEXT,
            UNIQUE KEY unique_assignment (trainee_id, document_id)
        )
    """)

    conn.commit()
    print("✅ documents and trainee_documents tables created.")
# ── End DB Migration ──────────────────────────────────────────────────────────

@app.route('/')
def home():
    if session.get('logged_in'):
        top_nav = admin_nav()
    elif session.get('trainee_id'):
        top_nav = trainee_nav()
    else:
        top_nav = ''

    html = STYLE + top_nav + '''
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    * { box-sizing: border-box; }
    .lp { font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; color:#222; }
    .lp-hero {
        background: linear-gradient(135deg,#2c3e50 0%,#3d5a73 100%);
        color:#fff; text-align:center; padding: 44px 22px 38px;
    }
    .lp-hero h1 { font-size: 30px; line-height:1.2; margin:0 0 10px; color:#ffffff; text-shadow:0 1px 3px rgba(0,0,0,.35); }
    .lp-hero .tag { font-size:17px; opacity:.92; margin:0 0 22px; }
    .lp-cta {
        display:inline-block; background:#e67e22; color:#fff;
        font-size:19px; font-weight:800; padding:16px 40px;
        border-radius:10px; text-decoration:none;
        box-shadow:0 4px 14px rgba(0,0,0,.25);
    }
    .lp-cta:hover { background:#d35400; }
    .lp-trust {
        display:flex; flex-wrap:wrap; justify-content:center; gap:10px;
        background:#f4efe9; padding:16px 12px; margin:0;
    }
    .lp-trust span {
        font-size:13px; font-weight:700; color:#5C3D2E;
        background:#fff; border:1px solid #e2d6cc;
        padding:7px 13px; border-radius:20px;
    }
    .lp-photos {
        display:none; grid-template-columns:1fr; gap:12px;
        max-width:640px; margin:26px auto; padding:0 16px;
    }
    @media (min-width:600px){ .lp-photos { grid-template-columns:1fr 1fr 1fr; } }
    .lp-photo {
        aspect-ratio:4/3; border-radius:12px; overflow:hidden;
        background:#ddd; box-shadow:0 2px 10px rgba(0,0,0,.12);
    }
    .lp-photo img { width:100%; height:100%; object-fit:cover; display:block; }
    .lp-ph {
        width:100%; height:100%; display:flex; align-items:center;
        justify-content:center; color:#888; font-size:13px; font-weight:700;
        background:repeating-linear-gradient(45deg,#e9e4de,#e9e4de 12px,#f2eee9 12px,#f2eee9 24px);
        text-align:center; padding:10px;
    }
    .lp-services {
        display:flex; flex-wrap:wrap; justify-content:center; gap:10px;
        max-width:640px; margin:0 auto 30px; padding:0 16px;
    }
    .lp-svc {
        flex:1 1 130px; background:#fff; border:1px solid #eee;
        border-radius:10px; padding:16px 12px; text-align:center;
        box-shadow:0 1px 6px rgba(0,0,0,.06);
    }
    .lp-svc b { display:block; color:#2c3e50; font-size:15px; margin-bottom:3px; }
    .lp-svc span { font-size:12px; color:#777; }
    .lp-about {
        max-width:620px; margin:0 auto 34px; text-align:center;
        color:#444; line-height:1.7; padding:0 22px; font-size:15px;
    }
    .lp-bottom { text-align:center; padding:0 22px 44px; }
    .lp-foot {
        text-align:center; padding:20px; border-top:1px solid #eee;
        background:#fafafa;
    }
    .lp-foot a { font-size:12px; color:#aaa; margin:0 10px; text-decoration:none; }
    .lp-foot a:hover { color:#3498db; }
    </style>

    <div class="lp">
      <div class="lp-hero">
        <h1>Las Vegas&rsquo;s Trusted Home Cleaning</h1>
        <p class="tag">Spotless homes, honest pricing, people you can trust in your home.</p>
        <a class="lp-cta" href="/quote">Get My Free Quote &rarr;</a>
      </div>

      <div class="lp-trust">
        <span>&#10003; Bonded</span>
        <span>&#10003; Insured</span>
        <span>&#10003; Veteran-Owned</span>
        <span>&#10003; Background-Checked</span>
      </div>

      <div class="lp-photos">
        <!-- PHOTO_1 --><div class="lp-photo"><div class="lp-ph">Your after-photo #1<br>(swap in later)</div></div>
        <!-- PHOTO_2 --><div class="lp-photo"><div class="lp-ph">Your after-photo #2<br>(swap in later)</div></div>
        <!-- PHOTO_3 --><div class="lp-photo"><div class="lp-ph">Your after-photo #3<br>(swap in later)</div></div>
      </div>

      <div class="lp-services">
        <div class="lp-svc"><b>Standard</b><span>Regular upkeep</span></div>
        <div class="lp-svc"><b>Deep Clean</b><span>Top to bottom</span></div>
        <div class="lp-svc"><b>Move-Out</b><span>Ready for new</span></div>
        <div class="lp-svc"><b>Airbnb</b><span>Rental turnover</span></div>
      </div>

      <div class="lp-about">
        We keep Las Vegas homes spotless with a trained, background-checked team
        you can trust. One-time deep clean, recurring service, or a short-term
        rental turnover &mdash; we treat every home like it&rsquo;s our own.
      </div>

      <div class="lp-bottom">
        <a class="lp-cta" href="/quote">Get My Free Quote &rarr;</a>
      </div>
    </div>
    '''

    if not session.get('logged_in') and not session.get('trainee_id'):
        html += '''
    <div class="lp-foot">
        <a href="/jobs">Careers</a>
        <a href="/login">Admin</a>
        <a href="/trainee-login">Staff</a>
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

    html = STYLE + get_nav() + "<h1>Casey's Cleaning Company - Open Positions</h1>"
    if not jobs:
        html += '<p>No open positions at this time. Please check back soon!</p>'
    else:
        for job in jobs:
            html += f'''
            <div class="job">
                <h2>{job['title']}</h2>
                <p><strong>Pay:</strong> {job['pay'] or 'TBD'}</p>
                <p><strong>Location:</strong> {job['location'] or 'TBD'}</p>
                <p>{job['description'] or ''}</p>
                <a class="btn" href="/apply/{job['id']}">Apply Now</a>
            </div>
            '''
    return html


# ============ ADMIN AUTH ============

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            session.pop('rnd_ok', None)  # SESSION_HARDENING_V1 -- R&D unlock is per-session
            return redirect('/dashboard')
        else:
            error = '<div class="error">Incorrect password. Try again.</div>'

    return STYLE + public_nav() + f'''
    <h1>Admin Login</h1>
    {error}
    <form method="POST">
        <label>Password:</label>
        <input type="password" name="password" required autofocus>
        <button class="btn" type="submit">Login</button>
    </form>
    '''


@app.route('/logout')
def logout():
    session.clear()  # SESSION_HARDENING_V1
    return redirect('/')


# ============ ADMIN: APPLICATIONS ============


@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    # Open applications (candidates not yet hired)
    cursor.execute('''
        SELECT candidates.*, jobs.title as job_title
        FROM candidates
        LEFT JOIN jobs ON candidates.job_id = jobs.id
        ORDER BY candidates.applied_date DESC
        LIMIT 5
    ''')
    recent_apps = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) as cnt FROM candidates')
    app_count = cursor.fetchone()['cnt']

    # Active trainees
    cursor.execute('''
        SELECT trainees.*, candidates.first_name, candidates.last_name
        FROM trainees
        LEFT JOIN candidates ON trainees.candidate_id = candidates.id
        ORDER BY trainees.hired_date DESC
        LIMIT 5
    ''')
    recent_trainees = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) as cnt FROM trainees')
    trainee_count = cursor.fetchone()['cnt']

    # Recent CRM leads
    cursor.execute('''
        SELECT * FROM leads
        ORDER BY id DESC
        LIMIT 5
    ''')
    recent_leads = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) as cnt FROM leads')
    lead_count = cursor.fetchone()['cnt']

    # Upcoming cleaning jobs (scheduled/in progress, today or later)
    cursor.execute('''
        SELECT cleaning_jobs.*, customers.first_name as cust_first, customers.last_name as cust_last
        FROM cleaning_jobs
        JOIN customers ON cleaning_jobs.customer_id = customers.id
        WHERE cleaning_jobs.scheduled_date >= CURDATE()
          AND cleaning_jobs.status IN ('scheduled', 'in_progress')
        ORDER BY cleaning_jobs.scheduled_date ASC, cleaning_jobs.scheduled_time ASC
        LIMIT 5
    ''')
    recent_jobs = cursor.fetchall()
    cursor.execute('''
        SELECT COUNT(*) as cnt FROM cleaning_jobs
        WHERE scheduled_date >= CURDATE() AND status IN ('scheduled', 'in_progress')
    ''')
    job_count = cursor.fetchone()['cnt']

    # Compliance items due within 30 days
    try:
        cursor.execute('''
            SELECT COUNT(*) as cnt FROM compliance_items
            WHERE due_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
              AND status != "completed"
        ''')
        compliance_due_count = cursor.fetchone()['cnt']
        cursor.execute('''
            SELECT * FROM compliance_items
            WHERE due_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
              AND status != "completed"
            ORDER BY due_date ASC LIMIT 5
        ''')
        compliance_due_items = cursor.fetchall()
    except Exception:
        compliance_due_count = 0
        compliance_due_items = []

    # quote page view counter
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS page_counters (name VARCHAR(64) PRIMARY KEY, count INT NOT NULL DEFAULT 0)")
        cursor.execute("SELECT count FROM page_counters WHERE name = 'quote_views'")
        _qv = cursor.fetchone()
        quote_view_count = _qv['count'] if _qv else 0
    except Exception:
        quote_view_count = 0

    conn.close()

    # Build application rows
    app_rows = ''
    for a in recent_apps:
        name = f"{a['first_name']} {a['last_name']}" if a.get('first_name') else 'Unknown'
        job = a.get('job_title') or 'N/A'
        date = str(a.get('applied_date', ''))[:10]
        app_rows += f'''
            <tr>
                <td>{name}</td>
                <td>{job}</td>
                <td>{date}</td>
                <td><a class="btn btn-sm" href="/applications">View</a></td>
            </tr>'''

    # Build trainee rows
    trainee_rows = ''
    for t in recent_trainees:
        name = f"{t['first_name']} {t['last_name']}" if t.get('first_name') else 'Unknown'
        hired = str(t.get('hired_date', ''))[:10]
        trainee_rows += f'''
            <tr>
                <td>{name}</td>
                <td>{hired}</td>
                <td><a class="btn btn-sm" href="/trainee/{t['id']}">View</a></td>
            </tr>'''

    # Build lead rows
    lead_rows = ''
    for l in recent_leads:
        name = f"{l['first_name']} {l['last_name']}"
        status = l.get('status', 'new').title()
        stype = l.get('service_type', '')
        badge_color = '#e07b39' if status.lower() == 'new' else '#6b8f71'
        lead_rows += f'''
            <tr>
                <td>{name}</td>
                <td>{stype}</td>
                <td><span style="background:{badge_color};color:#fff;padding:2px 8px;border-radius:10px;font-size:0.8rem;">{status}</span></td>
                <td><a class="btn btn-sm" href="/crm">View</a></td>
            </tr>'''


    # Build upcoming job rows
    job_rows = ''
    for j in recent_jobs:
        cust_name = f"{j['cust_first']} {j['cust_last']}"
        job_date = str(j['scheduled_date'])
        job_time = format_job_time(j['scheduled_time'])
        badge = job_status_badge(j['status'])
        job_rows += f'''
            <tr>
                <td>{cust_name}</td>
                <td>{job_date} {job_time}</td>
                <td>{badge}</td>
                <td><a class="btn btn-sm" href="/schedule">View</a></td>
            </tr>'''

    # Pre-build conditional sections to avoid f-string ternary issues
    if recent_apps:
        apps_section = '<table><tr><th>Name</th><th>Position</th><th>Date</th><th></th></tr>' + app_rows + '</table>'
    else:
        apps_section = '<p class="empty-msg">No applications yet.</p>'

    if recent_trainees:
        trainees_section = '<table><tr><th>Name</th><th>Hired</th><th></th></tr>' + trainee_rows + '</table>'
    else:
        trainees_section = '<p class="empty-msg">No trainees yet.</p>'

    if recent_leads:
        leads_section = '<table><tr><th>Name</th><th>Service</th><th>Status</th><th></th></tr>' + lead_rows + '</table>'
    else:
        # --- leads list (auto-generated; fail-safe) ---
        _empty_msg = '<p class="empty-msg">No leads yet. Add one manually or share your quote request link with customers: <b>/quote</b></p>'
        _leads = None
        try:
            try:
                _c = cursor
                _c.execute("SELECT * FROM leads ORDER BY id DESC")
            except Exception:
                _c = mysql.connection.cursor()
                _c.execute("SELECT * FROM leads ORDER BY id DESC")
            _rows = _c.fetchall()
            _cols = [d[0] for d in _c.description]
            _leads = [dict(zip(_cols, _r)) for _r in _rows]
        except Exception:
            _leads = None
        if not _leads:
            leads_section = _empty_msg
        else:
            _body = ('<table style="width:100%;border-collapse:collapse">'
                     '<tr style="text-align:left;border-bottom:2px solid #ccc">'
                     '<th style="padding:8px">Name</th><th style="padding:8px">Email</th>'
                     '<th style="padding:8px">Phone</th><th style="padding:8px">Source</th>'
                     '<th style="padding:8px">Date</th><th style="padding:8px"></th></tr>')
            for _l in _leads:
                _name = (_l.get('name') or ((str(_l.get('first_name') or '') + ' ' + str(_l.get('last_name') or '')).strip()) or '-')
                _email = _l.get('email') or '-'
                _phone = _l.get('phone') or '-'
                _src = _l.get('source') or _l.get('lead_source') or _l.get('lead_source_id') or '-'
                _date = _l.get('created_at') or _l.get('date') or _l.get('created') or ''
                _lid = _l.get('id')
                _body += ('<tr style="border-bottom:1px solid #eee">'
                          '<td style="padding:8px">%s</td><td style="padding:8px">%s</td>'
                          '<td style="padding:8px">%s</td><td style="padding:8px">%s</td>'
                          '<td style="padding:8px">%s</td>'
                          '<td style="padding:8px"><form method="POST" action="/leads/%s/convert" style="margin:0">'
                          '<button type="submit" style="background:#2c3e50;color:#fff;border:none;padding:6px 12px;border-radius:6px;cursor:pointer">Convert</button>'
                          '</form></td></tr>') % (_name, _email, _phone, _src, str(_date)[:16], _lid)
            leads_section = _body + '</table>'
        # --- end leads list ---

    if recent_jobs:
        schedule_section = '<table><tr><th>Customer</th><th>Date</th><th>Status</th><th></th></tr>' + job_rows + '</table>'
    else:
        schedule_section = '<p class="empty-msg">No upcoming jobs scheduled.</p>'

    compliance_rows = ''
    for _ci in compliance_due_items:
        import datetime as _dt
        _days = (_ci['due_date'] - _dt.date.today()).days
        if _days < 0:
            _color, _urg = '#c0392b', f'OVERDUE by {abs(_days)}d'
        elif _days <= 7:
            _color, _urg = '#e67e22', f'{_days}d left'
        else:
            _color, _urg = '#f39c12', f'{_days}d left'
        _desc = _ci['description'][:40] + ('...' if len(_ci['description']) > 40 else '')
        compliance_rows += f'<tr><td>{_ci["category"]}</td><td>{_desc}</td><td><span style="color:{_color};font-weight:bold;">{_urg}</span></td><td><a class="btn btn-sm" href="/compliance/{_ci["id"]}/edit">Update</a></td></tr>'
    if compliance_due_items:
        compliance_section = f'<table><tr><th>Category</th><th>Item</th><th>Due</th><th></th></tr>{compliance_rows}</table>'
    else:
        compliance_section = '<p class="empty-msg" style="color:#27ae60;">&#10003; All compliance items are current.</p>'

    html = STYLE + admin_nav() + f'''
    <style>
        .dash-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .dash-stat {{
            background: #fff;
            border-radius: 10px;
            padding: 1.5rem 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            border-left: 5px solid #8B5E3C;
            text-decoration: none;
            color: inherit;
            transition: transform 0.15s, box-shadow 0.15s;
        }}
        .dash-stat:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 18px rgba(0,0,0,0.13);
        }}
        .dash-stat .stat-number {{
            font-size: 2.8rem;
            font-weight: 700;
            color: #8B5E3C;
            line-height: 1;
        }}
        .dash-stat .stat-label {{
            font-size: 1rem;
            color: #555;
            margin-top: 0.4rem;
            font-family: 'Nunito', sans-serif;
        }}
        .dash-stat .stat-icon {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        .dash-card {{
            background: #fff;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 1.5rem;
        }}
        .dash-card h2 {{
            font-family: 'Lora', serif;
            color: #5a3e2b;
            font-size: 1.2rem;
            margin: 0 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #f0e8df;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .dash-card h2 a {{
            font-size: 0.8rem;
            font-family: 'Nunito', sans-serif;
            color: #e07b39;
            text-decoration: none;
            font-weight: 600;
        }}
        .dash-card table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
        }}
        .dash-card th {{
            text-align: left;
            color: #8B5E3C;
            font-weight: 700;
            padding: 0.4rem 0.5rem;
            border-bottom: 1px solid #f0e8df;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .dash-card td {{
            padding: 0.5rem 0.5rem;
            border-bottom: 1px solid #faf6f2;
            color: #333;
        }}
        .dash-card tr:last-child td {{ border-bottom: none; }}
        .dash-card .empty-msg {{
            color: #aaa;
            font-style: italic;
            padding: 0.5rem 0;
        }}
        .schedule-placeholder {{
            text-align: center;
            padding: 2.5rem 1rem;
            color: #aaa;
        }}
        .schedule-placeholder .big-icon {{ font-size: 3rem; }}
        .schedule-placeholder p {{ margin: 0.5rem 0 0 0; font-style: italic; }}
        .dash-cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 1.5rem;
        }}
        .btn-sm {{
            padding: 3px 10px;
            font-size: 0.8rem;
            background: #8B5E3C;
            color: #fff;
            border-radius: 5px;
            text-decoration: none;
        }}
    </style>

    <div style="max-width:1200px;margin:2rem auto;padding:0 1.5rem;">
        <h1 style="font-family:\'Lora\',serif;color:#5a3e2b;margin-bottom:0.25rem;">Dashboard</h1>
        <p style="color:#888;font-family:\'Nunito\',sans-serif;margin-bottom:1.8rem;">Casey\'s Cleaning — Business Overview</p>

        <!-- Stat Cards -->
        <div class="dash-grid">
            <a class="dash-stat" href="/applications">
                <div class="stat-icon">📋</div>
                <div class="stat-number">{app_count}</div>
                <div class="stat-label">Open Applications</div>
            </a>
            <a class="dash-stat" href="/trainees">
                <div class="stat-icon">👷</div>
                <div class="stat-number">{trainee_count}</div>
                <div class="stat-label">Active Trainees</div>
            </a>
            <a class="dash-stat" href="/crm">
                <div class="stat-icon">📞</div>
                <div class="stat-number">{lead_count}</div>
                <div class="stat-label">CRM Leads</div>
            </a>
            <a class="dash-stat" href="/quote" target="_blank">
                <div class="stat-icon">🧮</div>
                <div class="stat-number">{quote_view_count}</div>
                <div class="stat-label">Quote Page Views</div>
            </a>
            <a class="dash-stat" href="/schedule">
                <div class="stat-icon">📅</div>
                <div class="stat-number">{job_count}</div>
                <div class="stat-label">Upcoming Jobs</div>
            </a>
            <a class="dash-stat" href="https://qbo.intuit.com/" target="_blank" rel="noopener noreferrer">
                <div class="stat-icon">&#128176;</div>
                <div class="stat-number" style="font-size:1.7rem;">QuickBooks</div>
                <div class="stat-label">Sign in to manage billing</div>
            </a>
            <a class="dash-stat" href="/compliance" style="border-left-color:{'#c0392b' if compliance_due_count > 0 else '#27ae60'};">
                <div class="stat-icon">{'&#9888;&#65039;' if compliance_due_count > 0 else '&#9989;'}</div>
                <div class="stat-number">{compliance_due_count}</div>
                <div class="stat-label">Compliance Due Soon</div>
            </a>
        </div>

        <!-- Detail Cards -->
        <div class="dash-cards-grid">

            <!-- Applications -->
            <div class="dash-card">
                <h2>Recent Applications <a href="/applications">View All →</a></h2>
                {apps_section}
            </div>

            <!-- Trainees -->
            <div class="dash-card">
                <h2>Active Trainees <a href="/trainees">View All →</a></h2>
                {trainees_section}
            </div>

            <!-- CRM Leads -->
            <div class="dash-card">
                <h2>Recent Leads <a href="/crm">View All →</a></h2>
                {leads_section}
            </div>

            <!-- Upcoming Schedule -->
            <div class="dash-card">
                <h2>Upcoming Schedule <a href="/schedule">View All →</a></h2>
                {schedule_section}
            </div>

            <!-- Compliance -->
            <div class="dash-card">
                <h2>Compliance <a href="/compliance">View All &#8594;</a></h2>
                {compliance_section}
            </div>

            <!-- Advertise -->
            <div class="dash-card">
                <h2>Advertise</h2>
                <p class="form-note" style="margin:4px 0 12px;">Click <strong>Copy link</strong>, then paste it into that ad or post. Every lead from it gets tagged with its source in your CRM.</p>

                <div class="ad-row"><a class="btn" href="https://ads.google.com/" target="_blank" rel="noopener noreferrer" style="background:#4285F4;">Google Ads</a><button class="btn copy-src" data-src="google_ads" style="background:#e9e4de;color:#3a332c;">Copy link</button><span class="ad-tip">Highest intent &mdash; people searching for a cleaner right now</span></div>

                <div class="ad-row"><a class="btn" href="https://www.facebook.com/adsmanager/manage/campaigns" target="_blank" rel="noopener noreferrer" style="background:#1877F2;">Facebook</a><button class="btn copy-src" data-src="facebook" style="background:#e9e4de;color:#3a332c;">Copy link</button><span class="ad-tip">Proven for you &mdash; keep it</span></div>

                <div class="ad-row"><a class="btn" href="https://lasvegas.craigslist.org/" target="_blank" rel="noopener noreferrer" style="background:#5C3D2E;">Craigslist</a><button class="btn copy-src" data-src="craigslist" style="background:#e9e4de;color:#3a332c;">Copy link</button><span class="ad-tip">Proven for you &mdash; keep it</span></div>

                <div class="ad-row"><a class="btn" href="https://business.nextdoor.com/" target="_blank" rel="noopener noreferrer" style="background:#8ED500;color:#123;">Nextdoor</a><button class="btn copy-src" data-src="nextdoor" style="background:#e9e4de;color:#3a332c;">Copy link</button><span class="ad-tip">Free &mdash; best channel for residential cleaning</span></div>

                <div class="ad-row"><a class="btn" href="https://www.thumbtack.com/pro/" target="_blank" rel="noopener noreferrer" style="background:#009FD9;">Thumbtack</a><button class="btn copy-src" data-src="thumbtack" style="background:#e9e4de;color:#3a332c;">Copy link</button><span class="ad-tip">Pay per lead &mdash; worth a test</span></div>

                <div class="ad-row"><a class="btn" href="https://www.instagram.com/" target="_blank" rel="noopener noreferrer" style="background:#C13584;">Instagram</a><button class="btn copy-src" data-src="instagram" style="background:#e9e4de;color:#3a332c;">Copy link</button><span class="ad-tip">Post before/after photos</span></div>

                <div class="ad-row"><a class="btn" href="https://biz.yelp.com/" target="_blank" rel="noopener noreferrer" style="background:#D32323;">Yelp</a><button class="btn copy-src" data-src="yelp" style="background:#e9e4de;color:#3a332c;">Copy link</button><span class="ad-tip">Claim the free listing; skip the paid ads</span></div>

                <div class="ad-row"><a class="btn" href="https://ads.tiktok.com/" target="_blank" rel="noopener noreferrer" style="background:#010101;">TikTok</a><button class="btn copy-src" data-src="tiktok" style="background:#e9e4de;color:#3a332c;">Copy link</button><span class="ad-tip">Better for hiring than for customers</span></div>

                <div class="ad-row"><a class="btn" href="https://teams.microsoft.com" target="_blank" rel="noopener noreferrer" style="background:#6264A7;">Teams</a><span class="ad-tip">Team communication</span></div>

                <p class="form-note" id="copied-msg" style="display:none;color:#1d9e75;font-weight:600;margin-top:10px;">Link copied &mdash; paste it into your ad.</p>
            </div>
            <style>
              .ad-row{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;}}
              .ad-row .btn{{min-width:110px;text-align:center;}}
              .ad-tip{{font-size:12px;color:#8a7f76;}}
            </style>
            <script>
            document.addEventListener('click', function(e){{
              var b = e.target.closest('.copy-src');
              if(!b) return;
              var SHORTS = {{facebook:'/fb', nextdoor:'/nd', instagram:'/ig', craigslist:'/cl', tiktok:'/tt', thumbtack:'/tb', yelp:'/yelp'}};
              var src = b.getAttribute('data-src');
              var url = window.location.origin + (SHORTS[src] || ('/quote?utm_source=' + src));
              var done = function(){{
                var m = document.getElementById('copied-msg');
                m.textContent = 'Copied: ' + url;
                m.style.display = 'block';
                b.textContent = 'Copied!';
                setTimeout(function(){{ b.textContent = 'Copy link'; }}, 1800);
              }};
              if(navigator.clipboard && navigator.clipboard.writeText){{
                navigator.clipboard.writeText(url).then(done, function(){{ window.prompt('Copy this link:', url); }});
              }} else {{
                window.prompt('Copy this link:', url);
              }}
            }});
            </script>

        </div>
    </div>
    '''
    return html

@app.route('/staff')
@login_required
def staff_list():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT candidates.*,
               trainees.id as trainee_id,
               trainees.hired_date,
               trainees.access_code
        FROM candidates
        LEFT JOIN trainees ON trainees.candidate_id = candidates.id
        WHERE candidates.status IN ('Active', 'Scheduling')
        ORDER BY candidates.first_name ASC
    ''')
    staff = cursor.fetchall()

    # Get certification status for each trainee
    cursor.execute('''
        SELECT training_modules.required, module_progress.trainee_id, module_progress.passed
        FROM training_modules
        LEFT JOIN module_progress ON module_progress.module_id = training_modules.id
    ''')
    progress_rows = cursor.fetchall()
    conn.close()

    # Build cert map: trainee_id -> certified bool
    from collections import defaultdict
    required_total = sum(1 for r in progress_rows if r['required'])
    passed_by_trainee = defaultdict(int)
    for r in progress_rows:
        if r['required'] and r['passed'] and r['trainee_id']:
            passed_by_trainee[r['trainee_id']] += 1

    html = STYLE + admin_nav()
    html += '<h1>Staff</h1>'
    html += '<p class="form-note">Showing Active and Scheduling crew members only. '
    html += '<a href="/applications">View all applicants &rarr;</a></p>'

    if not staff:
        html += '<div class="info"><p>No active staff yet. Hire someone from <a href="/applications">Applications</a> and move them to Active status.</p></div>'
        return html

    html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1rem;margin-top:1rem;">'
    for s in staff:
        name = s['first_name'] + ' ' + s['last_name']
        status = s['status'] or 'Active'
        status_color = '#27ae60' if status == 'Active' else '#3498db'
        phone = s['phone'] or 'No phone'
        email = s['email'] or 'No email'
        hired = str(s['hired_date'])[:10] if s.get('hired_date') else 'Unknown'

        # Certification badge
        if s['trainee_id']:
            passed = passed_by_trainee.get(s['trainee_id'], 0)
            if required_total > 0 and passed >= required_total:
                cert_badge = '<span style="background:#27ae60;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">CERTIFIED</span>'
            else:
                cert_badge = f'<span style="background:#f39c12;color:white;padding:2px 8px;border-radius:4px;font-size:11px;">{passed}/{required_total} modules</span>'
            trainee_link = f'<a class="btn" href="/trainee/{s["trainee_id"]}" style="font-size:12px;padding:4px 10px;">Training Record</a>'
        else:
            cert_badge = '<span style="background:#95a5a6;color:white;padding:2px 8px;border-radius:4px;font-size:11px;">No training record</span>'
            trainee_link = ''

        html += f'''
        <div class="application" style="margin:0;">
            <h2 style="margin-bottom:6px;">{name}</h2>
            <p style="margin:4px 0;">
                <span style="background:{status_color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold;">{status}</span>
                &nbsp;{cert_badge}
            </p>
            <p style="margin:8px 0 4px 0;font-size:13px;">
                <strong>Phone:</strong> {phone}
            </p>
            <p style="margin:4px 0;font-size:13px;">
                <strong>Email:</strong> {email}
            </p>
            <p style="margin:4px 0;font-size:13px;color:#888;">
                Hired: {hired}
            </p>
            <div style="margin-top:10px;">
                {trainee_link}
                <a class="btn" href="/applications" style="font-size:12px;padding:4px 10px;background:#95a5a6;">Update Status</a>
            </div>
        </div>
        '''
    html += '</div>'
    return html


@app.route('/applications')
@login_required
def view_applications():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT candidates.*, jobs.title as job_title
        FROM candidates
        LEFT JOIN jobs ON candidates.job_id = jobs.id
        ORDER BY candidates.flagged ASC, candidates.score DESC, candidates.applied_date DESC
    ''')
    apps = cursor.fetchall()
    interview_scores = {}
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS phone_interviews (id INT AUTO_INCREMENT PRIMARY KEY, candidate_id INT NOT NULL, interviewer VARCHAR(150), interview_date DATE, answers TEXT, scores TEXT, total_score INT, recommendation VARCHAR(50), notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.commit()
        cursor.execute("SELECT candidate_id, total_score FROM phone_interviews")
        for _ir in cursor.fetchall():
            interview_scores[_ir['candidate_id']] = _ir['total_score']
    except Exception:
        interview_scores = {}
    conn.close()

    html = STYLE + admin_nav() + '<h1>Job Applications</h1>'
    html += '<p class="form-note">Sorted by: not flagged first, then highest score, then newest.</p>'

    if not apps:
        html += '<p>No applications yet.</p>'
    else:
        for app_row in apps:
            resume_link = ''
            if app_row['resume_filename']:
                resume_link = f'<a class="btn" href="{app_row["resume_filename"] if str(app_row["resume_filename"]).startswith("http") else "/resume/" + app_row["resume_filename"]}" target="_blank">View Resume</a> '

            license_link = ''
            if app_row['license_filename']:
                license_link = f'<a class="btn" href="/resume/{app_row["license_filename"]}" target="_blank">View Driver\'s License</a>'

            _pos = app_row.get('job_title') or 'Cleaner'
            _sms_msg = quote(f"Hi {app_row['first_name']}, this is Nathan with Casey's Cleaning. Thanks for applying for the {_pos} position! I'd like to schedule a quick phone interview - what days and times work best for you this week?")
            _email_subj = quote("Interview Invitation - Casey's Cleaning")
            _email_body = quote(f"Hi {app_row['first_name']},\n\nThank you for applying for the {_pos} position at Casey's Cleaning. We've reviewed your application and would like to schedule a brief phone interview.\n\nPlease reply with two or three days and times that work for you this week, and I'll confirm one.\n\nLooking forward to speaking with you,\nNathan\nCasey's Cleaning")
            contact_html = (
                f'<a class="btn" href="tel:{app_row["phone"]}" style="background:#17a2b8;">Call</a> '
                f'<a class="btn" href="sms:{app_row["phone"]}?&body={_sms_msg}" style="background:#6f42c1;">Text</a> '
                f'<a class="btn" href="https://mail.google.com/mail/?view=cm&fs=1&to={app_row["email"]}&su={_email_subj}&body={_email_body}" target="_blank" style="background:#fd7e14;">Email</a>'
            )
            flag_html = '<span class="flag-badge">FLAGGED</span>' if app_row['flagged'] else ''
            hired_html = '<span class="hired-badge">HIRED</span>' if app_row['hired'] else ''
            score = app_row['score'] if app_row['score'] is not None else 0
            score_html = f'<span class="score-badge {score_class(score)}">Score: {score}/100</span>'
            _iv = interview_scores.get(app_row['id'])
            interview_html = f'<span class="score-badge {score_class(_iv)}">Interview: {_iv}/100</span>' if _iv is not None else ''
            interview_btn = f'<a class="btn" href="/admin/candidate/{app_row["id"]}/interview" style="background:#2c3e50;">Phone Interview</a>'
            flagged_class = ' flagged' if app_row['flagged'] else ''
            tech_level = app_row['tech_level'] if app_row['tech_level'] is not None else 'Not answered'

            hire_button = ''
            if not app_row['hired']:
                hire_button = f'''
                <form method="POST" action="/hire/{app_row['id']}" style="display:inline-block; margin-top:10px; box-shadow:none; padding:0; background:none;">
                    <button class="btn btn-success" type="submit">Hire & Send Training Access</button>
                </form>
                '''

            html += f'''
            <div class="application{flagged_class}">
                <h2>{app_row['first_name']} {app_row['last_name']} {score_html} {interview_html} {flag_html} {hired_html}</h2>
                <p><strong>Position:</strong> {app_row['job_title'] or 'N/A'}</p>
                <p><strong>Email:</strong> {app_row['email']}</p>
                <p><strong>Phone:</strong> {app_row['phone'] or 'Not provided'}</p>
                <p><strong>Applied:</strong> {app_row['applied_date']}</p>
                <div class="screening-section">
                    <h3>Screening Answers</h3>
                    <div class="answer-row"><strong>Comfortable cleaning toilets/bathrooms:</strong> {yes_no(app_row['ok_toilets'])}</div>
                    <div class="answer-row"><strong>Able to kneel for hand-towel cleaning:</strong> {yes_no(app_row['ok_kneel'])}</div>
                    <div class="answer-row"><strong>18 or older:</strong> {yes_no(app_row['ok_adult'])}</div>
                    <div class="answer-row"><strong>Can pass background check:</strong> {yes_no(app_row['ok_background'])}</div>
                    <div class="answer-row"><strong>Can work in a team AND individually:</strong> {yes_no(app_row['ok_teamwork'])}</div>
                    <div class="answer-row"><strong>Available 15-20 hrs/week part-time:</strong> {yes_no(app_row['ok_parttime'])}</div>
                    <div class="answer-row"><strong>Tech/internet comfort (1-5):</strong> {tech_level}</div>
                    <div class="answer-row"><strong>Has own transportation:</strong> {yes_no(app_row['has_transportation'])}</div>
                    <div class="answer-row"><strong>Has own cleaning supplies:</strong> {yes_no(app_row['has_supplies'])}</div>
                </div>
                <p style="margin-top:15px;">{resume_link}{license_link}</p>
                <p style="margin-top:8px;"><strong>Schedule interview:</strong> {contact_html}</p>
                <p style="margin-top:8px;"><strong>Phone interview:</strong> {interview_btn}</p>
                {hire_button}
                <form method="POST" action="/update-status/{app_row['id']}" style="display:inline-block; margin-left:10px;">
                    <select name="status" onchange="this.form.submit()" style="padding:4px 8px; border-radius:4px; border:1px solid #ccc; font-size:13px;">
                        {''.join(f'<option value="{s}" {"selected" if app_row.get("status")==s else ""}>{s}</option>'
                            for s in ['Applied','Reviewing','Vetted','Hired','Onboarding','Training','Active','Scheduling'])}
                    </select>
                </form>
                <form method="POST" action="/delete/{app_row['id']}" onsubmit="return confirm('Delete this application?');" style="display:inline-block; margin-top:10px; box-shadow:none; padding:0; background:none;">
                    <button class="btn btn-danger" type="submit">Delete</button>
                </form>
            </div>
            '''
    return html


@app.route('/admin/candidate/<int:candidate_id>/interview', methods=['GET', 'POST'])
@login_required
def candidate_interview(candidate_id):
    import json as _json
    import html as _html
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS phone_interviews (id INT AUTO_INCREMENT PRIMARY KEY, candidate_id INT NOT NULL, interviewer VARCHAR(150), interview_date DATE, answers TEXT, scores TEXT, total_score INT, recommendation VARCHAR(50), notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()

    cursor.execute("SELECT * FROM candidates WHERE id = %s", (candidate_id,))
    cand = cursor.fetchone()
    if not cand:
        conn.close()
        return redirect('/applications')

    questions = [
        ("Experience", "Tell me about your experience in cleaning. How long, and what kinds of spaces?"),
        ("Challenges", "Describe a challenging cleaning situation. How did you handle it and what was the outcome?"),
        ("Cleaning Process", "Walk me through your process for cleaning a room start to finish. How do you make sure nothing gets missed?"),
        ("Products & Tools", "What products and tools do you prefer? Do you have your own supplies and equipment?"),
        ("Learning New Methods", "Are you open to learning and adapting to our specific methods and standards?"),
        ("Teamwork", "Tell me about working with a team. How do you collaborate and coordinate your work?"),
        ("Transportation", "Do you have reliable transportation to different job sites?"),
        ("Quality Control", "How do you feel about supervisors or clients double-checking your work? Give an example of handling feedback."),
        ("Taking Direction", "Describe a time you received direct criticism about your work. How did you respond?"),
        ("Pay Expectations", "What are your hourly rate expectations for this position?"),
    ]

    if request.method == 'POST':
        answers = {}
        scores = {}
        total = 0
        for i in range(1, 11):
            answers[str(i)] = request.form.get('answer_%d' % i, '').strip()
            try:
                sc = int(request.form.get('score_%d' % i, 0) or 0)
            except ValueError:
                sc = 0
            scores[str(i)] = sc
            total += sc
        interviewer = request.form.get('interviewer', '').strip()
        interview_date = request.form.get('interview_date', '').strip() or None
        recommendation = request.form.get('recommendation', '').strip()
        notes = request.form.get('notes', '').strip()

        cursor.execute("SELECT id FROM phone_interviews WHERE candidate_id = %s ORDER BY id DESC LIMIT 1", (candidate_id,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                "UPDATE phone_interviews SET interviewer=%s, interview_date=%s, answers=%s, scores=%s, total_score=%s, recommendation=%s, notes=%s WHERE id=%s",
                (interviewer, interview_date, _json.dumps(answers), _json.dumps(scores), total, recommendation, notes, existing['id'])
            )
        else:
            cursor.execute(
                "INSERT INTO phone_interviews (candidate_id, interviewer, interview_date, answers, scores, total_score, recommendation, notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (candidate_id, interviewer, interview_date, _json.dumps(answers), _json.dumps(scores), total, recommendation, notes)
            )
        conn.commit()
        conn.close()
        return redirect('/applications')

    cursor.execute("SELECT * FROM phone_interviews WHERE candidate_id = %s ORDER BY id DESC LIMIT 1", (candidate_id,))
    existing = cursor.fetchone()
    conn.close()

    saved_answers, saved_scores = {}, {}
    saved_interviewer = saved_date = saved_rec = saved_notes = ''
    saved_total = None
    if existing:
        try:
            saved_answers = _json.loads(existing['answers']) if existing['answers'] else {}
            saved_scores = _json.loads(existing['scores']) if existing['scores'] else {}
        except Exception:
            saved_answers, saved_scores = {}, {}
        saved_interviewer = existing['interviewer'] or ''
        saved_date = str(existing['interview_date']) if existing['interview_date'] else ''
        saved_rec = existing['recommendation'] or ''
        saved_notes = existing['notes'] or ''
        saved_total = existing['total_score']

    app_score = cand['score'] if cand['score'] is not None else 0
    cand_name = _html.escape("%s %s" % (cand['first_name'], cand['last_name']))

    q_html = ''
    for idx, (qtitle, qtext) in enumerate(questions, start=1):
        ans = _html.escape(saved_answers.get(str(idx), ''))
        sel = saved_scores.get(str(idx), '')
        options = '<option value="">-</option>'
        for n in range(1, 11):
            selected = 'selected' if str(sel) == str(n) else ''
            options += '<option value="%d" %s>%d</option>' % (n, selected, n)
        q_html += (
            '<div class="iv-q">'
            '<h3>%d. %s</h3>'
            '<p class="iv-prompt">%s</p>'
            '<textarea name="answer_%d" rows="3" placeholder="Type their answer during the call...">%s</textarea>'
            '<label>Score (1-10): <select name="score_%d">%s</select></label>'
            '</div>'
        ) % (idx, qtitle, _html.escape(qtext), idx, ans, idx, options)

    total_badge = ''
    if saved_total is not None:
        total_badge = '<span class="score-badge %s">Interview: %s/100</span>' % (score_class(saved_total), saved_total)

    rec_options = ''
    for r in ['', 'Move to next round', 'Reject', 'Need more info']:
        selected = 'selected' if saved_rec == r else ''
        label = r if r else '-- choose --'
        rec_options += '<option value="%s" %s>%s</option>' % (r, selected, label)

    style_block = (
        '<style>'
        '.iv-q { background:#fff; border:1px solid #e0e0e0; border-radius:8px; padding:16px; margin-bottom:14px; }'
        '.iv-q h3 { margin:0 0 4px; }'
        '.iv-prompt { color:#666; font-size:14px; margin:0 0 10px; }'
        '.iv-q textarea { width:100%; padding:8px; border:1px solid #ccc; border-radius:6px; box-sizing:border-box; }'
        '.iv-q label { display:block; margin-top:8px; font-weight:bold; }'
        '.iv-q select { padding:6px; border-radius:6px; border:1px solid #ccc; margin-left:6px; }'
        '.iv-meta { margin-bottom:14px; }'
        '.iv-meta label { margin-right:20px; font-weight:bold; }'
        '.iv-meta input { padding:6px; border-radius:6px; border:1px solid #ccc; margin-left:6px; }'
        '</style>'
    )

    body = STYLE + admin_nav()
    body += '<h1>Phone Interview: %s</h1>' % cand_name
    body += '<p class="form-note">Application score: <span class="score-badge %s">App: %s/100</span> %s</p>' % (score_class(app_score), app_score, total_badge)
    body += '<form method="POST">'
    body += '<div class="iv-meta">'
    body += '<label>Interviewer: <input type="text" name="interviewer" value="%s"></label>' % _html.escape(saved_interviewer)
    body += '<label>Date: <input type="date" name="interview_date" value="%s"></label>' % saved_date
    body += '</div>'
    body += q_html
    body += '<div class="iv-q"><h3>Overall Notes</h3><textarea name="notes" rows="4" placeholder="Overall impression, anything notable...">%s</textarea></div>' % _html.escape(saved_notes)
    body += '<div class="iv-q"><h3>Recommendation</h3><select name="recommendation">%s</select></div>' % rec_options
    body += '<button class="btn btn-success" type="submit">Save Interview</button> '
    body += '<a class="btn" href="/applications">Back to Applications</a>'
    body += '</form>'
    body += style_block
    return body


@app.route('/hire/<int:candidate_id>', methods=['POST'])
@login_required
def hire_candidate(candidate_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidates WHERE id = %s', (candidate_id,))
    candidate = cursor.fetchone()
    if not candidate:
        conn.close()
        return redirect('/applications')

    cursor.execute('SELECT * FROM trainees WHERE candidate_id = %s', (candidate_id,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return redirect(f'/trainee/{existing["id"]}')

    while True:
        code = generate_access_code()
        cursor.execute('SELECT 1 FROM trainees WHERE access_code = %s', (code,))
        if not cursor.fetchone():
            break

    cursor.execute('INSERT INTO trainees (candidate_id, email, access_code) VALUES (%s, %s, %s)',
                   (candidate_id, candidate['email'], code))
    cursor.execute('UPDATE candidates SET hired = 1, status = %s WHERE id = %s',
                   ('Onboarding', candidate_id))
    trainee_id = cursor.lastrowid
    # Auto-assign onboarding documents
    cursor.execute("SELECT id FROM documents WHERE phase='onboarding'")
    onboarding_docs = cursor.fetchall()
    for doc in onboarding_docs:
        try:
            cursor.execute(
                "INSERT IGNORE INTO trainee_documents (trainee_id, document_id, status) VALUES (%s, %s, 'pending')",
                (trainee_id, doc['id'])
            )
        except Exception:
            pass
    conn.commit()
    conn.close()
    return redirect(f'/trainee/{trainee_id}')


@app.route('/update-status/<int:candidate_id>', methods=['POST'])
@login_required
def update_candidate_status(candidate_id):
    status = request.form.get('status', 'Applied')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE candidates SET status=%s WHERE id=%s', (status, candidate_id))
    conn.commit()
    conn.close()
    return redirect('/applications')

@app.route('/delete/<int:candidate_id>', methods=['POST'])
@login_required
def delete_application(candidate_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM candidates WHERE id = %s', (candidate_id,))
    conn.commit()
    conn.close()
    return redirect('/applications')


@app.route('/post-job', methods=['GET', 'POST'])
@login_required
def post_job():
    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO jobs (title, description, pay, location)
                          VALUES (%s, %s, %s, %s)''',
                       (request.form['title'],
                        request.form['description'],
                        request.form['pay'],
                        request.form['location']))
        conn.commit()
        conn.close()
        return redirect('/jobs')

    return STYLE + admin_nav() + '''
    <h1>Post a New Job</h1>
    <form method="POST">
        <label>Job Title:</label>
        <input type="text" name="title" required>
        <label>Pay:</label>
        <input type="text" name="pay" placeholder="e.g. $15-17/hr DOE">
        <label>Location:</label>
        <input type="text" name="location" placeholder="e.g. Las Vegas, NV">
        <label>Description:</label>
        <textarea name="description" rows="5"></textarea>
        <button class="btn" type="submit">Post Job</button>
    </form>
    '''


# ============ APPLY (PUBLIC) ============

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM jobs WHERE id = %s', (job_id,))
    job = cursor.fetchone()

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form.get('phone', '')

        answers = {
            'ok_toilets': request.form.get('ok_toilets'),
            'ok_kneel': request.form.get('ok_kneel'),
            'ok_adult': request.form.get('ok_adult'),
            'ok_background': request.form.get('ok_background'),
            'ok_teamwork': request.form.get('ok_teamwork'),
            'ok_parttime': request.form.get('ok_parttime'),
            'tech_level': request.form.get('tech_level'),
            'has_transportation': request.form.get('has_transportation'),
            'has_supplies': request.form.get('has_supplies'),
        }

        score, flagged = calculate_score_and_flag(answers)

        resume_filename = None
        if 'resume' in request.files:
            resume_file = request.files['resume']
            if resume_file and resume_file.filename:
                timestamp = str(int(time.time()))
                resume_filename = f"{timestamp}_resume_{resume_file.filename}"
                _up = cloudinary.uploader.upload(resume_file, resource_type="auto", folder="resumes")
                resume_filename = _up.get('secure_url')

        license_filename = None
        if 'license' in request.files:
            license_file = request.files['license']
            if license_file and license_file.filename:
                timestamp = str(int(time.time()))
                license_filename = f"{timestamp}_license_{license_file.filename}"
                license_file.save(os.path.join(UPLOAD_FOLDER, license_filename))

        try:
            tech_int = int(answers['tech_level']) if answers['tech_level'] else None
        except (ValueError, TypeError):
            tech_int = None

        cursor.execute('''INSERT INTO candidates
                          (first_name, last_name, email, phone, resume_filename, job_id,
                           license_filename, ok_toilets, ok_kneel, ok_adult, ok_background,
                           ok_teamwork, ok_parttime, tech_level, has_transportation, has_supplies,
                           score, flagged)
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                       (first_name, last_name, email, phone, resume_filename, job_id,
                        license_filename, answers['ok_toilets'], answers['ok_kneel'],
                        answers['ok_adult'], answers['ok_background'], answers['ok_teamwork'],
                        answers['ok_parttime'], tech_int, answers['has_transportation'],
                        answers['has_supplies'], score, flagged))
        conn.commit()
        conn.close()

        return STYLE + public_nav() + '''
        <h1>Thank You!</h1>
        <p>Your application has been submitted successfully. We will review it and be in touch soon.</p>
        <a class="btn" href="/jobs">Back to Jobs</a>
        '''

    conn.close()

    if not job:
        return STYLE + public_nav() + '<h1>Job not found</h1><a href="/jobs">Back</a>'

    return STYLE + public_nav() + f'''
    <h1>Apply: {job['title']}</h1>
    <p class="form-note">Please answer all questions honestly. A driver's license copy is required.</p>
    <form method="POST" enctype="multipart/form-data">

        <h2>Contact Information</h2>
        <label>First Name:</label>
        <input type="text" name="first_name" required>
        <label>Last Name:</label>
        <input type="text" name="last_name" required>
        <label>Email:</label>
        <input type="email" name="email" required>
        <label>Phone:</label>
        <input type="tel" name="phone">

        <h2>Screening Questions</h2>
        <p class="form-note">Casey's Cleaning Company performs background checks on all hires.</p>

        <label>Are you 18 or older?</label>
        <div class="radio-group">
            <label><input type="radio" name="ok_adult" value="yes" required> Yes</label>
            <label><input type="radio" name="ok_adult" value="no"> No</label>
        </div>

        <label>Are you comfortable cleaning toilets and thoroughly cleaning bathrooms?</label>
        <div class="radio-group">
            <label><input type="radio" name="ok_toilets" value="yes" required> Yes</label>
            <label><input type="radio" name="ok_toilets" value="no"> No</label>
        </div>

        <label>We clean floors with hand towels (not mops). Are you able to kneel and work on your hands and knees?</label>
        <div class="radio-group">
            <label><input type="radio" name="ok_kneel" value="yes" required> Yes</label>
            <label><input type="radio" name="ok_kneel" value="no"> No</label>
        </div>

        <label>Are you able to pass a background check?</label>
        <div class="radio-group">
            <label><input type="radio" name="ok_background" value="yes" required> Yes</label>
            <label><input type="radio" name="ok_background" value="no"> No</label>
        </div>

        <label>Our normal process uses 3-person teams, and individuals on smaller jobs. Are you comfortable working both in a team AND independently?</label>
        <div class="radio-group">
            <label><input type="radio" name="ok_teamwork" value="yes" required> Yes</label>
            <label><input type="radio" name="ok_teamwork" value="no"> No</label>
        </div>

        <label>This role starts part-time at 15-20 hours per week (DOE). Are you available for that schedule?</label>
        <div class="radio-group">
            <label><input type="radio" name="ok_parttime" value="yes" required> Yes</label>
            <label><input type="radio" name="ok_parttime" value="no"> No</label>
        </div>

        <label>Rate your comfort using the internet and technology for work communication (1 = beginner, 5 = very comfortable):</label>
        <select name="tech_level" required>
            <option value="">-- Select --</option>
            <option value="1">1 - Beginner</option>
            <option value="2">2 - Basic</option>
            <option value="3">3 - Comfortable</option>
            <option value="4">4 - Very comfortable</option>
            <option value="5">5 - Expert</option>
        </select>

        <label>Do you have your own reliable transportation? (Plus, not required)</label>
        <div class="radio-group">
            <label><input type="radio" name="has_transportation" value="yes" required> Yes</label>
            <label><input type="radio" name="has_transportation" value="no"> No</label>
        </div>

        <label>Do you have your own cleaning supplies? (Plus, not required)</label>
        <div class="radio-group">
            <label><input type="radio" name="has_supplies" value="yes" required> Yes</label>
            <label><input type="radio" name="has_supplies" value="no"> No</label>
        </div>

        <h2>Documents</h2>
        <label>Resume (PDF, DOC, etc.):</label>
        <input type="file" name="resume">
        <p class="form-note">Finalists will be asked to provide a driver's license at the background-check stage.</p>

        <button class="btn" type="submit">Submit Application</button>
    </form>
    '''


@app.route('/resume/<filename>')
@login_required
def download_resume(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ============ ADMIN: TRAINING MODULES ============

@app.route('/training-modules')
@login_required
def training_modules():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM training_modules ORDER BY created_date')
    modules = cursor.fetchall()

    html = STYLE + admin_nav() + '<h1>Training Modules</h1>'
    html += '<p><a class="btn btn-success" href="/training-modules/new">+ New Module</a></p>'

    if not modules:
        html += '<p>No training modules yet. Click "New Module" to create one.</p>'
    else:
        for m in modules:
            required_label = '<span class="status-label status-passed">Required</span>' if m['required'] else '<span class="status-label status-not-started">Optional</span>'
            cursor.execute('SELECT COUNT(*) as cnt FROM quiz_questions WHERE module_id = %s', (m['id'],))
            q_count = cursor.fetchone()['cnt']

            html += f'''
            <div class="module-card">
                <h2>{m['title']} {required_label}</h2>
                <p>{m['description'] or ''}</p>
                <p class="form-note">{q_count} quiz question(s)</p>
                <a class="btn" href="/training-modules/{m['id']}/edit">Edit</a>
                <a class="btn" href="/training-modules/{m['id']}/questions">Manage Questions</a>
                <form method="POST" action="/training-modules/{m['id']}/delete" onsubmit="return confirm('Delete this module and all its questions?');" style="display:inline-block; box-shadow:none; padding:0; background:none;">
                    <button class="btn btn-danger" type="submit">Delete</button>
                </form>
            </div>
            '''
    conn.close()
    return html


@app.route('/training-modules/new', methods=['GET', 'POST'])
@login_required
def new_module():
    if request.method == 'POST':
        required = 1 if request.form.get('required') == 'on' else 0
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO training_modules (title, description, video_url, content, required)
                          VALUES (%s, %s, %s, %s, %s)''',
                       (request.form['title'],
                        request.form.get('description', ''),
                        request.form.get('video_url', ''),
                        request.form.get('content', ''),
                        required))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return redirect(f'/training-modules/{new_id}/questions')

    return STYLE + admin_nav() + '''
    <h1>New Training Module</h1>
    <form method="POST">
        <label>Module Title:</label>
        <input type="text" name="title" required placeholder="e.g. Bathroom Cleaning 101">
        <label>Description:</label>
        <textarea name="description" rows="2" placeholder="Brief description of what this module covers"></textarea>
        <label>YouTube Video URL (optional):</label>
        <input type="text" name="video_url" placeholder="https://www.youtube.com/watch?v=...">
        <p class="form-note">Upload your training video to YouTube as "Unlisted" and paste the link here.</p>
        <label>Written Content:</label>
        <textarea name="content" rows="10" placeholder="Step-by-step instructions, key points, etc."></textarea>
        <label style="font-weight:normal;">
            <input type="checkbox" name="required" checked style="width:auto; margin-right:8px;">
            Required for certification
        </label>
        <button class="btn" type="submit">Create Module &amp; Add Questions</button>
    </form>
    '''


@app.route('/training-modules/<int:module_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_module(module_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM training_modules WHERE id = %s', (module_id,))
    module = cursor.fetchone()
    if not module:
        conn.close()
        return redirect('/training-modules')

    if request.method == 'POST':
        required = 1 if request.form.get('required') == 'on' else 0
        cursor.execute('''UPDATE training_modules
                          SET title = %s, description = %s, video_url = %s, content = %s, required = %s
                          WHERE id = %s''',
                       (request.form['title'],
                        request.form.get('description', ''),
                        request.form.get('video_url', ''),
                        request.form.get('content', ''),
                        required, module_id))
        conn.commit()
        conn.close()
        return redirect('/training-modules')

    conn.close()
    checked = 'checked' if module['required'] else ''

    return STYLE + admin_nav() + f'''
    <h1>Edit Module</h1>
    <form method="POST">
        <label>Module Title:</label>
        <input type="text" name="title" required value="{module['title']}">
        <label>Description:</label>
        <textarea name="description" rows="2">{module['description'] or ''}</textarea>
        <label>YouTube Video URL (optional):</label>
        <input type="text" name="video_url" value="{module['video_url'] or ''}">
        <label>Written Content:</label>
        <textarea name="content" rows="10">{module['content'] or ''}</textarea>
        <label style="font-weight:normal;">
            <input type="checkbox" name="required" {checked} style="width:auto; margin-right:8px;">
            Required for certification
        </label>
        <button class="btn" type="submit">Save Changes</button>
    </form>
    '''


@app.route('/training-modules/<int:module_id>/delete', methods=['POST'])
@login_required
def delete_module(module_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM quiz_questions WHERE module_id = %s', (module_id,))
    cursor.execute('DELETE FROM module_progress WHERE module_id = %s', (module_id,))
    cursor.execute('DELETE FROM training_modules WHERE id = %s', (module_id,))
    conn.commit()
    conn.close()
    return redirect('/training-modules')


@app.route('/training-modules/<int:module_id>/questions', methods=['GET', 'POST'])
@login_required
def manage_questions(module_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM training_modules WHERE id = %s', (module_id,))
    module = cursor.fetchone()
    if not module:
        conn.close()
        return redirect('/training-modules')

    if request.method == 'POST':
        correct = request.form.get('correct_answer', 'a')
        cursor.execute('''INSERT INTO quiz_questions
                          (module_id, question, option_a, option_b, option_c, option_d, correct_answer)
                          VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                       (module_id,
                        request.form['question'],
                        request.form['option_a'],
                        request.form['option_b'],
                        request.form.get('option_c', ''),
                        request.form.get('option_d', ''),
                        correct))
        conn.commit()
        conn.close()
        return redirect(f'/training-modules/{module_id}/questions')

    cursor.execute('SELECT * FROM quiz_questions WHERE module_id = %s', (module_id,))
    questions = cursor.fetchall()
    conn.close()

    html = STYLE + admin_nav() + f'<h1>Quiz Questions: {module["title"]}</h1>'
    html += '<p class="form-note">Trainees must answer ALL questions correctly to pass this module.</p>'

    if questions:
        html += '<h2>Existing Questions</h2>'
        for i, q in enumerate(questions, 1):
            html += f'''
            <div class="quiz-question">
                <p>Q{i}: {q['question']}</p>
                <p>A: {q['option_a']} {"✓" if q['correct_answer'] == 'a' else ''}</p>
                <p>B: {q['option_b']} {"✓" if q['correct_answer'] == 'b' else ''}</p>
                {f"<p>C: {q['option_c']} {'✓' if q['correct_answer'] == 'c' else ''}</p>" if q['option_c'] else ''}
                {f"<p>D: {q['option_d']} {'✓' if q['correct_answer'] == 'd' else ''}</p>" if q['option_d'] else ''}
                <form method="POST" action="/quiz-question/{q['id']}/delete" style="display:inline-block; box-shadow:none; padding:0; background:none;">
                    <button class="btn btn-danger" type="submit">Delete</button>
                </form>
            </div>
            '''

    html += '''
    <h2>Add New Question</h2>
    <form method="POST">
        <label>Question:</label>
        <textarea name="question" rows="2" required></textarea>
        <label>Option A:</label>
        <input type="text" name="option_a" required>
        <label>Option B:</label>
        <input type="text" name="option_b" required>
        <label>Option C (optional):</label>
        <input type="text" name="option_c">
        <label>Option D (optional):</label>
        <input type="text" name="option_d">
        <label>Correct Answer:</label>
        <select name="correct_answer" required>
            <option value="a">A</option>
            <option value="b">B</option>
            <option value="c">C</option>
            <option value="d">D</option>
        </select>
        <button class="btn" type="submit">Add Question</button>
    </form>
    <p><a class="btn" href="/training-modules">Back to Modules</a></p>
    '''
    return html


@app.route('/quiz-question/<int:question_id>/delete', methods=['POST'])
@login_required
def delete_question(question_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT module_id FROM quiz_questions WHERE id = %s', (question_id,))
    q = cursor.fetchone()
    if q:
        cursor.execute('DELETE FROM quiz_questions WHERE id = %s', (question_id,))
        conn.commit()
        module_id = q['module_id']
        conn.close()
        return redirect(f'/training-modules/{module_id}/questions')
    conn.close()
    return redirect('/training-modules')


# ============ ADMIN: TRAINEES ============

@app.route('/trainees')
@login_required
def trainees_list():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT trainees.*, candidates.first_name, candidates.last_name
        FROM trainees
        LEFT JOIN candidates ON trainees.candidate_id = candidates.id
        ORDER BY trainees.hired_date DESC
    ''')
    trainees = cursor.fetchall()

    cursor.execute('SELECT COUNT(*) as cnt FROM training_modules WHERE required = 1')
    required_count = cursor.fetchone()['cnt']

    html = STYLE + admin_nav() + '<h1>Trainees</h1>'

    if not trainees:
        html += '<p>No trainees yet. Hire someone from the Applications page to create a trainee.</p>'
    else:
        for t in trainees:
            cursor.execute('''
                SELECT COUNT(*) as cnt FROM module_progress mp
                JOIN training_modules tm ON mp.module_id = tm.id
                WHERE mp.trainee_id = %s AND mp.passed = 1 AND tm.required = 1
            ''', (t['id'],))
            passed_count = cursor.fetchone()['cnt']
            certified = passed_count >= required_count and required_count > 0
            cert_html = '<span class="cert-badge">CERTIFIED</span>' if certified else ''
            progress_txt = f'{passed_count}/{required_count} required modules passed' if required_count else 'No required modules set'

            html += f'''
            <div class="application">
                <h2>{t['first_name']} {t['last_name']} {cert_html}</h2>
                <p><strong>Email:</strong> {t['email']}</p>
                <p><strong>Hired:</strong> {t['hired_date']}</p>
                <p><strong>Progress:</strong> {progress_txt}</p>
                <a class="btn" href="/trainee/{t['id']}">View Details &amp; Access Code</a>
                <a class="btn" href="/admin/documents/assign/{t['id']}">Assign Documents</a>
            </div>
            '''
    conn.close()
    return html


@app.route('/trainee/<int:trainee_id>')
@login_required
def trainee_detail(trainee_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT trainees.*, candidates.first_name, candidates.last_name, candidates.phone
        FROM trainees
        LEFT JOIN candidates ON trainees.candidate_id = candidates.id
        WHERE trainees.id = %s
    ''', (trainee_id,))
    t = cursor.fetchone()

    if not t:
        conn.close()
        return redirect('/trainees')

    _results = []
    try:
        cursor.execute('SELECT tm.title AS mtitle, mp.passed, mp.score, mp.attempts, mp.completed_date FROM module_progress mp JOIN training_modules tm ON tm.id = mp.module_id WHERE mp.trainee_id = %s ORDER BY tm.title', (trainee_id,))
        _results = cursor.fetchall()
    except Exception:
        _results = []
    conn.close()

    html = STYLE + admin_nav() + f'<h1>{t["first_name"]} {t["last_name"]}</h1>'
    html += f'''
    <div class="application">
        <p><strong>Email:</strong> {t['email']}</p>
        <p><strong>Phone:</strong> {t['phone'] or 'Not provided'}</p>
        <p><strong>Hired Date:</strong> {t['hired_date']}</p>
        <h3>Trainee Access Code</h3>
        <div class="access-code-display">{t['access_code']}</div>
        
        <p class="form-note">Send this code to {t['first_name']} along with the training login URL. They will use their email ({t['email']}) and this code to log in.</p>
    </div>
    '''
    _rows = ''
    for _r in _results:
        _sc = _r.get('score')
        _sc_txt = ('%d%%' % _sc) if _sc is not None else '-'
        _status = '<span style="color:#27ae60;font-weight:bold;">PASSED</span>' if _r['passed'] else '<span style="color:#c0392b;font-weight:bold;">Not passed</span>'
        _date_txt = _r['completed_date'] if _r['completed_date'] else ''
        _rows += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (_r['mtitle'], _status, _sc_txt, _r['attempts'], _date_txt)
    if _rows:
        html += ('<div class="application"><h3>Training Results (management only)</h3>'
                 '<table style="width:100%;border-collapse:collapse;" border="1" cellpadding="6">'
                 '<tr><th align="left">Module</th><th align="left">Status</th><th align="left">Grade</th><th align="left">Attempts</th><th align="left">Completed</th></tr>'
                 + _rows + '</table></div>')
    else:
        html += '<div class="application"><h3>Training Results (management only)</h3><p class="form-note">No test results yet.</p></div>'
    return html


# ============ TRAINEE AUTH ============

@app.route('/trainee-login', methods=['GET', 'POST'])
def trainee_login():
    error = ''
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        code = request.form.get('access_code', '').strip().upper()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM trainees WHERE LOWER(email) = %s AND access_code = %s',
            (email, code)
        )
        trainee = cursor.fetchone()
        conn.close()

        if trainee:
            session['trainee_id'] = trainee['id']
            return redirect('/trainee/documents')
        else:
            error = '<div class="error">Email or access code is incorrect. Please try again.</div>'

    return STYLE + public_nav() + f'''
    <h1>Trainee Login</h1>
    <p>If you have been hired, use the email you applied with and the access code we sent you.</p>
    {error}
    <form method="POST">
        <label>Email:</label>
        <input type="email" name="email" required autofocus>
        <label>Access Code:</label>
        <input type="text" name="access_code" required style="text-transform:uppercase; letter-spacing:2px;">
        <button class="btn" type="submit">Login</button>
    </form>
    '''


@app.route('/trainee-logout')
def trainee_logout():
    session.clear()  # SESSION_HARDENING_V1
    return redirect('/')


# ============ TRAINEE: TRAINING PORTAL ============

@app.route('/training')
@trainee_required
def my_training():
    trainee_id = session.get('trainee_id')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT trainees.*, candidates.first_name
        FROM trainees LEFT JOIN candidates ON trainees.candidate_id = candidates.id
        WHERE trainees.id = %s
    ''', (trainee_id,))
    trainee = cursor.fetchone()

    cursor.execute('SELECT * FROM training_modules ORDER BY created_date')
    modules = cursor.fetchall()
    cursor.execute('SELECT * FROM module_progress WHERE trainee_id = %s', (trainee_id,))
    progress_rows = cursor.fetchall()
    progress = {p['module_id']: p for p in progress_rows}

    cursor.execute('SELECT COUNT(*) as cnt FROM training_modules WHERE required = 1')
    required_count = cursor.fetchone()['cnt']
    passed_required = sum(1 for m in modules if m['required'] and progress.get(m['id']) and progress[m['id']]['passed'])
    certified = passed_required >= required_count and required_count > 0
    conn.close()

    name = trainee['first_name'] if trainee else 'Trainee'

    html = STYLE + trainee_nav() + f'<h1>Welcome, {name}!</h1>'

    if certified:
        html += '<div class="success"><h2 style="margin-top:0;">🎉 You are CERTIFIED!</h2><p>You have passed all required modules. Great work!</p></div>'
    else:
        html += f'<div class="info"><strong>Progress:</strong> {passed_required} of {required_count} required modules passed.</div>'

    if not modules:
        html += '<p>No training modules available yet. Check back later.</p>'
    else:
        html += '<h2>Training Modules</h2>'
        html += '<p class="form-note">Complete modules in any order. You must answer ALL quiz questions correctly to pass a module.</p>'
        for m in modules:
            p = progress.get(m['id'])
            if p and p['passed']:
                status = '<span class="status-label status-passed">PASSED</span>'
                card_class = 'module-card passed'
                btn_text = 'Review'
            elif p and p['attempts'] > 0:
                status = f'<span class="status-label status-failed">Try Again ({p["attempts"]} attempt(s))</span>'
                card_class = 'module-card failed'
                btn_text = 'Retry Module'
            else:
                status = '<span class="status-label status-not-started">Not Started</span>'
                card_class = 'module-card'
                btn_text = 'Start Module'

            req_label = '<span style="color:#e74c3c; font-weight:bold;">Required</span>' if m['required'] else '<span style="color:#7f8c8d;">Optional</span>'

            html += f'''
            <div class="{card_class}">
                <h2>{m['title']}</h2>
                <p>{req_label} · {status}</p>
                <p>{m['description'] or ''}</p>
                <a class="btn" href="/training/module/{m['id']}">{btn_text}</a>
            </div>
            '''
    return html


@app.route('/training/module/<int:module_id>')
@trainee_required
def view_module(module_id):
    trainee_id = session.get('trainee_id')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM training_modules WHERE id = %s', (module_id,))
    module = cursor.fetchone()
    if not module:
        conn.close()
        return redirect('/trainee/documents')

    cursor.execute('SELECT * FROM quiz_questions WHERE module_id = %s', (module_id,))
    questions = cursor.fetchall()
    cursor.execute('SELECT * FROM module_progress WHERE trainee_id = %s AND module_id = %s',
                   (trainee_id, module_id))
    p = cursor.fetchone()
    conn.close()

    video_html = youtube_embed(module['video_url']) if module['video_url'] else ''
    content_html = (module['content'] or '').replace('\n', '<br>')

    html = STYLE + trainee_nav() + f'<h1>{module["title"]}</h1>'
    if p and p['passed']:
        html += '<div class="success">✅ You have already passed this module. Feel free to review.</div>'

    if video_html:
        html += f'<h2>Training Video</h2>{video_html}'

    if content_html:
        html += f'<h2>Instructions</h2><div class="application">{content_html}</div>'

    if questions:
        html += f'<h2>Quiz ({len(questions)} questions)</h2>'
        html += '<p class="form-note">Answer each question, then submit. Take your time.</p>'
        html += f'<form method="POST" action="/training/module/{module_id}/submit">'
        for i, q in enumerate(questions, 1):
            html += f'<div class="quiz-question"><p>Q{i}: {q["question"]}</p>'
            for letter in ['a', 'b', 'c', 'd']:
                opt = q[f'option_{letter}']
                if opt:
                    html += f'<div class="radio-group"><label><input type="radio" name="q_{q["id"]}" value="{letter}" required> {opt}</label></div>'
            html += '</div>'
        html += '<button class="btn btn-success" type="submit">Submit Quiz</button></form>'
    else:
        html += '<p class="form-note">No quiz set for this module yet. Check back later.</p>'

    html += '<p><a class="btn" href="/training">Back to My Training</a></p>'
    return html


@app.route('/training/module/<int:module_id>/submit', methods=['POST'])
@trainee_required
def submit_quiz(module_id):
    trainee_id = session.get('trainee_id')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM quiz_questions WHERE module_id = %s', (module_id,))
    questions = cursor.fetchall()

    if not questions:
        conn.close()
        return redirect(f'/training/module/{module_id}')

    correct = 0
    total = len(questions)
    for q in questions:
        answer = request.form.get(f'q_{q["id"]}', '')
        if answer == q['correct_answer']:
            correct += 1

    percent = int(round((correct / total) * 100)) if total else 0
    threshold = 100
    try:
        cursor.execute('SELECT pass_percent FROM training_modules WHERE id = %s', (module_id,))
        _mrow = cursor.fetchone()
        if _mrow and _mrow.get('pass_percent') is not None:
            threshold = _mrow['pass_percent']
    except Exception:
        threshold = 100
    passed = (percent >= threshold)

    cursor.execute('SELECT * FROM module_progress WHERE trainee_id = %s AND module_id = %s',
                   (trainee_id, module_id))
    existing = cursor.fetchone()

    if existing:
        if passed:
            cursor.execute('UPDATE module_progress SET passed = 1, score = %s, attempts = attempts + 1, completed_date = NOW() WHERE id = %s', (percent, existing['id']))
        else:
            cursor.execute('UPDATE module_progress SET score = %s, attempts = attempts + 1 WHERE id = %s', (percent, existing['id']))
    else:
        cursor.execute('INSERT INTO module_progress (trainee_id, module_id, passed, score, attempts, completed_date) VALUES (%s, %s, %s, %s, 1, %s)',
                       (trainee_id, module_id, 1 if passed else 0, percent,
                        time.strftime('%Y-%m-%d %H:%M:%S') if passed else None))
    conn.commit()
    conn.close()

    html = STYLE + trainee_nav()
    if passed:
        html += f'''
        <h1>🎉 You Passed!</h1>
        <div class="success">
            <p>You got {correct} out of {total} correct. Module complete!</p>
        </div>
        <p><a class="btn" href="/training">Back to My Training</a></p>
        '''
    else:
        html += f'''
        <h1>Not Quite</h1>
        <div class="error">
            <p>You got {correct} out of {total} correct ({percent}%). You need {threshold}% to pass this module.</p>
            <p>Review the material and try again — you can attempt as many times as you need.</p>
        </div>
        <p><a class="btn" href="/training/module/{module_id}">Review &amp; Retry</a></p>
        <p><a class="btn" href="/training">Back to My Training</a></p>
        '''
    return html


# ============ ONBOARDING MODULE ============

def onboarding_nav():
    return '''
    <div class="nav">
        <a href="/onboarding">My Onboarding</a>
        <a href="/trainee-logout">Logout</a>
        <span class="trainee-badge">ONBOARDING</span>
    </div>
    '''

ONBOARDING_STYLE = '''
<style>
    .onboard-step { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin: 15px 0; border-left: 5px solid #95a5a6; }
    .onboard-step.complete { border-left-color: #27ae60; }
    .onboard-step.pending { border-left-color: #f39c12; }
    .step-number { display: inline-block; background: #95a5a6; color: white; border-radius: 50%; width: 28px; height: 28px; text-align: center; line-height: 28px; font-weight: bold; margin-right: 10px; font-size: 14px; }
    .step-number.complete { background: #27ae60; }
    .step-number.pending { background: #f39c12; }
    .doc-box { background: #f9f9f9; border: 1px solid #ddd; border-radius: 5px; padding: 20px; margin: 15px 0; max-height: 350px; overflow-y: auto; font-size: 13px; line-height: 1.6; white-space: pre-wrap; }
    .sign-box { background: #fff3cd; border: 1px solid #ffc107; border-radius: 5px; padding: 15px; margin: 15px 0; }
    .sign-box label { color: #856404; }
    .progress-bar { background: #ecf0f1; border-radius: 10px; height: 10px; margin: 10px 0; }
    .progress-fill { background: #27ae60; border-radius: 10px; height: 10px; transition: width 0.3s; }
    .upload-area { border: 2px dashed #ddd; border-radius: 5px; padding: 20px; text-align: center; margin: 10px 0; }
    .onboard-badge { background: #e67e22; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; margin-left: 10px; font-weight: bold; }
</style>
'''


def init_onboarding_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS onboarding_forms (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            form_type VARCHAR(50) DEFAULT 'custom',
            content TEXT,
            file_filename VARCHAR(255),
            required_for VARCHAR(20) DEFAULT 'both',
            sort_order INT DEFAULT 0,
            active INT DEFAULT 1,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS onboarding_signatures (
            id INT AUTO_INCREMENT PRIMARY KEY,
            trainee_id INT NOT NULL,
            form_id INT NOT NULL,
            signed_name VARCHAR(255),
            signed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address VARCHAR(50),
            FOREIGN KEY (trainee_id) REFERENCES trainees(id),
            FOREIGN KEY (form_id) REFERENCES onboarding_forms(id),
            UNIQUE KEY unique_sig (trainee_id, form_id)
        )
    ''')
    conn.commit()
    conn.close()

try:
    init_onboarding_db()
except Exception as e:
    print(f"Onboarding DB init warning: {e}")


# ---- ADMIN: MANAGE ONBOARDING FORMS ----

@app.route('/onboarding-forms')
@login_required
def onboarding_forms_list():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM onboarding_forms ORDER BY sort_order, created_date')
    forms = cursor.fetchall()
    conn.close()

    html = STYLE + ONBOARDING_STYLE + admin_nav() + '<h1>Onboarding Forms</h1>'
    html += '<p class="form-note">These forms are presented to new hires after training. They must sign each one to complete onboarding.</p>'
    html += '<p><a class="btn btn-success" href="/onboarding-forms/new">+ Add Form / Document</a></p>'

    if not forms:
        html += '<div class="info"><p>No onboarding forms yet. Add your NCA, policies, W-4, I-9, etc.</p></div>'
    else:
        for f in forms:
            required_for_label = {'both': 'Employees & Contractors', 'employee': 'Employees only', 'contractor': 'Contractors only'}.get(f['required_for'], 'Both')
            active_badge = '<span style="background:#27ae60;color:white;padding:2px 8px;border-radius:3px;font-size:11px;">Active</span>' if f['active'] else '<span style="background:#95a5a6;color:white;padding:2px 8px;border-radius:3px;font-size:11px;">Inactive</span>'
            file_note = 'File uploaded' if f['file_filename'] else 'Text content'
            html += f'''
            <div class="onboard-step">
                <h2>#{f["sort_order"] or "?"} {f["title"]} {active_badge}</h2>
                <p><strong>Type:</strong> {f["form_type"].upper()} &nbsp;|&nbsp; <strong>Required for:</strong> {required_for_label} &nbsp;|&nbsp; {file_note}</p>
                <p>{f["description"] or ""}</p>
                <a class="btn" href="/onboarding-forms/{f["id"]}/edit">Edit</a>
                <form method="POST" action="/onboarding-forms/{f["id"]}/delete" onsubmit="return confirm('Delete this form?');" style="display:inline-block;box-shadow:none;padding:0;background:none;">
                    <button class="btn btn-danger" type="submit">Delete</button>
                </form>
            </div>
            '''
    return html


@app.route('/onboarding-forms/new', methods=['GET', 'POST'])
@login_required
def new_onboarding_form():
    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor()
        file_filename = None
        if 'form_file' in request.files:
            f = request.files['form_file']
            if f and f.filename:
                timestamp = str(int(time.time()))
                file_filename = f"{timestamp}_form_{f.filename}"
                f.save(os.path.join(UPLOAD_FOLDER, file_filename))
        cursor.execute('''INSERT INTO onboarding_forms
                          (title, description, form_type, content, file_filename, required_for, sort_order, active)
                          VALUES (%s, %s, %s, %s, %s, %s, %s, 1)''',
                       (request.form['title'],
                        request.form.get('description', ''),
                        request.form.get('form_type', 'custom'),
                        request.form.get('content', ''),
                        file_filename,
                        request.form.get('required_for', 'both'),
                        int(request.form.get('sort_order', 1))))
        conn.commit()
        conn.close()
        return redirect('/onboarding-forms')

    return STYLE + ONBOARDING_STYLE + admin_nav() + '''
    <h1>Add Onboarding Form</h1>
    <form method="POST" enctype="multipart/form-data">
        <label>Form Title:</label>
        <input type="text" name="title" required placeholder="e.g. Non-Compete Agreement, Company Policy, W-4">

        <label>Form Type:</label>
        <select name="form_type">
            <option value="nca">NCA / Non-Compete</option>
            <option value="policy">Company Policy</option>
            <option value="w4">W-4 (Employee Tax)</option>
            <option value="w9">W-9 (Contractor Tax)</option>
            <option value="i9">I-9 (Identity Verification)</option>
            <option value="custom">Other / Custom</option>
        </select>

        <label>Required For:</label>
        <select name="required_for">
            <option value="both">Both Employees & Contractors</option>
            <option value="employee">Employees Only</option>
            <option value="contractor">Contractors Only</option>
        </select>

        <label>Display Order (1 = shown first):</label>
        <input type="number" name="sort_order" value="1" min="1" max="20">

        <label>Description (shown to employee before signing):</label>
        <textarea name="description" rows="2" placeholder="Brief description of what this document is"></textarea>

        <label>Document Text (paste your NCA, policy text, etc. here):</label>
        <textarea name="content" rows="12" placeholder="Paste the full text of the document here. The employee will read this before signing."></textarea>

        <label>OR Upload a PDF/Image of the form:</label>
        <div class="upload-area">
            <input type="file" name="form_file" accept=".pdf,.doc,.docx,.png,.jpg,.jpeg">
            <p class="form-note">Upload a PDF or image instead of pasting text above</p>
        </div>

        <button class="btn btn-success" type="submit">Save Form</button>
        <a class="btn" href="/onboarding-forms" style="background:#95a5a6;">Cancel</a>
    </form>
    '''


@app.route('/onboarding-forms/<int:form_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_onboarding_form(form_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM onboarding_forms WHERE id = %s', (form_id,))
    form = cursor.fetchone()
    if not form:
        conn.close()
        return redirect('/onboarding-forms')

    if request.method == 'POST':
        file_filename = form['file_filename']
        if 'form_file' in request.files:
            f = request.files['form_file']
            if f and f.filename:
                timestamp = str(int(time.time()))
                file_filename = f"{timestamp}_form_{f.filename}"
                f.save(os.path.join(UPLOAD_FOLDER, file_filename))
        active = 1 if request.form.get('active') == 'on' else 0
        cursor.execute('''UPDATE onboarding_forms
                          SET title=%s, description=%s, form_type=%s, content=%s,
                              file_filename=%s, required_for=%s, sort_order=%s, active=%s
                          WHERE id=%s''',
                       (request.form['title'],
                        request.form.get('description', ''),
                        request.form.get('form_type', 'custom'),
                        request.form.get('content', ''),
                        file_filename,
                        request.form.get('required_for', 'both'),
                        int(request.form.get('sort_order', 1)),
                        active, form_id))
        conn.commit()
        conn.close()
        return redirect('/onboarding-forms')

    conn.close()
    type_options = ''
    for val, label in [('nca','NCA / Non-Compete'),('policy','Company Policy'),('w4','W-4'),('w9','W-9'),('i9','I-9'),('custom','Other / Custom')]:
        sel = 'selected' if form['form_type'] == val else ''
        type_options += f'<option value="{val}" {sel}>{label}</option>'
    req_options = ''
    for val, label in [('both','Both'),('employee','Employees Only'),('contractor','Contractors Only')]:
        sel = 'selected' if form['required_for'] == val else ''
        req_options += f'<option value="{val}" {sel}>{label}</option>'
    active_checked = 'checked' if form['active'] else ''
    file_note = f'<p class="form-note">Current file: {form["file_filename"]}</p>' if form['file_filename'] else ''

    return STYLE + ONBOARDING_STYLE + admin_nav() + f'''
    <h1>Edit: {form["title"]}</h1>
    <form method="POST" enctype="multipart/form-data">
        <label>Form Title:</label>
        <input type="text" name="title" required value="{form['title']}">
        <label>Form Type:</label>
        <select name="form_type">{type_options}</select>
        <label>Required For:</label>
        <select name="required_for">{req_options}</select>
        <label>Display Order:</label>
        <input type="number" name="sort_order" value="{form['sort_order'] or 1}" min="1" max="20">
        <label>Description:</label>
        <textarea name="description" rows="2">{form['description'] or ''}</textarea>
        <label>Document Text:</label>
        <textarea name="content" rows="12">{form['content'] or ''}</textarea>
        <label>Upload New File (optional):</label>
        <div class="upload-area">
            <input type="file" name="form_file" accept=".pdf,.doc,.docx,.png,.jpg,.jpeg">
            {file_note}
        </div>
        <label style="font-weight:normal;">
            <input type="checkbox" name="active" {active_checked} style="width:auto;margin-right:8px;">
            Active (visible to new hires)
        </label>
        <button class="btn btn-success" type="submit">Save Changes</button>
        <a class="btn" href="/onboarding-forms" style="background:#95a5a6;">Cancel</a>
    </form>
    '''


@app.route('/onboarding-forms/<int:form_id>/delete', methods=['POST'])
@login_required
def delete_onboarding_form(form_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM onboarding_signatures WHERE form_id = %s', (form_id,))
    cursor.execute('DELETE FROM onboarding_forms WHERE id = %s', (form_id,))
    conn.commit()
    conn.close()
    return redirect('/onboarding-forms')


@app.route('/onboarding-file/<filename>')
@login_required
def view_onboarding_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ---- ADMIN: VIEW TRAINEE ONBOARDING STATUS ----

@app.route('/trainee/<int:trainee_id>/onboarding')
@login_required
def trainee_onboarding_status(trainee_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT trainees.*, candidates.first_name, candidates.last_name
        FROM trainees LEFT JOIN candidates ON trainees.candidate_id = candidates.id
        WHERE trainees.id = %s
    ''', (trainee_id,))
    t = cursor.fetchone()
    if not t:
        conn.close()
        return redirect('/trainees')

    cursor.execute('SELECT * FROM onboarding_forms WHERE active = 1 ORDER BY sort_order, created_date')
    forms = cursor.fetchall()
    cursor.execute('SELECT * FROM onboarding_signatures WHERE trainee_id = %s', (trainee_id,))
    sigs = {s['form_id']: s for s in cursor.fetchall()}
    conn.close()

    total = len(forms)
    signed = sum(1 for f in forms if f['id'] in sigs)
    pct = int((signed / total * 100)) if total else 0

    html = STYLE + ONBOARDING_STYLE + admin_nav()
    html += f'<h1>Onboarding Status: {t["first_name"]} {t["last_name"]}</h1>'
    html += f'''
    <div class="application">
        <p><strong>Email:</strong> {t["email"]}</p>
        <p><strong>Progress:</strong> {signed}/{total} forms signed</p>
        <div class="progress-bar"><div class="progress-fill" style="width:{pct}%"></div></div>
        {"<p><strong style='color:#27ae60;'>✅ Fully Onboarded!</strong></p>" if signed == total and total > 0 else "<p><strong style='color:#f39c12;'>⏳ Onboarding in progress</strong></p>"}
    </div>
    '''
    for f in forms:
        sig = sigs.get(f['id'])
        if sig:
            status_html = f'<span class="status-label status-passed">SIGNED — {sig["signed_name"]} on {str(sig["signed_date"])[:10]}</span>'
            card_class = 'onboard-step complete'
        else:
            status_html = '<span class="status-label status-not-started">Not Signed Yet</span>'
            card_class = 'onboard-step pending'
        html += f'''
        <div class="{card_class}">
            <h3>{f["title"]}</h3>
            <p>{status_html}</p>
            {('<p class="form-note">IP recorded: ' + sig["ip_address"] + '</p>') if sig and sig.get("ip_address") else ''}
        </div>
        '''
    html += f'<p><a class="btn" href="/trainee/{trainee_id}">Back to Trainee Profile</a></p>'
    return html
    
# ---- TRAINEE: ONBOARDING PORTAL ----

@app.route('/onboarding')
@trainee_required
def trainee_onboarding():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT trainees.*, candidates.first_name, candidates.last_name
        FROM trainees LEFT JOIN candidates ON trainees.candidate_id = candidates.id
        WHERE trainees.id = %s
    ''', (trainee_id,))
    trainee = cursor.fetchone()
    cursor.execute('SELECT * FROM onboarding_forms WHERE active = 1 ORDER BY sort_order, created_date')
    forms = cursor.fetchall()
    cursor.execute('SELECT * FROM onboarding_signatures WHERE trainee_id = %s', (trainee_id,))
    sigs = {s['form_id']: s for s in cursor.fetchall()}
    conn.close()

    total  = len(forms)
    signed = sum(1 for f in forms if f['id'] in sigs)
    pct    = int((signed / total * 100)) if total else 0
    name   = trainee['first_name'] if trainee else 'Team Member'

    return render_template(
        'trainee_onboarding.html',
        trainee=trainee,
        forms=forms,
        sigs=sigs,
        signed=signed,
        total=total,
        pct=pct,
        name=name
    )

@app.route('/onboarding/<int:form_id>/sign', methods=['GET', 'POST'])
@trainee_required
def sign_onboarding_form(form_id):
    trainee_id = session.get('trainee_id')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM onboarding_forms WHERE id = %s AND active = 1', (form_id,))
    form = cursor.fetchone()
    if not form:
        conn.close()
        return redirect('/onboarding')

    cursor.execute('''
        SELECT trainees.*, candidates.first_name, candidates.last_name
        FROM trainees LEFT JOIN candidates ON trainees.candidate_id = candidates.id
        WHERE trainees.id = %s
    ''', (trainee_id,))
    trainee = cursor.fetchone()

    cursor.execute('SELECT * FROM onboarding_signatures WHERE trainee_id = %s AND form_id = %s',
                   (trainee_id, form_id))
    existing_sig = cursor.fetchone()

    if request.method == 'POST':
        signed_name = request.form.get('signed_name', '').strip()
        ip = request.remote_addr
        if not signed_name:
            conn.close()
            return redirect(f'/onboarding/{form_id}/sign')
        if existing_sig:
            cursor.execute('''UPDATE onboarding_signatures
                              SET signed_name=%s, signed_date=NOW(), ip_address=%s
                              WHERE id=%s''',
                           (signed_name, ip, existing_sig['id']))
        else:
            cursor.execute('''INSERT INTO onboarding_signatures
                              (trainee_id, form_id, signed_name, ip_address)
                              VALUES (%s, %s, %s, %s)''',
                           (trainee_id, form_id, signed_name, ip))
        conn.commit()
        conn.close()
        return redirect('/onboarding')

    conn.close()
    full_name = f'{trainee["first_name"]} {trainee["last_name"]}' if trainee else ''
    return render_template('sign_onboarding_form.html', form=form, full_name=full_name, existing_sig=existing_sig)

@app.route('/onboarding-file-trainee/<filename>')
@trainee_required
def view_onboarding_file_trainee(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ============ CRM MODULE ============

def init_crm_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            phone VARCHAR(50),
            email VARCHAR(255),
            address TEXT,
            service_type VARCHAR(100),
            status VARCHAR(20) DEFAULT 'new',
            notes TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    ''')
    try:
        cursor.execute('SELECT source FROM leads LIMIT 1')
    except Exception:
        try:
            cursor.execute('ALTER TABLE leads ADD COLUMN source VARCHAR(100)')
        except Exception:
            pass
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS quote_events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event VARCHAR(20),
            source VARCHAR(100),
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    except Exception:
        pass
    conn.commit()
    conn.close()

try:
    init_crm_db()
except Exception as e:
    print(f"CRM DB init warning: {e}")


SERVICE_TYPES = [
    'Regular House Cleaning',
    'Deep Cleaning',
    'Move-In Cleaning',
    'Move-Out Cleaning',
    'Office / Commercial Cleaning',
    'Short-Term Rental / Airbnb Turnover',
    'Post-Construction Cleaning',
    'Other',
]

STATUS_LABELS = {
    'new': ('New', '#3498db'),
    'in_progress': ('In Progress', '#f39c12'),
    'done': ('Done', '#27ae60'),
}


def status_badge(status):
    label, color = STATUS_LABELS.get(status, ('Unknown', '#95a5a6'))
    return f'<span style="background:{color};color:white;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:bold;">{label}</span>'


def _source_funnel_html():
    """Views vs leads per source, so you can see which ads actually work."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS quote_events (id INT AUTO_INCREMENT PRIMARY KEY, event VARCHAR(20), source VARCHAR(100), created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.commit()
        cur.execute("SELECT source, event, COUNT(*) AS n FROM quote_events GROUP BY source, event")
        rows = cur.fetchall()
        conn.close()
    except Exception:
        return ''

    if not rows:
        return ('<div class="application"><h3>Lead Sources</h3>'
                '<p class="form-note">No quote traffic recorded yet. Add '
                '<code>?utm_source=facebook</code> to your ad links to start tracking.</p></div>')

    data = {}
    for r in rows:
        s = r['source'] or 'unknown'
        data.setdefault(s, {'view': 0, 'lead': 0})
        data[s][r['event']] = r['n']

    body = ''
    for s in sorted(data, key=lambda k: -data[k]['view']):
        v = data[s]['view']
        l = data[s]['lead']
        rate = ('%d%%' % round(l * 100.0 / v)) if v else '-'
        body += ('<tr><td>%s</td><td>%d</td><td>%d</td><td><strong>%s</strong></td></tr>'
                 % (s, v, l, rate))

    return ('<div class="application"><h3>Lead Sources</h3>'
            '<table style="width:100%;border-collapse:collapse;" border="1" cellpadding="6">'
            '<tr><th align="left">Source</th><th align="left">Quote views</th>'
            '<th align="left">Leads</th><th align="left">Convert</th></tr>'
            + body + '</table>'
            '<p class="form-note">Tag your ads: caseyscleaning.net/quote?utm_source=facebook</p></div>')


@app.route('/crm')
@login_required
def crm_list():
    status_filter = request.args.get('status', 'all')
    conn = get_db()
    cursor = conn.cursor()
    if status_filter != 'all':
        cursor.execute('SELECT * FROM leads WHERE status = %s ORDER BY created_date DESC', (status_filter,))
    else:
        cursor.execute('SELECT * FROM leads ORDER BY created_date DESC')
    leads = cursor.fetchall()
    cursor.execute('SELECT status, COUNT(*) as cnt FROM leads GROUP BY status')
    counts = {row['status']: row['cnt'] for row in cursor.fetchall()}
    total = sum(counts.values())
    conn.close()

    new_count = counts.get('new', 0)
    inprog_count = counts.get('in_progress', 0)
    done_count = counts.get('done', 0)

    filter_links = f'''
    <div style="margin-bottom:15px;">
        <a href="/crm" style="margin-right:10px;color:#3498db;font-weight:bold;">All ({total})</a>
        <a href="/crm?status=new" style="margin-right:10px;color:#3498db;">New ({new_count})</a>
        <a href="/crm?status=in_progress" style="margin-right:10px;color:#f39c12;">In Progress ({inprog_count})</a>
        <a href="/crm?status=done" style="color:#27ae60;">Done ({done_count})</a>
    </div>
    '''

    html = STYLE + admin_nav() + '<h1>CRM - Leads</h1>'
    html += filter_links
    html += '<p><a class="btn btn-success" href="/crm/new">+ Add Lead</a></p>'
    html += _source_funnel_html()

    if not leads:
        html += '<div class="info"><p>No leads yet. Add one manually or share your quote request link with customers: <strong>/quote</strong></p></div>'
    else:
        for lead in leads:
            # Extract photo URLs from notes (format: "... | Photos: url1, url2")
            notes_raw = lead['notes'] or ''
            photo_urls = []
            notes_clean = notes_raw
            if '| Photos:' in notes_raw:
                parts = notes_raw.split('| Photos:', 1)
                notes_clean = parts[0].strip().rstrip('|').strip()
                photo_urls = [u.strip() for u in parts[1].strip().split(',') if u.strip()]

            photo_html = ''
            if photo_urls:
                photo_html = '<div style="margin:8px 0;">'
                photo_html += '<p style="margin:0 0 6px 0;font-size:13px;font-weight:600;">Quote Photos:</p>'
                for url in photo_urls:
                    photo_html += (
                        f'<a href="{url}" target="_blank" rel="noopener">'
                        f'<img src="{url}" style="width:120px;height:90px;object-fit:cover;'
                        f'border-radius:6px;border:2px solid #D4A843;margin-right:8px;'
                        f'margin-bottom:4px;cursor:pointer;" title="Click to view full size">'
                        f'</a>'
                    )
                photo_html += '</div>'

            notes_html = f'<p><strong>Notes:</strong> {notes_clean}</p>' if notes_clean else ''

            _src = None
            try:
                _src = lead["source"]
            except Exception:
                _src = None
            if _src:
                _sc = {'facebook': '#3b5998', 'instagram': '#c13584', 'google': '#0f9d58',
                       'nextdoor': '#8ed500', 'direct': '#6b6259'}.get(str(_src).split('_')[0].lower(), '#b5651d')
                source_badge = f'<span style="background:{_sc};color:#fff;padding:2px 9px;border-radius:10px;font-size:11px;font-weight:600;margin-left:6px;">{_src}</span>'
            else:
                source_badge = ''

            html += f'''
            <div class="application">
                <h2>{lead["first_name"]} {lead["last_name"]} {status_badge(lead["status"])} {source_badge}</h2>
                <p><strong>Service:</strong> {lead["service_type"] or "Not specified"} &nbsp;|&nbsp;
                   <strong>Phone:</strong> {lead["phone"] or "N/A"} &nbsp;|&nbsp;
                   <strong>Email:</strong> {lead["email"] or "N/A"}</p>
                <p><strong>Address:</strong> {lead["address"] or "Not provided"}</p>
                {notes_html}
                {photo_html}
                <p class="form-note">Added: {str(lead["created_date"])[:10]}</p>
                <a class="btn" href="/crm/{lead["id"]}/edit">Edit / Update</a>
                <form method="POST" action="/leads/{lead["id"]}/convert" onsubmit="return confirm('Convert this lead to a customer?');" style="display:inline-block;margin-top:10px;margin-right:8px;box-shadow:none;padding:0;background:none;">
                    <button class="btn" type="submit" style="background:#28a745;color:#fff;border-color:#28a745;">Convert to Customer</button>
                </form>
                <form method="POST" action="/crm/{lead["id"]}/delete" onsubmit="return confirm('Delete this lead?');"
                      style="display:inline-block;margin-top:10px;box-shadow:none;padding:0;background:none;">
                    <button class="btn btn-danger" type="submit">Delete</button>
                </form>
            </div>
            '''
    return html


def get_marketing_sources_options(selected_id=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM marketing_sources ORDER BY name')
    sources = cursor.fetchall()
    conn.close()
    selected_id = str(selected_id) if selected_id else ''
    options = '<option value="">-- Not specified --</option>'
    for s in sources:
        sel = 'selected' if str(s['id']) == selected_id else ''
        options += f'<option value="{s["id"]}" {sel}>{s["name"]}</option>'
    return options


@app.route('/crm/new', methods=['GET', 'POST'])
@login_required
def crm_new():
    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO leads
                          (first_name, last_name, phone, email, address, service_type, status, notes, lead_source_id)
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                       (request.form['first_name'], request.form['last_name'],
                        request.form.get('phone', ''), request.form.get('email', ''),
                        request.form.get('address', ''), request.form.get('service_type', ''),
                        request.form.get('status', 'new'), request.form.get('notes', ''),
                        request.form.get('lead_source_id') or None))
        conn.commit()
        conn.close()
        return redirect('/crm')

    service_options = ''.join(f'<option value="{s}">{s}</option>' for s in SERVICE_TYPES)
    lead_source_options = get_marketing_sources_options()
    return STYLE + admin_nav() + f'''
    <h1>Add New Lead</h1>
    <form method="POST">
        <label>First Name:</label>
        <input type="text" name="first_name" required>
        <label>Last Name:</label>
        <input type="text" name="last_name" required>
        <label>Phone:</label>
        <input type="tel" name="phone">
        <label>Email:</label>
        <input type="email" name="email">
        <label>Address:</label>
        <input type="text" name="address" placeholder="Street, City, State">
        <label>Lead Source (how did they hear about us?):</label>
        <select name="lead_source_id">{lead_source_options}</select>
        <label>Service Type:</label>
        <select name="service_type">
            <option value="">-- Select service --</option>
            {service_options}
        </select>
        <label>Status:</label>
        <select name="status">
            <option value="new">New</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
        </select>
        <label>Notes:</label>
        <textarea name="notes" rows="3" placeholder="Any notes about this lead..."></textarea>
        <button class="btn btn-success" type="submit">Save Lead</button>
        <a class="btn" href="/crm" style="background:#95a5a6;">Cancel</a>
    </form>
    '''


@app.route('/crm/<int:lead_id>/edit', methods=['GET', 'POST'])
@login_required
def crm_edit(lead_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM leads WHERE id = %s', (lead_id,))
    lead = cursor.fetchone()
    if not lead:
        conn.close()
        return redirect('/crm')

    if request.method == 'POST':
        cursor.execute('''UPDATE leads SET first_name=%s, last_name=%s, phone=%s, email=%s,
                          address=%s, service_type=%s, status=%s, notes=%s, lead_source_id=%s WHERE id=%s''',
                       (request.form['first_name'], request.form['last_name'],
                        request.form.get('phone', ''), request.form.get('email', ''),
                        request.form.get('address', ''), request.form.get('service_type', ''),
                        request.form.get('status', 'new'), request.form.get('notes', ''),
                        request.form.get('lead_source_id') or None, lead_id))
        conn.commit()
        conn.close()
        return redirect('/crm')

    conn.close()
    service_options = ''
    for s in SERVICE_TYPES:
        sel = 'selected' if lead['service_type'] == s else ''
        service_options += f'<option value="{s}" {sel}>{s}</option>'
    status_options = ''
    for val, (label, color) in STATUS_LABELS.items():
        sel = 'selected' if lead['status'] == val else ''
        status_options += f'<option value="{val}" {sel}>{label}</option>'
    lead_source_options = get_marketing_sources_options(lead.get('lead_source_id'))

    return STYLE + admin_nav() + f'''
    <h1>Edit Lead: {lead["first_name"]} {lead["last_name"]}</h1>
    <form method="POST">
        <label>First Name:</label>
        <input type="text" name="first_name" required value="{lead['first_name']}">
        <label>Last Name:</label>
        <input type="text" name="last_name" required value="{lead['last_name']}">
        <label>Phone:</label>
        <input type="tel" name="phone" value="{lead['phone'] or ''}">
        <label>Email:</label>
        <input type="email" name="email" value="{lead['email'] or ''}">
        <label>Address:</label>
        <input type="text" name="address" value="{lead['address'] or ''}">
        <label>Lead Source:</label>
        <select name="lead_source_id">{lead_source_options}</select>
        <label>Service Type:</label>
        <select name="service_type">
            <option value="">-- Select service --</option>
            {service_options}
        </select>
        <label>Status:</label>
        <select name="status">{status_options}</select>
        <label>Notes:</label>
        <textarea name="notes" rows="3">{lead['notes'] or ''}</textarea>
        <button class="btn btn-success" type="submit">Save Changes</button>
        <a class="btn" href="/crm" style="background:#95a5a6;">Cancel</a>
    </form>
    '''


@app.route('/crm/<int:lead_id>/delete', methods=['POST'])
@login_required
def crm_delete(lead_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM leads WHERE id = %s', (lead_id,))
    conn.commit()
    conn.close()
    return redirect('/crm')


QUOTE_BASE = 70.0
QUOTE_PER_BED = 25.0
QUOTE_PER_BATH = 35.0
QUOTE_PER_SQFT = 0.015
QUOTE_MIN = 150.0

QUOTE_TYPE_MULT = {
    'standard': 1.00,
    'deep': 1.43,
    'moveout': 1.60,
    'airbnb': 1.00,
}
QUOTE_FREQ_MULT = {
    'weekly': 0.88,
    'biweekly': 0.94,
    'monthly': 0.97,
    'onetime': 1.25,
}
QUOTE_TYPE_LABEL = {
    'standard': 'Standard Clean',
    'deep': 'Deep Clean',
    'moveout': 'Move-Out Clean',
    'airbnb': 'Airbnb Turnover',
}
QUOTE_FREQ_LABEL = {
    'weekly': 'Weekly',
    'biweekly': 'Every 2 weeks',
    'monthly': 'Monthly',
    'onetime': 'One-time only',
}


def compute_quote(cleaning_type, bedrooms, bathrooms, sqft, frequency):
    """Return (price, label) for a quote configuration."""
    try:
        bedrooms = max(0, min(10, int(bedrooms)))
    except (TypeError, ValueError):
        bedrooms = 3
    try:
        bathrooms = max(0, min(10, int(bathrooms)))
    except (TypeError, ValueError):
        bathrooms = 2
    try:
        sqft = max(0, min(20000, int(sqft)))
    except (TypeError, ValueError):
        sqft = 2000

    ctype = cleaning_type if cleaning_type in QUOTE_TYPE_MULT else 'standard'
    freq = frequency if frequency in QUOTE_FREQ_MULT else 'onetime'

    base = (QUOTE_BASE
            + QUOTE_PER_BED * bedrooms
            + QUOTE_PER_BATH * bathrooms
            + QUOTE_PER_SQFT * sqft)
    price = base * QUOTE_TYPE_MULT[ctype]

    # deep and move-out cleans are inherently one-off; no frequency discount
    if ctype in ('standard', 'airbnb'):
        price = price * QUOTE_FREQ_MULT[freq]

    if price < QUOTE_MIN:
        price = QUOTE_MIN
    return int(round(price)), QUOTE_TYPE_LABEL[ctype]


def detect_source():
    """Where did this visitor come from? utm_source wins, then referrer."""
    try:
        utm = (request.args.get('utm_source') or '').strip().lower()
        if utm:
            return utm[:100]
        ref = (request.referrer or '').lower()
        if not ref:
            return 'direct'
        for name in ('facebook', 'instagram', 'google', 'bing', 'nextdoor',
                     'yelp', 'youtube', 'tiktok', 'twitter', 'linkedin'):
            if name in ref:
                return name
        if 'caseyscleaning' in ref:
            return 'direct'
        return ref.split('/')[2][:100] if '//' in ref else 'other'
    except Exception:
        return 'unknown'


def log_quote_event(event, source):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS quote_events (id INT AUTO_INCREMENT PRIMARY KEY, event VARCHAR(20), source VARCHAR(100), created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("INSERT INTO quote_events (event, source) VALUES (%s, %s)", (event, source))
        conn.commit()
        conn.close()
    except Exception:
        pass


def send_quote_emails(customer_email, customer_name, price, type_label,
                      freq_label, bedrooms, bathrooms, sqft, address, phone, source):
    """Send a lead alert to the owner and the quote to the customer.
    Never raises: any failure is swallowed so the lead/price flow is unaffected."""
    import os, smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    api_key = os.environ.get('RESEND_API_KEY')
    owner_email = os.environ.get('GMAIL_USER') or os.environ.get('OWNER_EMAIL')
    from_addr = os.environ.get('MAIL_FROM', 'quotes@caseyscleaning.net')
    if not api_key or not owner_email:
        return False
    try:
        biz = "Casey's Cleaning"
        owner = MIMEMultipart('alternative')
        owner['Subject'] = "New quote lead: %s ($%s)" % (customer_name, price)
        owner['From'] = "Casey's Cleaning <%s>" % from_addr
        owner['To'] = owner_email
        owner.attach(MIMEText(
            "New quote request via %s\n\nName: %s\nEmail: %s\nPhone: %s\n"
            "Address: %s\n\n%s | %s | %s bed / %s bath / %s sqft\n"
            "Estimate sent to customer: $%s\n" % (
                source, customer_name, customer_email, phone or '(not given)',
                address or '(not given)', type_label, freq_label,
                bedrooms, bathrooms, sqft, price), 'plain'))
        cust = MIMEMultipart('alternative')
        cust['Subject'] = "Your free quote from %s" % biz
        cust['From'] = "%s <%s>" % (biz, from_addr)
        cust['To'] = customer_email
        cust['Reply-To'] = owner_email
        cust.attach(MIMEText(
            "Hi %s,\n\nThanks for reaching out to Casey's Cleaning! "
            "Based on what you told us, your estimated price is:\n\n"
            "    $%s  (%s, %s)\n\n"
            "This is an estimate. We'll confirm the final price after a quick "
            "walkthrough, so you only pay for what your home actually needs.\n\n"
            "We'll be in touch shortly to schedule. Reply to this email anytime.\n\n"
            "Casey's Cleaning of Las Vegas\n(702) 506-8918\n" % (
                customer_name, price, type_label, freq_label), 'plain'))
        server = smtplib.SMTP('smtp.resend.com', 587, timeout=15)
        server.starttls()
        server.login('resend', api_key)
        server.sendmail(from_addr, [owner_email], owner.as_string())
        server.sendmail(from_addr, [customer_email], cust.as_string())
        server.quit()
        return True
    except Exception as e:
        import traceback
        print("QUOTE EMAIL FAILED:", repr(e), flush=True)
        traceback.print_exc()
        return False


@app.route('/quote/price', methods=['POST'])
def quote_price():
    """Capture the lead, then return their price."""
    import json as _json
    first_name = (request.form.get('first_name') or '').strip()
    last_name = (request.form.get('last_name') or '').strip()
    phone = (request.form.get('phone') or '').strip()
    email = (request.form.get('email') or '').strip()
    address = (request.form.get('address') or '').strip()
    notes = (request.form.get('notes') or '').strip()

    cleaning_type = request.form.get('cleaning_type', 'standard')
    frequency = request.form.get('frequency', 'onetime')
    bedrooms = request.form.get('bedrooms', '3')
    bathrooms = request.form.get('bathrooms', '2')
    sqft = request.form.get('sqft', '2000')
    source = (request.form.get('source') or 'unknown').strip()[:100]

    if not first_name or not email:
        return {'ok': False, 'error': 'Name and email are required.'}, 400

    price, type_label = compute_quote(cleaning_type, bedrooms, bathrooms, sqft, frequency)
    freq_label = QUOTE_FREQ_LABEL.get(frequency, 'One-time only')

    full_notes = "[Quote] %s | %s | Beds: %s | Baths: %s | SqFt: %s | Estimate: $%s" % (
        type_label, freq_label, bedrooms, bathrooms, sqft, price)
    if address:
        full_notes += " | Address: " + address
    if notes:
        full_notes += " | Notes: " + notes

    try:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO leads (first_name, last_name, phone, email, address, service_type, status, notes, source) VALUES (%s,%s,%s,%s,%s,%s,'new',%s,%s)",
                (first_name, last_name, phone, email, address, cleaning_type, full_notes, source))
        except Exception:
            cursor.execute(
                "INSERT INTO leads (first_name, last_name, phone, email, address, service_type, status, notes) VALUES (%s,%s,%s,%s,%s,%s,'new',%s)",
                (first_name, last_name, phone, email, address, cleaning_type, full_notes))
        conn.commit()
        conn.close()
    except Exception as _e:
        import traceback
        print("LEAD INSERT FAILED:", repr(_e), flush=True)
        traceback.print_exc()

    log_quote_event('lead', source)

    try:

        send_quote_emails(email, first_name, price, type_label,

                          freq_label, bedrooms, bathrooms, sqft,

                          address, phone, source)

    except Exception:

        pass

    return {'ok': True, 'price': price, 'type_label': type_label,
            'freq_label': freq_label, 'name': first_name}


@app.route('/quote', methods=['GET', 'POST'])
def quote_request():
    if request.method == 'POST':
        first_name    = request.form.get('first_name', '').strip()
        last_name     = request.form.get('last_name', '').strip()
        phone         = request.form.get('phone', '').strip()
        email         = request.form.get('email', '').strip()
        address       = request.form.get('address', '').strip()
        notes         = request.form.get('notes', '').strip()
        cleaning_type = request.form.get('cleaning_type', 'standard')
        bedrooms      = request.form.get('bedrooms', '3')
        bathrooms     = request.form.get('bathrooms', '2')
        sqft        = request.form.get('sqft', '')
        estimate      = request.form.get('estimate', '0')

        photo_urls = []
        for i in range(1, 4):
            pf = request.files.get(f'photo_{i}')
            if pf and pf.filename:
                try:
                    res = cloudinary.uploader.upload(pf, resource_type='image',
                                                      folder='imhotep_quote_photos',
                                                      use_filename=True, unique_filename=True,
                                                      access_mode='public', type='upload')
                    photo_urls.append(res.get('secure_url', ''))
                except Exception:
                    pass

        full_notes = f"[Quote] Type: {cleaning_type.upper()} | Beds: {bedrooms} | Baths: {bathrooms} | SqFt: {sqft} | Estimate: ${estimate}"
        if notes:
            full_notes += f" | Notes: {notes}"
        if address:
            full_notes += f" | Address: {address}"
        if photo_urls:
            full_notes += " | Photos: " + ", ".join(photo_urls)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO leads
            (first_name, last_name, phone, email, address, service_type, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, 'new', %s)''',
            (first_name, last_name, phone, email, address, cleaning_type, full_notes))
        conn.commit()
        conn.close()

        return render_template('quote_thanks.html', name=first_name, estimate=estimate)

    # --- count quote-page visits (Request a Quote clicks) ---
    try:
        _c = get_db()
        _cur = _c.cursor()
        _cur.execute("CREATE TABLE IF NOT EXISTS page_counters (name VARCHAR(64) PRIMARY KEY, count INT NOT NULL DEFAULT 0)")
        _cur.execute("INSERT INTO page_counters (name, count) VALUES ('quote_views', 1) ON DUPLICATE KEY UPDATE count = count + 1")
        _c.commit()
        _c.close()
    except Exception:
        pass

    source = detect_source()
    log_quote_event('view', source)
    return render_quote_page(source)


def render_quote_page(source):
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Get Your Free Quote &mdash; Casey's Cleaning</title>
<style>
 *{box-sizing:border-box;}
 body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
      background:#faf7f4;color:#2f2a26;}
 .topnav{background:#5a3d26;padding:12px 20px;display:flex;align-items:center;
      justify-content:space-between;flex-wrap:wrap;gap:8px;}
 .topnav .brand{color:#fff;font-weight:700;font-size:18px;text-decoration:none;}
 .topnav .brand span{color:#e8b84b;}
 .topnav .navlinks a{color:#f0e6dc;text-decoration:none;font-size:14px;margin-left:18px;}
 .topnav .navlinks a:hover{color:#fff;text-decoration:underline;}
 .backlink{text-align:center;margin-top:18px;}
 .backlink a{color:#8a7f76;font-size:14px;text-decoration:none;}
 .backlink a:hover{color:#b5651d;text-decoration:underline;}
 .hero{background:#6b4a2f;color:#fff;padding:38px 20px 30px;text-align:center;}
 .hero h1{margin:0 0 8px;font-size:28px;}
 .hero p{margin:0;opacity:.9;font-size:15px;}
 .wrap{max-width:640px;margin:-18px auto 40px;padding:0 16px;}
 .card{background:#fff;border:1px solid #e8e0d8;border-radius:12px;
       padding:20px;margin-bottom:16px;}
 .card h2{margin:0 0 4px;font-size:17px;}
 .card .sub{margin:0 0 14px;color:#8a7f76;font-size:13px;}
 .opts{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;}
 .opt{border:2px solid #e8e0d8;border-radius:10px;padding:12px;text-align:center;
      cursor:pointer;background:#fff;transition:.15s;}
 .opt:hover{border-color:#c9a227;}
 .opt.sel{border-color:#b5651d;background:#fdf6ee;}
 .opt b{display:block;font-size:14px;margin-bottom:2px;}
 .opt span{font-size:12px;color:#8a7f76;}
 .row{display:flex;align-items:center;gap:12px;margin-bottom:14px;}
 .row label{flex:0 0 120px;font-size:14px;color:#6b6259;}
 .row input[type=range]{flex:1;}
 .val{flex:0 0 62px;text-align:right;font-weight:600;font-size:14px;}
 .fld{margin-bottom:12px;}
 .fld label{display:block;font-size:13px;color:#6b6259;margin-bottom:4px;}
 .fld input,.fld textarea{width:100%;padding:11px;border:1px solid #d8cfc5;
      border-radius:8px;font-size:15px;font-family:inherit;}
 .two{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
 .btn{width:100%;background:#b5651d;color:#fff;border:0;border-radius:10px;
      padding:15px;font-size:16px;font-weight:600;cursor:pointer;}
 .btn:hover{background:#9c5518;}
 .btn:disabled{background:#c9bcb0;cursor:not-allowed;}
 .locked{text-align:center;padding:22px;background:#fdf6ee;border:2px dashed #e0cdb4;
      border-radius:10px;color:#8a7f76;font-size:14px;}
 .price{text-align:center;padding:8px 0 4px;}
 .price .amt{font-size:46px;font-weight:700;color:#b5651d;line-height:1;}
 .range{text-align:center;font-size:34px;font-weight:700;color:#6b4a2f;line-height:1.1;}
 .price .lbl{color:#8a7f76;font-size:14px;margin-top:6px;}
 .err{color:#b3261e;font-size:13px;margin-top:8px;display:none;}
 .note{font-size:12px;color:#9a8f85;text-align:center;margin-top:10px;}
 .hidden{display:none;}
</style></head><body>
<div class="topnav">
  <a class="brand" href="/">Casey's <span>Cleaning</span></a>
  <div class="navlinks">
    <a href="/">Home</a>
    <a href="/jobs">View Jobs</a>
  </div>
</div>
<div class="hero">
  <h1>Get Your Free Instant Quote</h1>
  <p>Tell us about your home &mdash; we&rsquo;ll email you a free quote.</p>
</div>
<div class="wrap">

  <div class="card">
    <h2>Type of cleaning</h2>
    <p class="sub">Pick what fits your needs</p>
    <div class="opts" id="types">
      <div class="opt sel" data-v="standard"><b>Standard</b><span>Regular upkeep</span></div>
      <div class="opt" data-v="deep"><b>Deep Clean</b><span>Top to bottom</span></div>
      <div class="opt" data-v="moveout"><b>Move-Out</b><span>Ready for new</span></div>
      <div class="opt" data-v="airbnb"><b>Airbnb</b><span>Rental turnover</span></div>
    </div>
  </div>

  <div class="card" id="freqcard">
    <h2>How often?</h2>
    <p class="sub">Recurring service saves you money</p>
    <div class="opts" id="freqs">
      <div class="opt" data-v="weekly"><b>Weekly</b><span>Best value</span></div>
      <div class="opt sel" data-v="biweekly"><b>Every 2 weeks</b><span>Most popular</span></div>
      <div class="opt" data-v="monthly"><b>Monthly</b><span>Light upkeep</span></div>
      <div class="opt" data-v="onetime"><b>One-time</b><span>Just once</span></div>
    </div>
  </div>

  <div class="card">
    <h2>Home size</h2>
    <p class="sub">Adjust to match your home</p>
    <div class="row"><label>Bedrooms</label>
      <input type="range" id="bed" min="0" max="7" step="1" value="3">
      <div class="val" id="bedv">3</div></div>
    <div class="row"><label>Bathrooms</label>
      <input type="range" id="bath" min="1" max="6" step="1" value="2">
      <div class="val" id="bathv">2</div></div>
    <div class="row"><label>Square feet</label>
      <input type="range" id="sqft" min="500" max="6000" step="100" value="2000">
      <div class="val" id="sqftv">2000</div></div>
  </div>

  <div class="card hidden" id="rangecard">
    <p class="sub" style="text-align:center;margin:0 0 6px;">Your estimated price</p>
    <div class="range" id="range">$210 &ndash; $250</div>
    <p class="note" id="rangenote">Estimate updates as you adjust your home above.</p>
  </div>

  <div class="card" id="gate">
    <h2>You&rsquo;re all set &mdash; nice work!</h2>
    <p class="sub">Just pop in your email and your free quote is on its way. No cost, no obligation.</p>
    <div class="two">
      <div class="fld"><label>First name *</label><input id="fn" required></div>
      <div class="fld"><label>Email *</label><input id="em" type="email" required></div>
    </div>
    <!-- kept in the DOM so the JS still works; submitted empty -->
    <div class="fld hidden"><label>Last name</label><input id="ln"></div>
    <div class="fld hidden"><label>Phone</label><input id="ph" type="tel"></div>
    <div class="fld"><label>Address (optional)</label><input id="ad"></div>
    <button class="btn" id="go">Email Me My Free Quote</button>
    <div class="err" id="err"></div>
    <p class="note">No obligation. We'll never share your information.</p>
  </div>

  <div class="card hidden" id="result">
    <div class="price hidden">
      <div class="amt" id="amt">$0</div>
      <div class="lbl" id="lbl"></div>
    </div>
    <p class="note" id="thanks"></p>
  </div>

  <div class="backlink"><a href="/">&larr; Back to Casey's Cleaning</a></div>

</div>
<script>
var SOURCE = "__SOURCE__";
var state = {type:'standard', freq:'biweekly'};

function pick(boxId, key){
  var box = document.getElementById(boxId);
  box.addEventListener('click', function(e){
    var t = e.target.closest('.opt');
    if(!t) return;
    box.querySelectorAll('.opt').forEach(function(o){o.classList.remove('sel');});
    t.classList.add('sel');
    state[key] = t.getAttribute('data-v');
    toggleFreq();
    estimate();
  });
}
pick('types','type');
pick('freqs','freq');

function toggleFreq(){
  var fc = document.getElementById('freqcard');
  if(state.type === 'deep' || state.type === 'moveout'){ fc.classList.add('hidden'); }
  else { fc.classList.remove('hidden'); }
}
toggleFreq();

var TYPE_MULT = {standard:1.00, deep:1.43, moveout:1.60, airbnb:1.00};
var FREQ_MULT = {weekly:0.88, biweekly:0.94, monthly:0.97, onetime:1.25};

function estimate(){
  var bed  = +document.getElementById('bed').value;
  var bath = +document.getElementById('bath').value;
  var sqft = +document.getElementById('sqft').value;
  var p = 70 + 25*bed + 35*bath + 0.015*sqft;
  p = p * (TYPE_MULT[state.type] || 1);
  if(state.type === 'standard' || state.type === 'airbnb'){
    p = p * (FREQ_MULT[state.freq] || 1);
  }
  if(p < 150) p = 150;
  var lo = Math.floor((p * 0.92) / 5) * 5;
  var hi = Math.ceil((p * 1.09) / 5) * 5;
  document.getElementById('range').innerHTML = '$' + lo + ' &ndash; $' + hi;
}

['bed','bath','sqft'].forEach(function(id){
  var el = document.getElementById(id);
  el.addEventListener('input', function(){
    document.getElementById(id+'v').textContent = el.value;
    estimate();
  });
});

estimate();

document.getElementById('go').addEventListener('click', function(){
  var fn = document.getElementById('fn').value.trim();
  var ph = document.getElementById('ph').value.trim();
  var em = document.getElementById('em').value.trim();
  var err = document.getElementById('err');
  if(!fn || !em){
    err.textContent = 'Please enter your name and email.';
    err.style.display = 'block';
    return;
  }
  err.style.display = 'none';
  var btn = this;
  btn.disabled = true; btn.textContent = 'Sending your quote...';

  var d = new FormData();
  d.append('first_name', fn);
  d.append('last_name', document.getElementById('ln').value.trim());
  d.append('phone', ph);
  d.append('email', em);
  d.append('address', document.getElementById('ad').value.trim());
  d.append('cleaning_type', state.type);
  d.append('frequency', state.freq);
  d.append('bedrooms', document.getElementById('bed').value);
  d.append('bathrooms', document.getElementById('bath').value);
  d.append('sqft', document.getElementById('sqft').value);
  d.append('source', SOURCE);

  fetch('/quote/price', {method:'POST', body:d})
    .then(function(r){ return r.json(); })
    .then(function(j){
      if(!j.ok){ throw new Error(j.error || 'error'); }
      document.getElementById('gate').classList.add('hidden');
      document.getElementById('rangecard').classList.add('hidden');
      var res = document.getElementById('result');
      res.classList.remove('hidden');
      document.getElementById('amt').textContent = '$' + j.price;
      var lbl = j.type_label;
      if(state.type === 'standard' || state.type === 'airbnb'){ lbl += ' \u00b7 ' + j.freq_label; }
      document.getElementById('lbl').textContent = lbl;
      document.getElementById('thanks').textContent =
        'Thanks ' + j.name + '! Your free quote is on its way to your inbox. We\\'ll confirm the final price after a quick walkthrough, so you only pay for what your home actually needs.';
      res.scrollIntoView({behavior:'smooth'});
    })
    .catch(function(){
      btn.disabled = false; btn.textContent = 'Email Me My Free Quote';
      err.textContent = 'Something went wrong. Please call us at (702) 506-8918.';
      err.style.display = 'block';
    });
});
</script>
</body></html>""".replace("__SOURCE__", source)


@app.route('/customers')
@login_required
def customers_list():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM customers ORDER BY created_date DESC')
    customers = cursor.fetchall()
    conn.close()

    html = STYLE + admin_nav() + '<h1>Customers</h1>'
    html += '<p><a class="btn btn-success" href="/customers/new">+ Add Customer</a></p>'

    if not customers:
        html += '<div class="info"><p>No customers yet. Add one manually to get started.</p></div>'
    else:
        for c in customers:
            active_label = 'Active' if c['active'] else 'Inactive'
            active_color = '#27ae60' if c['active'] else '#95a5a6'
            html += f'''
            <div class="application">
                <h2>{c["first_name"]} {c["last_name"]} <span style="font-size:13px;color:{active_color};">({active_label})</span></h2>
                <p><strong>Phone:</strong> {c["phone"] or "N/A"} &nbsp;|&nbsp;
                   <strong>Email:</strong> {c["email"] or "N/A"}</p>
                <p><strong>Address:</strong> {c["address"] or "Not provided"}</p>
                <p class="form-note">Added: {str(c["created_date"])[:10]}</p>
                <a class="btn" href="/customers/{c["id"]}/edit">Edit</a>
            </div>
            '''
    return html


@app.route('/customers/new', methods=['GET', 'POST'])
@login_required
def customers_new():
    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO customers
                          (first_name, last_name, phone, email, address, active, lead_source_id)
                          VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                       (request.form['first_name'], request.form['last_name'],
                        request.form.get('phone', ''), request.form.get('email', ''),
                        request.form.get('address', ''),
                        1 if request.form.get('active') == 'on' else 0,
                        request.form.get('lead_source_id') or None))
        conn.commit()
        conn.close()
        return redirect('/customers')

    lead_source_options = get_marketing_sources_options()
    return STYLE + admin_nav() + f'''
    <h1>Add New Customer</h1>
    <form method="POST">
        <label>First Name:</label>
        <input type="text" name="first_name" required>
        <label>Last Name:</label>
        <input type="text" name="last_name" required>
        <label>Phone:</label>
        <input type="tel" name="phone">
        <label>Email:</label>
        <input type="email" name="email">
        <label>Address:</label>
        <input type="text" name="address" placeholder="Street, City, State">
        <label>Lead Source:</label>
        <select name="lead_source_id">{lead_source_options}</select>
        <label><input type="checkbox" name="active" checked style="width:auto;display:inline-block;margin-right:6px;">Active customer</label>
        <button class="btn btn-success" type="submit">Save Customer</button>
        <a class="btn" href="/customers" style="background:#95a5a6;">Cancel</a>
    </form>
    '''


@app.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def customers_edit(customer_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM customers WHERE id = %s', (customer_id,))
    customer = cursor.fetchone()
    if not customer:
        conn.close()
        return redirect('/customers')

    if request.method == 'POST':
        cursor.execute('''UPDATE customers SET first_name=%s, last_name=%s, phone=%s,
                          email=%s, address=%s, active=%s, lead_source_id=%s WHERE id=%s''',
                       (request.form['first_name'], request.form['last_name'],
                        request.form.get('phone', ''), request.form.get('email', ''),
                        request.form.get('address', ''),
                        1 if request.form.get('active') == 'on' else 0,
                        request.form.get('lead_source_id') or None, customer_id))
        conn.commit()
        conn.close()
        return redirect('/customers')

    conn.close()
    checked = 'checked' if customer['active'] else ''
    lead_source_options = get_marketing_sources_options(customer.get('lead_source_id'))
    return STYLE + admin_nav() + f'''
    <h1>Edit Customer: {customer["first_name"]} {customer["last_name"]}</h1>
    <form method="POST">
        <label>First Name:</label>
        <input type="text" name="first_name" required value="{customer['first_name']}">
        <label>Last Name:</label>
        <input type="text" name="last_name" required value="{customer['last_name']}">
        <label>Phone:</label>
        <input type="tel" name="phone" value="{customer['phone'] or ''}">
        <label>Email:</label>
        <input type="email" name="email" value="{customer['email'] or ''}">
        <label>Address:</label>
        <input type="text" name="address" value="{customer['address'] or ''}">
        <label>Lead Source:</label>
        <select name="lead_source_id">{lead_source_options}</select>
        <label><input type="checkbox" name="active" {checked} style="width:auto;display:inline-block;margin-right:6px;">Active customer</label>
        <button class="btn btn-success" type="submit">Save Changes</button>
        <a class="btn" href="/customers" style="background:#95a5a6;">Cancel</a>
    </form>
    '''


JOB_STATUS_LABELS = {
    'pending_confirmation': ('Pending Confirmation', '#9b59b6'),
    'scheduled': ('Scheduled', '#3498db'),
    'in_progress': ('In Progress', '#f39c12'),
    'completed': ('Completed', '#27ae60'),
    'rescheduled': ('Rescheduled', '#e67e22'),
    'cancelled': ('Cancelled', '#c0392b'),
}

RECURRENCE_LABELS = {
    'one_time': 'One-Time',
    'weekly': 'Weekly',
    'biweekly': 'Biweekly',
    'monthly': 'Monthly',
}

def format_job_time(t):
    """pymysql returns TIME columns as datetime.timedelta, not a clock time --
    str(timedelta)[:5] breaks for any single-digit hour (e.g. 9:00 AM jobs)."""
    if not t:
        return ''
    total_seconds = int(t.total_seconds())
    hours = (total_seconds // 3600) % 24
    minutes = (total_seconds % 3600) // 60
    return f'{hours:02d}:{minutes:02d}'


CREW_ROLES = ['floor', 'bathroom', 'duster']


def job_status_badge(status):
    label, color = JOB_STATUS_LABELS.get(status, ('Unknown', '#95a5a6'))
    return f'<span style="background:{color};color:white;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:bold;">{label}</span>'


def get_crew_roster():
    """Real crew roster -- people who've actually been hired and trained,
    not candidates.status (which is set manually and not kept current)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT candidates.id, candidates.first_name, candidates.last_name
        FROM trainees
        JOIN candidates ON trainees.candidate_id = candidates.id
        ORDER BY candidates.first_name
    ''')
    roster = cursor.fetchall()
    conn.close()
    return roster


def crew_options(roster, selected_id):
    selected_id = str(selected_id) if selected_id else ''
    opts = '<option value="">-- none --</option>'
    for person in roster:
        sel = 'selected' if str(person['id']) == selected_id else ''
        opts += f'<option value="{person["id"]}" {sel}>{person["first_name"]} {person["last_name"]}</option>'
    return opts


def save_job_crew(cursor, job_id, form):
    cursor.execute('DELETE FROM cleaning_job_crew WHERE cleaning_job_id=%s', (job_id,))
    lead_role = form.get('lead_role', '')
    for role in CREW_ROLES:
        candidate_id = form.get(f'{role}_candidate_id', '')
        if candidate_id:
            is_lead = 1 if lead_role == role else 0
            cursor.execute(
                'INSERT INTO cleaning_job_crew (cleaning_job_id, candidate_id, role, is_lead) VALUES (%s, %s, %s, %s)',
                (job_id, candidate_id, role, is_lead)
            )


def next_recurrence_date(base_date, recurrence_rule):
    '''Given a job's date and its recurrence pattern, return the next occurrence's date.'''
    if recurrence_rule == 'weekly':
        return base_date + timedelta(days=7)
    elif recurrence_rule == 'biweekly':
        return base_date + timedelta(days=14)
    elif recurrence_rule == 'monthly':
        month = base_date.month + 1
        year = base_date.year
        if month > 12:
            month = 1
            year += 1
        day = min(base_date.day, calendar.monthrange(year, month)[1])
        return base_date.replace(year=year, month=month, day=day)
    return None


def create_next_occurrence(cursor, customer_id, scheduled_date_str, scheduled_time, service_type, recurrence_rule, price, form):
    '''Creates the next visit for a recurring job, in Pending Confirmation status,
    carrying forward the same crew -- nothing here books itself; it just waits
    until you've actually confirmed the date with the client.'''
    base_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()
    next_date = next_recurrence_date(base_date, recurrence_rule)
    if not next_date:
        return
    cursor.execute('''INSERT INTO cleaning_jobs
        (customer_id, scheduled_date, scheduled_time, service_type, status, recurrence_rule, price, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
        (customer_id, next_date, scheduled_time, service_type, 'pending_confirmation', recurrence_rule, price, ''))
    new_job_id = cursor.lastrowid
    save_job_crew(cursor, new_job_id, form)


def job_form_html(job, crew_by_role, lead_role, customers, roster, action_url, title, submit_label):
    customer_options = '<option value="">-- Select customer --</option>'
    for c in customers:
        sel = 'selected' if job and str(job['customer_id']) == str(c['id']) else ''
        customer_options += f'<option value="{c["id"]}" {sel}>{c["first_name"]} {c["last_name"]}</option>'

    service_options = '<option value="">-- Select service --</option>'
    for s in SERVICE_TYPES:
        sel = 'selected' if job and job['service_type'] == s else ''
        service_options += f'<option value="{s}" {sel}>{s}</option>'

    status_options = ''
    current_status = job['status'] if job else 'scheduled'
    for val, (label, color) in JOB_STATUS_LABELS.items():
        sel = 'selected' if current_status == val else ''
        status_options += f'<option value="{val}" {sel}>{label}</option>'

    recurrence_options = ''
    current_recurrence = job['recurrence_rule'] if job and job['recurrence_rule'] else 'one_time'
    for val, label in RECURRENCE_LABELS.items():
        sel = 'selected' if current_recurrence == val else ''
        recurrence_options += f'<option value="{val}" {sel}>{label}</option>'

    crew_rows = ''
    for role in CREW_ROLES:
        opts = crew_options(roster, crew_by_role.get(role))
        checked = 'checked' if lead_role == role else ''
        crew_rows += f'''
        <tr>
            <td style="padding:6px 10px;text-transform:capitalize;">{role}</td>
            <td style="padding:6px 10px;"><select name="{role}_candidate_id" style="margin:0;">{opts}</select></td>
            <td style="padding:6px 10px;"><input type="radio" name="lead_role" value="{role}" {checked} style="width:auto;"> Lead</td>
        </tr>
        '''

    scheduled_date = job['scheduled_date'] if job else ''
    scheduled_time = format_job_time(job['scheduled_time']) if job else ''
    price = job['price'] if job and job['price'] is not None else ''
    notes = job['notes'] if job and job['notes'] else ''

    return STYLE + admin_nav() + f'''
    <h1>{title}</h1>
    <form method="POST" action="{action_url}">
        <label>Customer:</label>
        <select name="customer_id" required>{customer_options}</select>
        <label>Date:</label>
        <input type="date" name="scheduled_date" required value="{scheduled_date}">
        <label>Time:</label>
        <input type="time" name="scheduled_time" value="{scheduled_time}">
        <label>Service Type:</label>
        <select name="service_type">{service_options}</select>
        <label>Status:</label>
        <select name="status">{status_options}</select>
        <label>Recurrence:</label>
        <select name="recurrence_rule">{recurrence_options}</select>
        <label>Price (reference only -- estimates come from QuickBooks):</label>
        <input type="number" name="price" step="0.01" value="{price}">
        <label>Crew:</label>
        <table style="margin-bottom:1rem;">{crew_rows}</table>
        <label>Notes:</label>
        <textarea name="notes" rows="3">{notes}</textarea>
        <button class="btn btn-success" type="submit">{submit_label}</button>
        <a class="btn" href="/schedule" style="background:#95a5a6;">Cancel</a>
    </form>
    '''


@app.route('/schedule')
@login_required
def schedule_list():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT cleaning_jobs.*, customers.first_name as cust_first, customers.last_name as cust_last
        FROM cleaning_jobs
        JOIN customers ON cleaning_jobs.customer_id = customers.id
        WHERE cleaning_jobs.status != 'pending_confirmation'
        ORDER BY cleaning_jobs.scheduled_date ASC, cleaning_jobs.scheduled_time ASC
    ''')
    jobs = cursor.fetchall()
    cursor.execute('''
        SELECT cleaning_job_crew.*, candidates.first_name, candidates.last_name
        FROM cleaning_job_crew
        JOIN candidates ON cleaning_job_crew.candidate_id = candidates.id
    ''')
    crew_rows = cursor.fetchall()
    conn.close()

    crew_by_job = {}
    for row in crew_rows:
        crew_by_job.setdefault(row['cleaning_job_id'], []).append(row)

    html = STYLE + admin_nav() + '<h1>Scheduling</h1>'
    html += '<p><a class="btn btn-success" href="/schedule/new">+ Schedule a Job</a> <a class="btn" href="/schedule/calendar" style="background:#8e44ad;">&#128197; Calendar</a> <a class="btn" href="/schedule/timesheets" style="background:#5C3D2E;">Timesheets</a></p>'

    if not jobs:
        html += '<div class="info"><p>No jobs scheduled yet. You\'ll need at least one customer first -- see <a href="/customers">Customers</a>.</p></div>'
    else:
        for job in jobs:
            crew = crew_by_job.get(job['id'], [])
            if crew:
                parts = []
                for c in crew:
                    role_label = c['role'].title() if c['role'] else 'Crew'
                    lead_tag = ' (Lead)' if c['is_lead'] else ''
                    parts.append(f"{c['first_name']} {c['last_name']} - {role_label}{lead_tag}")
                crew_html = '<p><strong>Crew:</strong> ' + ', '.join(parts) + '</p>'
            else:
                crew_html = '<p><strong>Crew:</strong> Not assigned yet</p>'

            time_str = format_job_time(job['scheduled_time'])
            html += f'''
            <div class="application">
                <h2>{job["cust_first"]} {job["cust_last"]} {job_status_badge(job["status"])}</h2>
                <p><strong>Date:</strong> {job["scheduled_date"]} {time_str} &nbsp;|&nbsp;
                   <strong>Service:</strong> {job["service_type"] or "Not specified"}</p>
                {crew_html}
                {f"<p><strong>Notes:</strong> {job['notes']}</p>" if job["notes"] else ""}
                <a class="btn" href="/schedule/{job["id"]}/edit">Edit</a>
                <a class="btn" href="/schedule/{job["id"]}/photos" style="background:#8e44ad;">Photos</a>
                <form method="POST" action="/schedule/{job["id"]}/delete" onsubmit="return confirm('Delete this job?');"
                      style="display:inline-block;margin-top:10px;box-shadow:none;padding:0;background:none;">
                    <button class="btn btn-danger" type="submit">Delete</button>
                </form>
            </div>
            '''
    return html


@app.route('/schedule/new', methods=['GET', 'POST'])
@login_required
def schedule_new():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        new_status = request.form.get('status', 'scheduled')
        recurrence_rule = request.form.get('recurrence_rule', 'one_time')
        cursor.execute('''INSERT INTO cleaning_jobs
            (customer_id, scheduled_date, scheduled_time, service_type, status, recurrence_rule, price, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
            (request.form['customer_id'], request.form['scheduled_date'],
             request.form.get('scheduled_time') or None, request.form.get('service_type', ''),
             new_status, recurrence_rule,
             request.form.get('price') or None, request.form.get('notes', '')))
        job_id = cursor.lastrowid
        save_job_crew(cursor, job_id, request.form)
        if new_status == 'completed' and recurrence_rule != 'one_time':
            create_next_occurrence(cursor, request.form['customer_id'], request.form['scheduled_date'],
                                    request.form.get('scheduled_time') or None, request.form.get('service_type', ''),
                                    recurrence_rule, request.form.get('price') or None, request.form)
        conn.commit()
        conn.close()
        return redirect('/schedule')

    cursor.execute('SELECT * FROM customers WHERE active=1 ORDER BY first_name')
    customers = cursor.fetchall()
    conn.close()
    roster = get_crew_roster()

    return job_form_html(None, {}, '', customers, roster, '/schedule/new', 'Schedule a Job', 'Save Job')


@app.route('/schedule/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def schedule_edit(job_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cleaning_jobs WHERE id = %s', (job_id,))
    job = cursor.fetchone()
    if not job:
        conn.close()
        return redirect('/schedule')

    if request.method == 'POST':
        old_status = job['status']
        new_status = request.form.get('status', 'scheduled')
        recurrence_rule = request.form.get('recurrence_rule', 'one_time')
        cursor.execute('''UPDATE cleaning_jobs SET customer_id=%s, scheduled_date=%s, scheduled_time=%s,
            service_type=%s, status=%s, recurrence_rule=%s, price=%s, notes=%s WHERE id=%s''',
            (request.form['customer_id'], request.form['scheduled_date'],
             request.form.get('scheduled_time') or None, request.form.get('service_type', ''),
             new_status, recurrence_rule,
             request.form.get('price') or None, request.form.get('notes', ''), job_id))
        save_job_crew(cursor, job_id, request.form)
        if old_status != 'completed' and new_status == 'completed' and recurrence_rule != 'one_time':
            create_next_occurrence(cursor, request.form['customer_id'], request.form['scheduled_date'],
                                    request.form.get('scheduled_time') or None, request.form.get('service_type', ''),
                                    recurrence_rule, request.form.get('price') or None, request.form)
        conn.commit()
        conn.close()
        return redirect('/schedule')

    cursor.execute('SELECT * FROM customers ORDER BY first_name')
    customers = cursor.fetchall()
    cursor.execute('SELECT * FROM cleaning_job_crew WHERE cleaning_job_id=%s', (job_id,))
    crew_rows = cursor.fetchall()
    conn.close()
    roster = get_crew_roster()

    crew_by_role = {row['role']: row['candidate_id'] for row in crew_rows}
    lead_role = next((row['role'] for row in crew_rows if row['is_lead']), '')

    return job_form_html(job, crew_by_role, lead_role, customers, roster,
                          f'/schedule/{job_id}/edit', f'Edit Job: {job["scheduled_date"]}', 'Save Changes')


@app.route('/schedule/<int:job_id>/photos', methods=['GET'])
@login_required
def job_photos_view(job_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cleaning_jobs WHERE id=%s', (job_id,))
    job = cursor.fetchone()
    if not job:
        conn.close()
        return redirect('/schedule')
    cursor.execute('''SELECT * FROM job_photos WHERE cleaning_job_id=%s ORDER BY uploaded_date DESC''', (job_id,))
    photos = cursor.fetchall()
    conn.close()

    photo_html = ''
    for p in photos:
        label_color = '#3498db' if p['photo_type'] == 'before' else '#27ae60'
        label = 'Before' if p['photo_type'] == 'before' else 'After'
        photo_html += f'''
        <div style="display:inline-block;margin:8px;text-align:center;vertical-align:top;">
            <a href="{p["cloudinary_url"]}" target="_blank">
                <img src="{p["cloudinary_url"]}" style="width:180px;height:140px;object-fit:cover;border-radius:8px;border:2px solid {label_color};">
            </a>
            <div style="margin-top:4px;">
                <span style="background:{label_color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold;">{label}</span>
                <form method="POST" action="/schedule/{job_id}/photos/{p["id"]}/delete"
                      style="display:inline;background:none;box-shadow:none;padding:0;"
                      onsubmit="return confirm('Delete this photo?');">
                    <button type="submit" style="background:none;border:none;color:#c0392b;cursor:pointer;font-size:12px;margin-left:4px;">✕</button>
                </form>
            </div>
        </div>'''

    return STYLE + admin_nav() + f'''
    <h1>Job Photos: {job["scheduled_date"]}</h1>
    <p><a class="btn" href="/schedule/{job_id}/edit">← Back to Job</a></p>
    <h2 style="font-size:1.1rem;margin-top:1.5rem;">Upload New Photo</h2>
    <form method="POST" action="/schedule/{job_id}/photos" enctype="multipart/form-data">
        <label>Photo Type:</label>
        <select name="photo_type">
            <option value="before">Before</option>
            <option value="after">After</option>
        </select>
        <label>Photo:</label>
        <input type="file" name="photo" accept="image/*" required>
        <button class="btn btn-success" type="submit">Upload Photo</button>
    </form>
    <h2 style="font-size:1.1rem;margin-top:2rem;">Photos ({len(photos)})</h2>
    {photo_html if photos else "<p style='color:#888;'>No photos yet for this job.</p>"}
    '''


@app.route('/schedule/<int:job_id>/photos', methods=['POST'])
@login_required
def job_photos_upload(job_id):
    photo_file = request.files.get('photo')
    photo_type = request.form.get('photo_type', 'before')
    if photo_file and photo_file.filename:
        upload_result = cloudinary.uploader.upload(
            photo_file,
            resource_type='image',
            folder='imhotep_job_photos',
            use_filename=True,
            unique_filename=True,
            access_mode='public',
            type='upload'
        )
        photo_url = upload_result.get('secure_url', '')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO job_photos (cleaning_job_id, cloudinary_url, photo_type) VALUES (%s, %s, %s)',
            (job_id, photo_url, photo_type)
        )
        conn.commit()
        conn.close()
    return redirect(f'/schedule/{job_id}/photos')


@app.route('/schedule/<int:job_id>/photos/<int:photo_id>/delete', methods=['POST'])
@login_required
def job_photos_delete(job_id, photo_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM job_photos WHERE id=%s AND cleaning_job_id=%s', (photo_id, job_id))
    conn.commit()
    conn.close()
    return redirect(f'/schedule/{job_id}/photos')


@app.route('/schedule/<int:job_id>/delete', methods=['POST'])
@login_required
def schedule_delete(job_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cleaning_job_crew WHERE cleaning_job_id=%s', (job_id,))
    cursor.execute('DELETE FROM cleaning_jobs WHERE id=%s', (job_id,))
    conn.commit()
    conn.close()
    return redirect('/schedule')


JOB_STATUS_COLORS = {
    'scheduled':            '#3498db',
    'in_progress':          '#f39c12',
    'completed':            '#27ae60',
    'rescheduled':          '#95a5a6',
    'cancelled':            '#c0392b',
    'pending_confirmation': '#9b59b6',
}



@app.route('/schedule/calendar')
@login_required
def schedule_calendar():
    import datetime as _dt
    import calendar as _cal
    view = request.args.get('view', 'month')
    today = _dt.date.today()
    year  = int(request.args.get('year',  today.year))
    month = int(request.args.get('month', today.month))
    week_start_str = request.args.get('week_start', '')
    if week_start_str:
        week_start = _dt.date.fromisoformat(week_start_str)
    else:
        week_start = today - _dt.timedelta(days=today.weekday())
    conn = get_db()
    cursor = conn.cursor()
    if view == 'month':
        first_day = _dt.date(year, month, 1)
        last_day  = _dt.date(year, month, _cal.monthrange(year, month)[1])
        cursor.execute(
            "SELECT cleaning_jobs.*, customers.first_name as cust_first, customers.last_name as cust_last"
            " FROM cleaning_jobs JOIN customers ON cleaning_jobs.customer_id = customers.id"
            " WHERE cleaning_jobs.scheduled_date BETWEEN %s AND %s"
            " AND cleaning_jobs.status != 'pending_confirmation'"
            " ORDER BY cleaning_jobs.scheduled_date, cleaning_jobs.scheduled_time",
            (first_day, last_day))
    else:
        week_end = week_start + _dt.timedelta(days=6)
        cursor.execute(
            "SELECT cleaning_jobs.*, customers.first_name as cust_first, customers.last_name as cust_last"
            " FROM cleaning_jobs JOIN customers ON cleaning_jobs.customer_id = customers.id"
            " WHERE cleaning_jobs.scheduled_date BETWEEN %s AND %s"
            " AND cleaning_jobs.status != 'pending_confirmation'"
            " ORDER BY cleaning_jobs.scheduled_date, cleaning_jobs.scheduled_time",
            (week_start, week_end))
    jobs = cursor.fetchall()
    conn.close()
    jobs_by_date = {}
    for j in jobs:
        d = str(j['scheduled_date'])
        jobs_by_date.setdefault(d, []).append(j)
    if view == 'month':
        prev_m = month - 1 if month > 1 else 12
        prev_y = year if month > 1 else year - 1
        next_m = month + 1 if month < 12 else 1
        next_y = year if month < 12 else year + 1
        prev_url = "/schedule/calendar?view=month&year=" + str(prev_y) + "&month=" + str(prev_m)
        next_url = "/schedule/calendar?view=month&year=" + str(next_y) + "&month=" + str(next_m)
        title = _cal.month_name[month] + " " + str(year)
    else:
        prev_ws = (week_start - _dt.timedelta(days=7)).isoformat()
        next_ws = (week_start + _dt.timedelta(days=7)).isoformat()
        prev_url = "/schedule/calendar?view=week&week_start=" + prev_ws
        next_url = "/schedule/calendar?view=week&week_start=" + next_ws
        title = "Week of " + week_start.strftime("%b %d, %Y")
    month_url = "/schedule/calendar?view=month&year=" + str(year) + "&month=" + str(month)
    week_url  = "/schedule/calendar?view=week&week_start=" + week_start.isoformat()
    month_active = "active" if view == "month" else ""
    week_active  = "active" if view == "week"  else ""
    html = STYLE + admin_nav()
    html += "<style>.cal-nav{display:flex;gap:8px;align-items:center;margin-bottom:1rem;}"
    html += ".cal-nav a{padding:6px 14px;background:#5C3D2E;color:#FFF9F0;border-radius:6px;text-decoration:none;font-size:13px;font-weight:700;}"
    html += ".view-toggle{display:flex;gap:6px;}"
    html += ".view-toggle a{padding:6px 14px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:700;border:2px solid #5C3D2E;color:#5C3D2E;}"
    html += ".view-toggle a.active{background:#5C3D2E;color:#FFF9F0;}"
    html += ".month-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:1px;background:#ddd;border-radius:8px;overflow:hidden;}"
    html += ".month-day-header{background:#5C3D2E;color:#FFF9F0;text-align:center;padding:8px;font-size:12px;font-weight:700;}"
    html += ".month-day{background:#fff;min-height:90px;padding:4px;}"
    html += ".month-day.today-cell{background:#fdf6ec;}"
    html += ".day-num{font-size:12px;font-weight:700;color:#5C3D2E;margin-bottom:4px;}"
    html += ".cal-job{font-size:11px;padding:2px 5px;border-radius:3px;margin-bottom:2px;color:white;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;text-decoration:none;}"
    html += ".week-grid{display:grid;grid-template-columns:60px repeat(7,1fr);gap:1px;background:#ddd;border-radius:8px;overflow:hidden;}"
    html += ".week-day-header{background:#5C3D2E;color:#FFF9F0;text-align:center;padding:10px 4px;font-size:12px;font-weight:700;}"
    html += ".week-time{background:#f5f5f5;text-align:right;padding:4px 6px;font-size:10px;color:#888;}"
    html += ".week-cell{background:#fff;min-height:50px;padding:2px;}"
    html += ".week-cell.today-cell{background:#fdf6ec;}</style>"
    html += "<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;'>"
    html += "<h1 style='margin:0;'>Calendar</h1>"
    html += "<div class='view-toggle'>"
    html += "<a href='" + month_url + "' class='" + month_active + "'>Month</a>"
    html += "<a href='" + week_url  + "' class='" + week_active  + "'>Week</a>"
    html += "</div></div>"
    html += "<div class='cal-nav'>"
    html += "<a href='" + prev_url + "'>&larr; Prev</a>"
    html += "<strong style='font-size:1.1rem;'>" + title + "</strong>"
    html += "<a href='" + next_url + "'>Next &rarr;</a>"
    html += "<a href='/schedule/new' style='margin-left:12px;background:#27ae60;'>+ New Job</a>"
    html += "</div>"
    if view == 'month':
        html += "<div class='month-grid'>"
        for dn in ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']:
            html += "<div class='month-day-header'>" + dn + "</div>"
        first_weekday = _dt.date(year, month, 1).weekday()
        for _ in range(first_weekday):
            html += "<div class='month-day' style='background:#f9f9f9;'></div>"
        num_days = _cal.monthrange(year, month)[1]
        for day in range(1, num_days + 1):
            d = _dt.date(year, month, day)
            extra = " today-cell" if d == today else ""
            html += "<div class='month-day" + extra + "'><div class='day-num'>" + str(day) + "</div>"
            for j in jobs_by_date.get(str(d), []):
                color = JOB_STATUS_COLORS.get(j["status"], "#95a5a6")
                t = format_job_time(j["scheduled_time"]) if j["scheduled_time"] else ""
                label = (t + " " if t else "") + j["cust_first"] + " " + j["cust_last"]
                html += "<a class='cal-job' href='/schedule/" + str(j["id"]) + "/edit' style='background:" + color + ";' title='" + label + "'>" + label + "</a>"
            html += "</div>"
        remainder = (7 - (first_weekday + num_days) % 7) % 7
        for _ in range(remainder):
            html += "<div class='month-day' style='background:#f9f9f9;'></div>"
        html += "</div>"
    else:
        days = [week_start + _dt.timedelta(days=i) for i in range(7)]
        html += "<div class='week-grid'>"
        html += "<div class='week-day-header'></div>"
        for d in days:
            bg = "background:#D4A843;color:#fff;" if d == today else ""
            html += "<div class='week-day-header' style='" + bg + "'>" + d.strftime("%a") + "<br><span style='font-size:14px;'>" + str(d.day) + "</span></div>"
        for hour in range(7, 21):
            label = ("12" if hour == 12 else str(hour % 12)) + ("am" if hour < 12 else "pm")
            html += "<div class='week-time'>" + label + "</div>"
            for d in days:
                extra = " today-cell" if d == today else ""
                html += "<div class='week-cell" + extra + "'>"
                for j in jobs_by_date.get(str(d), []):
                    jt = j["scheduled_time"]
                    show = False
                    if jt:
                        job_hour = (int(jt.total_seconds()) // 3600) % 24
                        show = (job_hour == hour)
                    elif hour == 8:
                        show = True
                    if show:
                        color = JOB_STATUS_COLORS.get(j["status"], "#95a5a6")
                        lbl = j["cust_first"] + " " + j["cust_last"]
                        html += "<a class='cal-job' href='/schedule/" + str(j["id"]) + "/edit' style='background:" + color + ";'>" + lbl + "</a>"
                html += "</div>"
        html += "</div>"
    html += "<div style='margin-top:1rem;display:flex;flex-wrap:wrap;gap:8px;'>"
    for st, color in JOB_STATUS_COLORS.items():
        if st == "pending_confirmation":
            continue
        lbl = st.replace("_", " ").title()
        html += "<span style='background:" + color + ";color:white;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:bold;'>" + lbl + "</span>"
    html += "</div>"
    return html


@app.route('/schedule/timesheets')
@login_required
def schedule_timesheets():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT time_punches.*, candidates.first_name, candidates.last_name,"
        " cleaning_jobs.scheduled_date, cleaning_jobs.service_type,"
        " customers.first_name as cust_first, customers.last_name as cust_last"
        " FROM time_punches"
        " JOIN candidates ON time_punches.candidate_id = candidates.id"
        " LEFT JOIN cleaning_jobs ON time_punches.cleaning_job_id = cleaning_jobs.id"
        " LEFT JOIN customers ON cleaning_jobs.customer_id = customers.id"
        " ORDER BY time_punches.clock_in DESC LIMIT 100")
    punches = cursor.fetchall()
    conn.close()
    html = STYLE + admin_nav() + "<h1>Timesheets</h1>"
    html += "<p><a class='btn' href='/schedule'>&larr; Back to Schedule</a></p>"
    if not punches:
        html += "<div class='info'><p>No time punches yet.</p></div>"
        return html
    html += "<style>.ts-table{width:100%;border-collapse:collapse;margin-top:1rem;}.ts-table th{background:#5C3D2E;color:#FFF9F0;padding:10px 12px;text-align:left;font-size:13px;}.ts-table td{padding:10px 12px;border-bottom:1px solid #eee;font-size:13px;vertical-align:middle;}.ts-table tr:hover td{background:#fdf6ec;}</style>"
    html += "<table class='ts-table'><tr><th>Staff</th><th>Job</th><th>Clock In</th><th>Clock Out</th><th>Hours</th><th>Location</th></tr>"
    for p in punches:
        name = p["first_name"] + " " + p["last_name"]
        job_label = (p["cust_first"] + " " + p["cust_last"] + " (" + str(p["scheduled_date"]) + ")") if p.get("cust_first") else "General"
        cin  = str(p["clock_in"])[:16] if p["clock_in"] else "—"
        cout = str(p["clock_out"])[:16] if p["clock_out"] else "Still clocked in"
        if p["clock_in"] and p["clock_out"]:
            diff = (p["clock_out"] - p["clock_in"]).total_seconds()
            hrs = int(diff // 3600)
            mins = int((diff % 3600) // 60)
            hours_str = str(hrs) + "h " + str(mins) + "m"
        else:
            hours_str = "—"
        if p["clock_in_lat"] and p["clock_in_lng"]:
            map_url = "https://maps.google.com/?q=" + str(p["clock_in_lat"]) + "," + str(p["clock_in_lng"])
            location = "<a href='" + map_url + "' target='_blank' style='color:#3498db;'>View Map</a>"
        else:
            location = "—"
        html += "<tr><td>" + name + "</td><td>" + job_label + "</td><td>" + cin + "</td><td>" + cout + "</td><td>" + hours_str + "</td><td>" + location + "</td></tr>"
    html += "</table>"
    return html


@app.route('/timeclock/clockin', methods=['POST'])
def timeclock_clockin():
    trainee_id = session.get('trainee_id')
    if not trainee_id:
        return redirect('/trainee-login')
    job_id = request.form.get('job_id') or None
    lat = request.form.get('lat') or None
    lng = request.form.get('lng') or None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT candidate_id FROM trainees WHERE id=%s', (trainee_id,))
    t = cursor.fetchone()
    if t:
        cursor.execute('SELECT id FROM time_punches WHERE candidate_id=%s AND clock_out IS NULL', (t['candidate_id'],))
        if not cursor.fetchone():
            cursor.execute(
                'INSERT INTO time_punches (candidate_id, cleaning_job_id, clock_in, clock_in_lat, clock_in_lng) VALUES (%s, %s, NOW(), %s, %s)',
                (t['candidate_id'], job_id, lat, lng))
            conn.commit()
    conn.close()
    return redirect('/timeclock')


@app.route('/timeclock/clockout', methods=['POST'])
def timeclock_clockout():
    trainee_id = session.get('trainee_id')
    if not trainee_id:
        return redirect('/trainee-login')
    lat = request.form.get('lat') or None
    lng = request.form.get('lng') or None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT candidate_id FROM trainees WHERE id=%s', (trainee_id,))
    t = cursor.fetchone()
    if t:
        cursor.execute(
            'UPDATE time_punches SET clock_out=NOW(), clock_out_lat=%s, clock_out_lng=%s WHERE candidate_id=%s AND clock_out IS NULL',
            (lat, lng, t['candidate_id']))
        conn.commit()
    conn.close()
    return redirect('/timeclock')


@app.route('/timeclock')
def timeclock_portal():
    trainee_id = session.get('trainee_id')
    if not trainee_id:
        return redirect('/trainee-login')
    import datetime as _dt
    today = _dt.date.today()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT candidates.id as cand_id, candidates.first_name FROM trainees'
        ' JOIN candidates ON trainees.candidate_id = candidates.id WHERE trainees.id=%s',
        (trainee_id,))
    cand = cursor.fetchone()
    cand_id = cand['cand_id'] if cand else None
    today_jobs = []
    active_punch = None
    if cand_id:
        cursor.execute(
            'SELECT cleaning_jobs.id, cleaning_jobs.scheduled_time, cleaning_jobs.service_type,'
            ' customers.first_name as cust_first, customers.last_name as cust_last'
            ' FROM cleaning_job_crew'
            ' JOIN cleaning_jobs ON cleaning_job_crew.cleaning_job_id = cleaning_jobs.id'
            ' JOIN customers ON cleaning_jobs.customer_id = customers.id'
            ' WHERE cleaning_job_crew.candidate_id=%s AND cleaning_jobs.scheduled_date=%s'
            " AND cleaning_jobs.status IN ('scheduled','in_progress')",
            (cand_id, today))
        today_jobs = cursor.fetchall()
        cursor.execute('SELECT * FROM time_punches WHERE candidate_id=%s AND clock_out IS NULL', (cand_id,))
        active_punch = cursor.fetchone()
    conn.close()
    tc_parts = []
    tc_parts.append(STYLE + trainee_nav())
    tc_parts.append('<h1>Time Clock</h1>')
    tc_parts.append('<script>'
                    'var _lat="",_lng="";'
                    'if(navigator.geolocation){'
                    'navigator.geolocation.getCurrentPosition('
                    'function(p){_lat=p.coords.latitude;_lng=p.coords.longitude;'
                    'document.getElementById("tc-status").textContent="Location ready."},'
                    'function(){document.getElementById("tc-status").textContent="Location unavailable."}'
                    ')}'
                    'function injectGPS(la,ln){'
                    'document.getElementById(la).value=_lat;'
                    'document.getElementById(ln).value=_lng;'
                    '}'
                    '</script>')
    tc_parts.append('<p id="tc-status" style="color:#888;font-size:13px;">Getting location...</p>')
    if active_punch:
        cin = str(active_punch['clock_in'])[:16]
        tc_parts.append('<div class="success">'
                        '<p><strong>Clocked in since:</strong> ' + cin + '</p>'
                        '<form method="POST" action="/timeclock/clockout"'
                        ' style="background:none;box-shadow:none;padding:0;">'
                        '<input type="hidden" name="lat" id="out-lat">'
                        '<input type="hidden" name="lng" id="out-lng">'
                        '<button class="btn" type="submit" style="background:#c0392b;"'
                        ' onclick="injectGPS(&apos;out-lat&apos;,&apos;out-lng&apos;)">'
                        'Clock Out</button></form></div>')
    elif today_jobs:
        tc_parts.append('<p>Select your job to clock in:</p>')
        for j in today_jobs:
            t = format_job_time(j['scheduled_time']) if j['scheduled_time'] else ''
            label = (t + ' - ' if t else '') + j['cust_first'] + ' ' + j['cust_last']
            jid = str(j['id'])
            la = 'lat-' + jid
            ln = 'lng-' + jid
            oc = 'injectGPS(&apos;' + la + '&apos;,&apos;' + ln + '&apos;)'
            tc_parts.append(
                '<div class="application">'
                '<p><strong>' + label + '</strong></p>'
                '<p>' + (j['service_type'] or '') + '</p>'
                '<form method="POST" action="/timeclock/clockin"'
                ' style="background:none;box-shadow:none;padding:0;">'
                '<input type="hidden" name="job_id" value="' + jid + '">'
                '<input type="hidden" name="lat" id="' + la + '">'
                '<input type="hidden" name="lng" id="' + ln + '">'
                '<button class="btn btn-success" type="submit"'
                ' onclick="' + oc + '">Clock In</button>'
                '</form></div>'
            )
    else:
        tc_parts.append('<div class="info"><p>No jobs assigned for today.</p></div>')
    tc_parts.append('<p style="margin-top:1rem;"><a class="btn" href="/trainee/documents"'
                    ' style="background:#95a5a6;">Back to Portal</a></p>')
    return ''.join(tc_parts)

COMPLIANCE_CATEGORIES = ['Insurance', 'Tax Filing', 'License', 'Registration', 'Payroll', 'Other']
COMPLIANCE_RECURRENCE = {'one_time': 'One-Time', 'monthly': 'Monthly', 'quarterly': 'Quarterly', 'annual': 'Annual'}
COMPLIANCE_STATUS = {
    'current':   ('Current',   '#27ae60'),
    'due_soon':  ('Due Soon',  '#f39c12'),
    'overdue':   ('Overdue',   '#c0392b'),
    'completed': ('Completed', '#3498db'),
}
MARKETS = ['Las Vegas', 'Salt Lake City', 'Both']


def compliance_status_badge(status, due_date=None):
    import datetime as _dt
    if due_date and status != 'completed':
        days = (due_date - _dt.date.today()).days
        if days < 0:
            status = 'overdue'
        elif days <= 30:
            status = 'due_soon'
        else:
            status = 'current'
    label, color = COMPLIANCE_STATUS.get(status, ('Unknown', '#95a5a6'))
    return f'<span style="background:{color};color:white;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:bold;">{label}</span>'


def advance_compliance_date(due_date, recurrence):
    import calendar as _cal
    import datetime as _dt
    if recurrence == 'monthly':
        m, y = due_date.month + 1, due_date.year
        if m > 12: m, y = 1, y + 1
        return due_date.replace(year=y, month=m, day=min(due_date.day, _cal.monthrange(y, m)[1]))
    elif recurrence == 'quarterly':
        m, y = due_date.month + 3, due_date.year
        while m > 12: m, y = m - 12, y + 1
        return due_date.replace(year=y, month=m, day=min(due_date.day, _cal.monthrange(y, m)[1]))
    elif recurrence == 'annual':
        try:
            return due_date.replace(year=due_date.year + 1)
        except ValueError:
            return due_date.replace(year=due_date.year + 1, day=28)
    return None


@app.route('/compliance')
@login_required
def compliance_list():
    import datetime as _dt
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM compliance_items ORDER BY due_date ASC')
    items = cursor.fetchall()
    conn.close()
    today = _dt.date.today()
    html = STYLE + admin_nav() + """<style>
    .comp-table{width:100%;border-collapse:collapse;margin-top:1rem;}
    .comp-table th{background:#5C3D2E;color:#FFF9F0;padding:10px 14px;text-align:left;font-size:13px;}
    .comp-table td{padding:10px 14px;border-bottom:1px solid #eee;font-size:14px;vertical-align:middle;}
    .comp-table tr:hover td{background:#fdf6ec;}
    </style>"""
    html += '<h1>Compliance</h1><p><a class="btn btn-success" href="/compliance/new">+ Add Item</a></p>'
    if not items:
        html += '<div class="info"><p>No compliance items yet.</p></div>'
    else:
        html += '<table class="comp-table"><tr><th>Category</th><th>Description</th><th>Market</th><th>Due Date</th><th>Recurrence</th><th>Status</th><th>Notes</th><th></th></tr>'
        for item in items:
            days = (item['due_date'] - today).days
            badge = compliance_status_badge(item['status'], item['due_date'])
            days_str = f'({abs(days)}d overdue)' if days < 0 else f'({days}d)' if days <= 30 else ''
            rec_label = COMPLIANCE_RECURRENCE.get(item['recurrence'], item['recurrence'])
            notes_short = (item['notes'] or '')[:50]
            html += f'''<tr>
                <td>{item["category"]}</td>
                <td><strong>{item["description"]}</strong></td>
                <td>{item["market"]}</td>
                <td>{item["due_date"]} <span style="font-size:12px;color:#888;">{days_str}</span></td>
                <td>{rec_label}</td>
                <td>{badge}</td>
                <td style="font-size:12px;color:#666;">{notes_short}</td>
                <td><a class="btn" href="/compliance/{item["id"]}/edit">Edit</a></td>
            </tr>'''
        html += '</table>'
    return html


@app.route('/compliance/new', methods=['GET', 'POST'])
@login_required
def compliance_new():
    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO compliance_items
            (category, description, market, due_date, recurrence, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (request.form['category'], request.form['description'],
             request.form.get('market', 'Las Vegas'), request.form['due_date'],
             request.form.get('recurrence', 'one_time'), 'current',
             request.form.get('notes', '')))
        conn.commit()
        conn.close()
        return redirect('/compliance')
    cat_opts = ''.join(f'<option value="{c}">{c}</option>' for c in COMPLIANCE_CATEGORIES)
    rec_opts = ''.join(f'<option value="{v}">{l}</option>' for v, l in COMPLIANCE_RECURRENCE.items())
    mkt_opts = ''.join(f'<option value="{m}">{m}</option>' for m in MARKETS)
    return STYLE + admin_nav() + f'''
    <h1>Add Compliance Item</h1>
    <form method="POST">
        <label>Category:</label><select name="category">{cat_opts}</select>
        <label>Description:</label>
        <input type="text" name="description" required placeholder="e.g. Workers Comp Insurance monthly payment">
        <label>Market:</label><select name="market">{mkt_opts}</select>
        <label>Due Date:</label><input type="date" name="due_date" required>
        <label>Recurrence:</label><select name="recurrence">{rec_opts}</select>
        <label>Notes (carrier, policy number, contact, etc.):</label>
        <textarea name="notes" rows="3"></textarea>
        <button class="btn btn-success" type="submit">Save Item</button>
        <a class="btn" href="/compliance" style="background:#95a5a6;">Cancel</a>
    </form>'''


@app.route('/compliance/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def compliance_edit(item_id):
    import datetime as _dt
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM compliance_items WHERE id=%s', (item_id,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        return redirect('/compliance')
    if request.method == 'POST':
        action = request.form.get('action', 'save')
        new_due = request.form['due_date']
        recurrence = request.form.get('recurrence', 'one_time')
        if action == 'complete' and recurrence != 'one_time':
            base = _dt.datetime.strptime(new_due, '%Y-%m-%d').date()
            nxt = advance_compliance_date(base, recurrence)
            if nxt:
                new_due = nxt.strftime('%Y-%m-%d')
        cursor.execute('''UPDATE compliance_items SET category=%s, description=%s, market=%s,
            due_date=%s, recurrence=%s, status=%s, notes=%s WHERE id=%s''',
            (request.form['category'], request.form['description'],
             request.form.get('market', 'Las Vegas'), new_due,
             recurrence, 'current', request.form.get('notes', ''), item_id))
        conn.commit()
        conn.close()
        return redirect('/compliance')
    conn.close()
    cat_opts = ''.join(f'<option value="{c}" {"selected" if c == item["category"] else ""}>{c}</option>' for c in COMPLIANCE_CATEGORIES)
    rec_opts = ''.join(f'<option value="{v}" {"selected" if v == item["recurrence"] else ""}>{l}</option>' for v, l in COMPLIANCE_RECURRENCE.items())
    mkt_opts = ''.join(f'<option value="{m}" {"selected" if m == item["market"] else ""}>{m}</option>' for m in MARKETS)
    return STYLE + admin_nav() + f'''
    <h1>Edit: {item["description"]}</h1>
    <form method="POST">
        <label>Category:</label><select name="category">{cat_opts}</select>
        <label>Description:</label>
        <input type="text" name="description" required value="{item["description"]}">
        <label>Market:</label><select name="market">{mkt_opts}</select>
        <label>Due Date:</label><input type="date" name="due_date" required value="{item["due_date"]}">
        <label>Recurrence:</label><select name="recurrence">{rec_opts}</select>
        <label>Notes:</label>
        <textarea name="notes" rows="3">{item["notes"] or ""}</textarea>
        <button class="btn btn-success" type="submit" name="action" value="save">Save Changes</button>
        <button class="btn" type="submit" name="action" value="complete"
            style="background:#27ae60;"
            onclick="return confirm('Mark as filed/paid and advance to next due date?')">
            &#10003; Mark Filed / Paid
        </button>
        <a class="btn" href="/compliance" style="background:#95a5a6;">Cancel</a>
    </form>'''


# ── Document Library Routes ───────────────────────────────────────────────────

@app.route('/admin/documents')
@login_required
def admin_documents():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents ORDER BY title")
    docs = cur.fetchall()
    return render_template('admin_documents.html', documents=docs)


@app.route('/admin/documents/add', methods=['GET', 'POST'])
def admin_add_document():
    if not session.get('logged_in'):
        return redirect('/login')
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        doc_type = request.form.get('doc_type', 'signable')
        drive_link = request.form.get('drive_link', '').strip()
        description = request.form.get('description', '').strip()
        file_url = ''
        uploaded_file = request.files.get('document_file')
        if uploaded_file and uploaded_file.filename:
            upload_result = cloudinary.uploader.upload(
                uploaded_file,
                resource_type='image',
                folder='imhotep_docs',
                use_filename=True,
                unique_filename=True,
                access_mode='public',
                type='upload'
            )
            file_url = upload_result.get('secure_url', '')
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO documents (title, doc_type, drive_link, file_url, description, active) VALUES (%s, %s, %s, %s, %s, %s)",
            (title, doc_type, drive_link, file_url, description, 1)
        )
        conn.commit()
        return redirect('/admin/documents')
    return render_template('admin_document_form.html', doc=None)


@app.route('/admin/documents/delete/<int:doc_id>')
def delete_document(doc_id):
    if not session.get('logged_in'):
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM documents WHERE id=%s", (doc_id,))
    conn.commit()
    return redirect('/admin/documents')


@app.route('/admin/documents/edit/<int:doc_id>', methods=['GET', 'POST'])
def admin_edit_document(doc_id):
    if not session.get('logged_in'):
        return redirect('/login')
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        doc_type = request.form.get('doc_type', 'signable')
        drive_link = request.form.get('drive_link', '').strip()
        description = request.form.get('description', '').strip()
        active = 1 if request.form.get('active') else 0
        uploaded_file = request.files.get('document_file')
        file_url = request.form.get('existing_file_url', '')
        if uploaded_file and uploaded_file.filename:
            upload_result = cloudinary.uploader.upload(
                uploaded_file,
                resource_type='image',
                folder='imhotep_docs',
                use_filename=True,
                unique_filename=True,
                access_mode='public',
                type='upload'
            )
            file_url = upload_result.get('secure_url', '')
        cur.execute(
            "UPDATE documents SET title=%s, doc_type=%s, drive_link=%s, file_url=%s, description=%s, active=%s WHERE id=%s",
            (title, doc_type, drive_link, file_url, description, active, doc_id)
        )
        conn.commit()
        return redirect('/admin/documents')
    cur.execute("SELECT * FROM documents WHERE id=%s", (doc_id,))
    doc = cur.fetchone()
    return render_template('admin_document_form.html', doc=doc)


@app.route('/admin/documents/assign/<int:trainee_id>', methods=['GET', 'POST'])
def admin_assign_documents(trainee_id):
    if not session.get('logged_in'):
        return redirect('/login')
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        selected_ids = request.form.getlist('document_ids')
        # Remove unselected assignments that are still pending
        cur.execute(
            "DELETE FROM trainee_documents WHERE trainee_id=%s AND status='pending' AND document_id NOT IN ({})".format(
                ','.join(['%s'] * len(selected_ids)) if selected_ids else '0'
            ),
            [trainee_id] + [int(i) for i in selected_ids] if selected_ids else [trainee_id]
        )
        for doc_id in selected_ids:
            cur.execute(
                "INSERT IGNORE INTO trainee_documents (trainee_id, document_id) VALUES (%s, %s)",
                (trainee_id, int(doc_id))
            )
        conn.commit()
        return redirect(url_for('trainee_detail', trainee_id=trainee_id))
    cur.execute("SELECT * FROM trainees WHERE id=%s", (trainee_id,))
    trainee = cur.fetchone()
    cur.execute("SELECT * FROM documents WHERE active=1 ORDER BY title")
    all_docs = cur.fetchall()
    cur.execute("SELECT document_id FROM trainee_documents WHERE trainee_id=%s", (trainee_id,))
    assigned_ids = {row['document_id'] for row in cur.fetchall()}
    return render_template('admin_assign_documents.html', trainee=trainee, documents=all_docs, assigned_ids=assigned_ids)


@app.route('/admin/documents/verify/<int:assignment_id>', methods=['POST'])
def admin_verify_document(assignment_id):
    if not session.get('logged_in'):
        return redirect('/login')
    return redirect(url_for('trainee_detail', trainee_id=row['trainee_id']))
    cur = conn.cursor()
    verified_by = session.get('username', 'Admin')
    cur.execute(
        "UPDATE trainee_documents SET status='verified', verified_by=%s, verified_date=NOW() WHERE id=%s",
        (verified_by, assignment_id)
    )
    conn.commit()
    cur.execute("SELECT trainee_id FROM trainee_documents WHERE id=%s", (assignment_id,))
    row = cur.fetchone()
    return redirect(url_for('trainees_list'))


def _add_timeclock_links(page_html):
    """Add My Training + Time Clock links next to the My Documents link.

    The trainee documents templates have their own hardcoded menu that is
    missing the Time Clock link, which strands staff who need to clock in.
    Rather than editing the template, we inject the links into the rendered
    HTML right before it is sent to the browser.
    """
    try:
        training_link = '<a href="/training">My Training</a>'
        clock_link = '<a href="/timeclock">&#9200; Time Clock</a>'
        if 'href="/timeclock"' in page_html:
            return page_html  # already has it, nothing to do

        needle = '<a href="/trainee/documents">My Documents</a>'
        if needle in page_html:
            replacement = training_link + needle + clock_link
            return page_html.replace(needle, replacement, 1)

        # fall back: some templates may write the link slightly differently
        alt = "<a href='/trainee/documents'>My Documents</a>"
        if alt in page_html:
            replacement = training_link + alt + clock_link
            return page_html.replace(alt, replacement, 1)

        return page_html
    except Exception:
        return page_html


@app.route('/trainee/documents')
def trainee_documents():
    if not session.get('trainee_id'):
        return redirect('/trainee-login')
    trainee_id = session.get('trainee_id')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT td.id as assignment_id, d.title, d.doc_type, d.drive_link, d.file_url, d.description,
               td.status, td.signed_date, td.verified_date, td.verified_by
        FROM trainee_documents td
        JOIN documents d ON td.document_id = d.id
        WHERE td.trainee_id = %s
        ORDER BY d.title
    """, (trainee_id,))
    docs = cur.fetchall()
    conn.close()
    return _add_timeclock_links(render_template('trainee_documents.html', documents=docs))


@app.route('/trainee/documents/sign/<int:assignment_id>', methods=['GET', 'POST'])
def trainee_sign_document(assignment_id):
    if not session.get('trainee_id'):
        return redirect('/trainee-login')
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        signature_data = request.form.get('signature_data', '')
        cur.execute(
            "UPDATE trainee_documents SET status='signed', signature_data=%s, signed_date=NOW() WHERE id=%s",
            (signature_data, assignment_id)
        )
        conn.commit()
        return redirect('/trainee/documents')
    cur.execute("""
        SELECT td.*, d.title, d.drive_link, d.file_url, d.description
        FROM trainee_documents td
        JOIN documents d ON td.document_id = d.id
        WHERE td.id=%s
    """, (assignment_id,))
    assignment = cur.fetchone()
    return _add_timeclock_links(render_template('trainee_sign_document.html', assignment=assignment))

# ── End Document Library Routes ───────────────────────────────────────────────




@app.route('/leads/<int:lead_id>/convert', methods=['POST'])
def convert_lead(lead_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM leads WHERE id = %s', (lead_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return redirect('/leads')
    if isinstance(row, dict):
        lead = row
    else:
        cols = [d[0] for d in cursor.description]
        lead = dict(zip(cols, row))

    # Name: handle either a single 'name' column or first/last columns
    full_name = (lead.get('name') or
                 ((lead.get('first_name') or '') + ' ' + (lead.get('last_name') or '')).strip())
    parts = (full_name or 'Unknown').split(' ', 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ''

    phone = (lead.get('phone') or '').strip()
    email = (lead.get('email') or '').strip()
    address = (lead.get('address') or '').strip()
    lead_source_id = lead.get('lead_source_id') or lead.get('source_id') or None

    # Duplicate guard: same phone = same customer
    existing = None
    if phone:
        cursor.execute('SELECT id FROM customers WHERE phone = %s', (phone,))
        existing = cursor.fetchone()

    if existing is None:
        cursor.execute("""INSERT INTO customers
            (first_name, last_name, phone, email, address, active, lead_source_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (first_name, last_name, phone, email, address, 1, lead_source_id))

    # Mark the lead as done so pipeline counts stay honest
    if 'status' in lead:
        cursor.execute('UPDATE leads SET status = %s WHERE id = %s', ('done', lead_id))

    conn.commit()
    conn.close()
    return redirect('/customers')

# --- short source-tagged ad links (auto-generated) ---
_SHORT_SOURCES = {
    'fb': 'facebook',
    'nd': 'nextdoor',
    'gg': 'google',
    'cl': 'craigslist',
    'yelp': 'yelp',
    'ig': 'instagram',
    'tt': 'tiktok',
    'tb': 'thumbtack',
}

def _short_link_redirect():
    from flask import request as _rq, redirect as _rd
    _code = _rq.path.strip('/').lower()
    _src = _SHORT_SOURCES.get(_code, 'direct')
    return _rd('/quote?utm_source=' + _src, code=302)

for _sc, _ss in _SHORT_SOURCES.items():
    if not any(_r.rule == '/' + _sc for _r in app.url_map.iter_rules()):
        app.add_url_rule('/' + _sc, 'shortlink_' + _sc, _short_link_redirect)
# --- end short ad links ---

# ---------------------------------------------------------------------------
# RND_MODULE_V1 -- Research & Development
# Small problems take the decision path, large ones take the research path.
# Admin-only (session['logged_in']) + RND_CODE passcode. 404 to everyone else.
# ---------------------------------------------------------------------------
import os as _rnd_os
import html as _rnd_html
from datetime import datetime as _rnd_dt

_RND_DECISION_STEPS = [
    "Identify the problem",
    "Generate alternatives",
    "Evaluate and select",
    "Implement",
    "Evaluate the result",
]

_RND_RESEARCH_STEPS = [
    "Define the problem",
    "Literature review",
    "Design / hypothesis",
    "Collect data",
    "Analyze data",
    "Conclusions and recommendations",
    "Implement",
    "Evaluate the result",
]

_RND_DOMAINS = ["marketing", "hiring", "pricing", "labor", "ops", "finance", "product"]
_RND_READY = {"done": False}
_RND_404 = ("<h1>Not Found</h1><p>The requested URL was not found on the server.</p>", 404)


def _rnd_conn():
    return get_db()


def _rnd_style():
    return globals().get("STYLE", "")


def _rnd_nav():
    fn = globals().get("admin_nav")
    try:
        return fn() if callable(fn) else ""
    except Exception:
        return ""


def _rnd_is_admin():
    return bool(session.get("logged_in"))


def _rnd_unlocked():
    return bool(session.get("rnd_ok"))


def _rnd_esc(v):
    return _rnd_html.escape("" if v is None else str(v))


def _rnd_init():
    if _RND_READY["done"]:
        return
    conn = _rnd_conn()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS rnd_problems (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        statement TEXT,
        domain VARCHAR(50),
        reversible TINYINT(1) DEFAULT 0,
        recurring TINYINT(1) DEFAULT 0,
        data_on_hand TINYINT(1) DEFAULT 0,
        cost_bounded TINYINT(1) DEFAULT 0,
        path VARCHAR(20),
        path_override TINYINT(1) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'open',
        current_step INT DEFAULT 1,
        opened_at DATETIME,
        closed_at DATETIME,
        decision_made TEXT,
        predicted TEXT,
        metric VARCHAR(100),
        baseline DECIMAL(12,2),
        review_date DATE,
        actual DECIMAL(12,2),
        outcome VARCHAR(20),
        lesson TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS rnd_steps (
        id INT AUTO_INCREMENT PRIMARY KEY,
        problem_id INT NOT NULL,
        step_no INT,
        step_name VARCHAR(100),
        content TEXT,
        completed TINYINT(1) DEFAULT 0,
        completed_at DATETIME,
        INDEX (problem_id)
    )""")
    conn.commit()
    cur.close()
    conn.close()
    _RND_READY["done"] = True


def _rnd_triage(reversible, recurring, data_on_hand, cost_bounded):
    """Four yeses -> decision path. Any no -> research path."""
    return "decision" if all([reversible, recurring, data_on_hand, cost_bounded]) else "research"


def _rnd_chk(name, label):
    return ('<label style="display:block;margin:4px 0">'
            '<input type="checkbox" name="' + name + '" value="1"> ' + label + '</label>')


def _rnd_gate_page():
    b = ['<h1>R&amp;D</h1>',
         '<p>This area requires the R&amp;D passcode.</p>',
         '<form method="POST" action="/rnd/unlock" style="max-width:340px">',
         '<p><input type="password" name="code" autofocus '
         'style="width:100%;padding:10px" placeholder="Passcode"></p>',
         '<p><button type="submit" class="btn">Enter</button></p>',
         '</form>']
    if request.args.get("bad"):
        b.insert(2, '<p style="color:#b00"><b>Incorrect passcode.</b></p>')
    return _rnd_style() + _rnd_nav() + ''.join(b)


def _rnd_unlock():
    if not _rnd_is_admin():
        return _RND_404
    expected = _rnd_os.environ.get("RND_CODE", "")
    supplied = (request.form.get("code") or "").strip()
    if expected and supplied == expected:
        session["rnd_ok"] = True
        return redirect("/rnd")
    return redirect("/rnd?bad=1")


def _rnd_list():
    if not _rnd_is_admin():
        return _RND_404
    if not _rnd_unlocked():
        return _rnd_gate_page()
    _rnd_init()
    conn = _rnd_conn()
    cur = conn.cursor()
    cur.execute("""SELECT id, title, domain, path, status, current_step, outcome
                   FROM rnd_problems ORDER BY (status='closed'), id DESC""")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    body = ['<h1>R&amp;D</h1>',
            '<p style="color:#666">Small problems take the decision path. '
            'Large ones take the research path.</p>']
    if not rows:
        body.append('<p class="empty-msg">No problems logged yet.</p>')
    else:
        body.append('<table cellpadding="8" cellspacing="0" '
                    'style="border-collapse:collapse;width:100%">')
        body.append('<tr style="text-align:left;border-bottom:2px solid #ddd">'
                    '<th>#</th><th>Problem</th><th>Domain</th><th>Path</th>'
                    '<th>Status</th><th>Outcome</th></tr>')
        for r in rows:
            pid, title, domain, path, status, step, outcome = (r[0], r[1], r[2],
                                                               r[3], r[4], r[5], r[6])
            color = '#2d6cdf' if path == 'decision' else '#7a4bd0'
            badge = ('<span style="background:' + color + ';color:#fff;padding:2px 8px;'
                     'border-radius:10px;font-size:12px">' + _rnd_esc(path) + '</span>')
            body.append('<tr style="border-bottom:1px solid #eee">'
                        '<td>' + str(pid) + '</td>'
                        '<td><a href="/rnd/' + str(pid) + '">' + _rnd_esc(title) + '</a></td>'
                        '<td>' + _rnd_esc(domain) + '</td>'
                        '<td>' + badge + '</td>'
                        '<td>' + _rnd_esc(status) + ' (step ' + str(step) + ')</td>'
                        '<td>' + _rnd_esc(outcome or '-') + '</td></tr>')
        body.append('</table>')

    opts = ''.join('<option value="' + d + '">' + d + '</option>' for d in _RND_DOMAINS)
    body.append('<h2 style="margin-top:32px">Log a new problem</h2>')
    body.append('<form method="POST" action="/rnd/new" style="max-width:640px">')
    body.append('<p><input name="title" placeholder="Problem in one line" '
                'style="width:100%;padding:8px" required></p>')
    body.append('<p><textarea name="statement" rows="4" style="width:100%;padding:8px" '
                'placeholder="State the problem in a paragraph"></textarea></p>')
    body.append('<p>Domain: <select name="domain">' + opts + '</select></p>')
    body.append('<fieldset style="border:1px solid #ddd;padding:12px">'
                '<legend><b>Triage gate</b> &mdash; all four checked = decision path</legend>')
    body.append(_rnd_chk("reversible", "Reversible &mdash; can I undo it cheaply?"))
    body.append(_rnd_chk("recurring", "Recurring &mdash; have I faced this exact problem before?"))
    body.append(_rnd_chk("data_on_hand", "Known variables &mdash; do I already have the data?"))
    body.append(_rnd_chk("cost_bounded", "Bounded cost &mdash; is the downside small?"))
    body.append('</fieldset>')
    body.append('<p><input name="metric" placeholder="Metric to watch '
                '(e.g. leads_per_week_facebook)" style="width:100%;padding:8px"></p>')
    body.append('<p><input name="baseline" placeholder="Baseline value today (number)" '
                'style="width:100%;padding:8px"></p>')
    body.append('<p><input name="predicted" placeholder="What I expect to happen" '
                'style="width:100%;padding:8px"></p>')
    body.append('<p><label>Review on: <input type="date" name="review_date"></label></p>')
    body.append('<p><button type="submit" class="btn">Run triage</button></p></form>')
    return _rnd_style() + _rnd_nav() + ''.join(body)


def _rnd_new():
    if not _rnd_is_admin():
        return _RND_404
    if not _rnd_unlocked():
        return redirect("/rnd")
    _rnd_init()
    f = request.form
    rev = 1 if f.get("reversible") else 0
    rec = 1 if f.get("recurring") else 0
    dat = 1 if f.get("data_on_hand") else 0
    cost = 1 if f.get("cost_bounded") else 0
    path = _rnd_triage(rev, rec, dat, cost)
    steps = _RND_DECISION_STEPS if path == "decision" else _RND_RESEARCH_STEPS

    try:
        baseline = float(f.get("baseline")) if f.get("baseline") else None
    except ValueError:
        baseline = None

    conn = _rnd_conn()
    cur = conn.cursor()
    cur.execute("""INSERT INTO rnd_problems
        (title, statement, domain, reversible, recurring, data_on_hand, cost_bounded,
         path, status, current_step, opened_at, predicted, metric, baseline, review_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'open',1,%s,%s,%s,%s,%s)""",
        (f.get("title", "").strip(), f.get("statement", ""), f.get("domain", ""),
         rev, rec, dat, cost, path, _rnd_dt.now(),
         f.get("predicted", ""), f.get("metric", ""), baseline,
         f.get("review_date") or None))
    pid = cur.lastrowid
    for i, name in enumerate(steps, start=1):
        cur.execute("INSERT INTO rnd_steps (problem_id, step_no, step_name) VALUES (%s,%s,%s)",
                    (pid, i, name))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/rnd/" + str(pid))


def _rnd_detail(pid):
    if not _rnd_is_admin():
        return _RND_404
    if not _rnd_unlocked():
        return redirect("/rnd")
    _rnd_init()
    conn = _rnd_conn()
    cur = conn.cursor()
    cur.execute("""SELECT id,title,statement,domain,path,status,current_step,
                          predicted,metric,baseline,review_date,actual,outcome,lesson
                   FROM rnd_problems WHERE id=%s""", (pid,))
    p = cur.fetchone()
    if not p:
        cur.close()
        conn.close()
        return _RND_404
    cur.execute("""SELECT step_no, step_name, content, completed
                   FROM rnd_steps WHERE problem_id=%s ORDER BY step_no""", (pid,))
    steps = cur.fetchall()
    cur.close()
    conn.close()

    kind = ("Decision path &mdash; small problem" if p[4] == "decision"
            else "Research path &mdash; large problem")
    b = ['<p><a href="/rnd">&larr; All problems</a></p>',
         '<h1>' + _rnd_esc(p[1]) + '</h1>',
         '<p><b>' + kind + '</b> &nbsp;|&nbsp; ' + _rnd_esc(p[3]) +
         ' &nbsp;|&nbsp; ' + _rnd_esc(p[5]) + '</p>']
    if p[2]:
        b.append('<p style="background:#f6f6f6;padding:12px">' + _rnd_esc(p[2]) + '</p>')
    if p[8]:
        b.append('<p><b>Watching:</b> ' + _rnd_esc(p[8]) + ' &nbsp; baseline ' +
                 _rnd_esc(p[9]) + ' &nbsp; review ' + _rnd_esc(p[10]) + '</p>')
    if p[7]:
        b.append('<p><b>Predicted:</b> ' + _rnd_esc(p[7]) + '</p>')

    b.append('<h2>Steps</h2>')
    for s in steps:
        no, name, content, done = s[0], s[1], s[2], s[3]
        bg = '#f0fbf2' if done else '#fff'
        b.append('<div style="border:1px solid #ddd;background:' + bg +
                 ';padding:12px;margin:10px 0">')
        b.append('<b>' + str(no) + '. ' + ('&#10004; ' if done else '') +
                 _rnd_esc(name) + '</b>')
        b.append('<form method="POST" action="/rnd/' + str(pid) + '/step">')
        b.append('<input type="hidden" name="step_no" value="' + str(no) + '">')
        b.append('<textarea name="content" rows="3" style="width:100%;padding:8px">' +
                 _rnd_esc(content) + '</textarea>')
        b.append('<label style="display:inline-block;margin:6px 12px 0 0">'
                 '<input type="checkbox" name="completed" value="1"' +
                 (' checked' if done else '') + '> complete</label>')
        b.append('<button type="submit" class="btn">Save</button></form></div>')

    b.append('<h2>Outcome</h2>')
    if p[12]:
        b.append('<p><b>' + _rnd_esc(p[12]) + '</b> &mdash; actual ' + _rnd_esc(p[11]) + '</p>')
        b.append('<p>' + _rnd_esc(p[13]) + '</p>')
    else:
        b.append('<form method="POST" action="/rnd/' + str(pid) + '/close" '
                 'style="max-width:640px">')
        b.append('<p><input name="actual" placeholder="Actual value of the metric" '
                 'style="width:100%;padding:8px"></p>')
        b.append('<p><select name="outcome">'
                 '<option value="worked">worked</option>'
                 '<option value="failed">failed</option>'
                 '<option value="inconclusive">inconclusive</option></select></p>')
        b.append('<p><textarea name="lesson" rows="3" style="width:100%;padding:8px" '
                 'placeholder="What I learned"></textarea></p>')
        b.append('<p><button type="submit" class="btn">Close problem</button></p></form>')
    return _rnd_style() + _rnd_nav() + ''.join(b)


def _rnd_step(pid):
    if not _rnd_is_admin():
        return _RND_404
    if not _rnd_unlocked():
        return redirect("/rnd")
    _rnd_init()
    f = request.form
    done = 1 if f.get("completed") else 0
    try:
        no = int(f.get("step_no", 1))
    except ValueError:
        no = 1
    conn = _rnd_conn()
    cur = conn.cursor()
    cur.execute("""UPDATE rnd_steps SET content=%s, completed=%s, completed_at=%s
                   WHERE problem_id=%s AND step_no=%s""",
                (f.get("content", ""), done, _rnd_dt.now() if done else None, pid, no))
    cur.execute("""SELECT COALESCE(MIN(step_no), 0) FROM rnd_steps
                   WHERE problem_id=%s AND completed=0""", (pid,))
    row = cur.fetchone()
    nxt = row[0] if row and row[0] else no
    cur.execute("UPDATE rnd_problems SET current_step=%s, status='active' WHERE id=%s",
                (nxt, pid))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/rnd/" + str(pid))


def _rnd_close(pid):
    if not _rnd_is_admin():
        return _RND_404
    if not _rnd_unlocked():
        return redirect("/rnd")
    _rnd_init()
    f = request.form
    try:
        actual = float(f.get("actual")) if f.get("actual") else None
    except ValueError:
        actual = None
    conn = _rnd_conn()
    cur = conn.cursor()
    cur.execute("""UPDATE rnd_problems SET actual=%s, outcome=%s, lesson=%s,
                          status='closed', closed_at=%s WHERE id=%s""",
                (actual, f.get("outcome", ""), f.get("lesson", ""), _rnd_dt.now(), pid))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/rnd/" + str(pid))


# --- nav injection: wrap admin_nav instead of editing its internals -----------
if callable(globals().get("admin_nav")):
    _rnd_prev_admin_nav = admin_nav

    def admin_nav(*a, **kw):
        try:
            out = _rnd_prev_admin_nav(*a, **kw)
        except Exception:
            raise
        try:
            if not session.get("logged_in"):
                return out
            if 'href="/rnd"' in out:
                return out
            link = '<a href="/rnd">R&amp;D</a>'
            if "</nav>" in out:
                return out.replace("</nav>", link + "</nav>", 1)
            return out + link
        except Exception:
            return out


for _rnd_rule, _rnd_ep, _rnd_fn, _rnd_m in [
    ("/rnd", "rnd_list", _rnd_list, ["GET"]),
    ("/rnd/unlock", "rnd_unlock", _rnd_unlock, ["POST"]),
    ("/rnd/new", "rnd_new", _rnd_new, ["POST"]),
    ("/rnd/<int:pid>", "rnd_detail", _rnd_detail, ["GET"]),
    ("/rnd/<int:pid>/step", "rnd_step", _rnd_step, ["POST"]),
    ("/rnd/<int:pid>/close", "rnd_close", _rnd_close, ["POST"]),
]:
    if not any(str(r.rule) == _rnd_rule for r in app.url_map.iter_rules()):
        app.add_url_rule(_rnd_rule, _rnd_ep, _rnd_fn, methods=_rnd_m)
# ------------------------------------------------------- end RND_MODULE_V1



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
