from flask import Flask, request, redirect, send_from_directory, session, url_for
import sqlite3
import os
import time
import random
import string
import json
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Secret key for sessions - set this in Render's environment variables
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')

# Admin password - set this in Render's environment variables
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme')

# Upload folder - works locally and on Render
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database file - SQLite stores everything in one file
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'imhotep.db')


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            pay TEXT,
            location TEXT,
            posted_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            resume_filename TEXT,
            applied_date TEXT DEFAULT CURRENT_TIMESTAMP,
            job_id INTEGER,
            license_filename TEXT,
            ok_toilets TEXT,
            ok_kneel TEXT,
            ok_adult TEXT,
            ok_background TEXT,
            ok_teamwork TEXT,
            ok_parttime TEXT,
            tech_level INTEGER,
            has_transportation TEXT,
            has_supplies TEXT,
            score INTEGER,
            flagged INTEGER DEFAULT 0,
            hired INTEGER DEFAULT 0,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    ''')

    # Training modules created by admin
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            video_url TEXT,
            content TEXT,
            required INTEGER DEFAULT 1,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Quiz questions for each module
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT,
            option_d TEXT,
            correct_answer TEXT NOT NULL,
            FOREIGN KEY (module_id) REFERENCES training_modules(id)
        )
    ''')

    # Trainees (hired applicants with login access)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trainees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            access_code TEXT NOT NULL UNIQUE,
            hired_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    ''')

    # Track which modules each trainee has passed
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS module_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trainee_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            passed INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            completed_date TEXT,
            FOREIGN KEY (trainee_id) REFERENCES trainees(id),
            FOREIGN KEY (module_id) REFERENCES training_modules(id),
            UNIQUE(trainee_id, module_id)
        )
    ''')

    # Migration: add new columns to existing candidates table if missing
    existing_cols = [row[1] for row in cursor.execute("PRAGMA table_info(candidates)").fetchall()]
    new_cols = {
        'license_filename': 'TEXT',
        'ok_toilets': 'TEXT',
        'ok_kneel': 'TEXT',
        'ok_adult': 'TEXT',
        'ok_background': 'TEXT',
        'ok_teamwork': 'TEXT',
        'ok_parttime': 'TEXT',
        'tech_level': 'INTEGER',
        'has_transportation': 'TEXT',
        'has_supplies': 'TEXT',
        'score': 'INTEGER',
        'flagged': 'INTEGER DEFAULT 0',
        'hired': 'INTEGER DEFAULT 0',
    }
    for col, coltype in new_cols.items():
        if col not in existing_cols:
            cursor.execute(f'ALTER TABLE candidates ADD COLUMN {col} {coltype}')

    # Insert default jobs if table is empty
    cursor.execute('SELECT COUNT(*) FROM jobs')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''INSERT INTO jobs (title, description, pay, location)
                          VALUES (?, ?, ?, ?)''',
                       ('Part-Time Cleaner',
                        'Join Casey\'s Cleaning Company! We are hiring reliable, detail-oriented part-time cleaners for residential and commercial cleaning in Las Vegas.',
                        '$15-17/hr DOE',
                        'Las Vegas, NV'))
    conn.commit()
    conn.close()


# Initialize database on startup
init_db()


def login_required(f):
    """Decorator that protects admin pages."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def trainee_required(f):
    """Decorator that protects trainee pages."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('trainee_id'):
            return redirect(url_for('trainee_login'))
        return f(*args, **kwargs)
    return decorated_function


def generate_access_code(length=8):
    """Generate a random alphanumeric access code."""
    chars = string.ascii_uppercase + string.digits
    # Exclude confusing characters: 0, O, 1, I, L
    chars = chars.replace('0', '').replace('O', '').replace('1', '').replace('I', '').replace('L', '')
    return ''.join(random.choices(chars, k=length))


def calculate_score_and_flag(answers):
    """
    Returns (score, flagged) based on screening answers.
    score: 0-100
    flagged: 1 if any knockout failed, else 0
    """
    score = 0
    flagged = 0

    # Knockout questions (must all be 'yes' to pass)
    knockouts = ['ok_toilets', 'ok_kneel', 'ok_adult', 'ok_background']
    for q in knockouts:
        if answers.get(q) == 'yes':
            score += 15  # 4 x 15 = 60 points possible
        else:
            flagged = 1

    # Important but not knockout
    if answers.get('ok_teamwork') == 'yes':
        score += 10
    if answers.get('ok_parttime') == 'yes':
        score += 10

    # Tech level (1-5 scale, scaled to 0-10 points)
    try:
        tech = int(answers.get('tech_level') or 0)
        tech = max(0, min(5, tech))
        score += tech * 2  # 5 x 2 = 10 points possible
    except (ValueError, TypeError):
        pass

    # Plus factors
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
        <a href="/">View Jobs</a>
        <a href="/login">Admin Login</a>
        <a href="/trainee-login">Trainee Login</a>
    </div>
    '''


def admin_nav():
    return '''
    <div class="nav">
        <a href="/">View Jobs</a>
        <a href="/applications">Applications</a>
        <a href="/post-job">Post a Job</a>
        <a href="/training-modules">Training</a>
        <a href="/trainees">Trainees</a>
        <a href="/logout">Logout</a>
        <span class="admin-badge">ADMIN</span>
    </div>
    '''


def trainee_nav():
    return '''
    <div class="nav">
        <a href="/training">My Training</a>
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
    """Extract YouTube video ID from various YouTube URL formats."""
    if not url:
        return None
    url = url.strip()
    # Handle youtu.be short links
    if 'youtu.be/' in url:
        vid = url.split('youtu.be/')[-1].split('?')[0].split('&')[0]
        return vid
    # Handle youtube.com/watch?v=...
    if 'youtube.com/watch' in url and 'v=' in url:
        vid = url.split('v=')[-1].split('&')[0]
        return vid
    # Handle youtube.com/embed/...
    if 'youtube.com/embed/' in url:
        vid = url.split('embed/')[-1].split('?')[0].split('&')[0]
        return vid
    return None


def youtube_embed(url):
    """Return iframe HTML for a YouTube URL, or empty string."""
    vid = extract_youtube_id(url)
    if not vid:
        return ''
    return f'<iframe src="https://www.youtube.com/embed/{vid}" allowfullscreen></iframe>'


# ============ PUBLIC ROUTES ============

@app.route('/')
def show_jobs():
    conn = get_db()
    jobs = conn.execute('SELECT * FROM jobs ORDER BY posted_date DESC').fetchall()
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
            return redirect('/applications')
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
    session.pop('logged_in', None)
    return redirect('/')


# ============ ADMIN: APPLICATIONS ============

@app.route('/applications')
@login_required
def view_applications():
    conn = get_db()
    apps = conn.execute('''
        SELECT candidates.*, jobs.title as job_title
        FROM candidates
        LEFT JOIN jobs ON candidates.job_id = jobs.id
        ORDER BY candidates.flagged ASC, candidates.score DESC, candidates.applied_date DESC
    ''').fetchall()
    conn.close()

    html = STYLE + admin_nav() + '<h1>Job Applications</h1>'
    html += '<p class="form-note">Sorted by: not flagged first, then highest score, then newest.</p>'

    if not apps:
        html += '<p>No applications yet.</p>'
    else:
        for app_row in apps:
            resume_link = ''
            if app_row['resume_filename']:
                resume_link = f'<a class="btn" href="/resume/{app_row["resume_filename"]}" target="_blank">View Resume</a> '

            license_link = ''
            if app_row['license_filename']:
                license_link = f'<a class="btn" href="/resume/{app_row["license_filename"]}" target="_blank">View Driver\'s License</a>'

            flag_html = '<span class="flag-badge">FLAGGED</span>' if app_row['flagged'] else ''
            hired_html = '<span class="hired-badge">HIRED</span>' if app_row['hired'] else ''
            score = app_row['score'] if app_row['score'] is not None else 0
            score_html = f'<span class="score-badge {score_class(score)}">Score: {score}/100</span>'
            flagged_class = ' flagged' if app_row['flagged'] else ''

            tech_level = app_row['tech_level'] if app_row['tech_level'] is not None else 'Not answered'

            # Hire button (only if not already hired)
            hire_button = ''
            if not app_row['hired']:
                hire_button = f'''
                <form method="POST" action="/hire/{app_row['id']}" style="display:inline-block; margin-top:10px; box-shadow:none; padding:0; background:none;">
                    <button class="btn btn-success" type="submit">Hire & Send Training Access</button>
                </form>
                '''

            html += f'''
            <div class="application{flagged_class}">
                <h2>{app_row['first_name']} {app_row['last_name']} {score_html} {flag_html} {hired_html}</h2>
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
                {hire_button}
                <form method="POST" action="/delete/{app_row['id']}" onsubmit="return confirm('Delete this application?');" style="display:inline-block; margin-top:10px; box-shadow:none; padding:0; background:none;">
                    <button class="btn btn-danger" type="submit">Delete</button>
                </form>
            </div>
            '''

    return html


@app.route('/hire/<int:candidate_id>', methods=['POST'])
@login_required
def hire_candidate(candidate_id):
    """Mark candidate as hired and generate trainee access code."""
    conn = get_db()
    candidate = conn.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,)).fetchone()
    if not candidate:
        conn.close()
        return redirect('/applications')

    # Check if already a trainee
    existing = conn.execute('SELECT * FROM trainees WHERE candidate_id = ?', (candidate_id,)).fetchone()
    if existing:
        conn.close()
        return redirect(f'/trainee/{existing["id"]}')

    # Generate unique access code
    while True:
        code = generate_access_code()
        exists = conn.execute('SELECT 1 FROM trainees WHERE access_code = ?', (code,)).fetchone()
        if not exists:
            break

    conn.execute('INSERT INTO trainees (candidate_id, email, access_code) VALUES (?, ?, ?)',
                 (candidate_id, candidate['email'], code))
    conn.execute('UPDATE candidates SET hired = 1 WHERE id = ?', (candidate_id,))
    trainee_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.commit()
    conn.close()

    return redirect(f'/trainee/{trainee_id}')


@app.route('/delete/<int:candidate_id>', methods=['POST'])
@login_required
def delete_application(candidate_id):
    conn = get_db()
    conn.execute('DELETE FROM candidates WHERE id = ?', (candidate_id,))
    conn.commit()
    conn.close()
    return redirect('/applications')


@app.route('/post-job', methods=['GET', 'POST'])
@login_required
def post_job():
    if request.method == 'POST':
        conn = get_db()
        conn.execute('''INSERT INTO jobs (title, description, pay, location)
                        VALUES (?, ?, ?, ?)''',
                     (request.form['title'],
                      request.form['description'],
                      request.form['pay'],
                      request.form['location']))
        conn.commit()
        conn.close()
        return redirect('/')

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
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()

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
                resume_file.save(os.path.join(UPLOAD_FOLDER, resume_filename))

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

        conn.execute('''INSERT INTO candidates
                        (first_name, last_name, email, phone, resume_filename, job_id,
                         license_filename, ok_toilets, ok_kneel, ok_adult, ok_background,
                         ok_teamwork, ok_parttime, tech_level, has_transportation, has_supplies,
                         score, flagged)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
        <a class="btn" href="/">Back to Jobs</a>
        '''

    conn.close()

    if not job:
        return STYLE + public_nav() + '<h1>Job not found</h1><a href="/">Back</a>'

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

        <label>Driver's License (photo or scan, required):</label>
        <input type="file" name="license" required accept="image/*,.pdf">
        <p class="form-note">Used for identity verification and background check. Stored securely.</p>

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
    modules = conn.execute('SELECT * FROM training_modules ORDER BY created_date').fetchall()
    conn.close()

    html = STYLE + admin_nav() + '<h1>Training Modules</h1>'
    html += '<p><a class="btn btn-success" href="/training-modules/new">+ New Module</a></p>'

    if not modules:
        html += '<p>No training modules yet. Click "New Module" to create one.</p>'
    else:
        for m in modules:
            required_label = '<span class="status-label status-passed">Required</span>' if m['required'] else '<span class="status-label status-not-started">Optional</span>'

            # Count quiz questions
            conn = get_db()
            q_count = conn.execute('SELECT COUNT(*) FROM quiz_questions WHERE module_id = ?', (m['id'],)).fetchone()[0]
            conn.close()

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

    return html


@app.route('/training-modules/new', methods=['GET', 'POST'])
@login_required
def new_module():
    if request.method == 'POST':
        required = 1 if request.form.get('required') == 'on' else 0
        conn = get_db()
        conn.execute('''INSERT INTO training_modules (title, description, video_url, content, required)
                        VALUES (?, ?, ?, ?, ?)''',
                     (request.form['title'],
                      request.form.get('description', ''),
                      request.form.get('video_url', ''),
                      request.form.get('content', ''),
                      required))
        new_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
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
    module = conn.execute('SELECT * FROM training_modules WHERE id = ?', (module_id,)).fetchone()
    if not module:
        conn.close()
        return redirect('/training-modules')

    if request.method == 'POST':
        required = 1 if request.form.get('required') == 'on' else 0
        conn.execute('''UPDATE training_modules
                        SET title = ?, description = ?, video_url = ?, content = ?, required = ?
                        WHERE id = ?''',
                     (request.form['title'],
                      request.form.get('description', ''),
                      request.form.get('video_url', ''),
                      request.form.get('content', ''),
                      required,
                      module_id))
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
    conn.execute('DELETE FROM quiz_questions WHERE module_id = ?', (module_id,))
    conn.execute('DELETE FROM module_progress WHERE module_id = ?', (module_id,))
    conn.execute('DELETE FROM training_modules WHERE id = ?', (module_id,))
    conn.commit()
    conn.close()
    return redirect('/training-modules')


@app.route('/training-modules/<int:module_id>/questions', methods=['GET', 'POST'])
@login_required
def manage_questions(module_id):
    conn = get_db()
    module = conn.execute('SELECT * FROM training_modules WHERE id = ?', (module_id,)).fetchone()
    if not module:
        conn.close()
        return redirect('/training-modules')

    if request.method == 'POST':
        correct = request.form.get('correct_answer', 'a')
        conn.execute('''INSERT INTO quiz_questions
                        (module_id, question, option_a, option_b, option_c, option_d, correct_answer)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
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

    questions = conn.execute('SELECT * FROM quiz_questions WHERE module_id = ?', (module_id,)).fetchall()
    conn.close()

    html = STYLE + admin_nav() + f'<h1>Quiz Questions: {module["title"]}</h1>'
    html += '<p class="form-note">Trainees must answer ALL questions correctly to pass this module.</p>'

    if questions:
        html += '<h2>Existing Questions</h2>'
        for i, q in enumerate(questions, 1):
            html += f'''
            <div class="quiz-question">
                <p>Q{i}: {q['question']}</p>
                <p>A: {q['option_a']} {'✓' if q['correct_answer'] == 'a' else ''}</p>
                <p>B: {q['option_b']} {'✓' if q['correct_answer'] == 'b' else ''}</p>
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
    q = conn.execute('SELECT module_id FROM quiz_questions WHERE id = ?', (question_id,)).fetchone()
    if q:
        conn.execute('DELETE FROM quiz_questions WHERE id = ?', (question_id,))
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
    trainees = conn.execute('''
        SELECT trainees.*, candidates.first_name, candidates.last_name
        FROM trainees
        LEFT JOIN candidates ON trainees.candidate_id = candidates.id
        ORDER BY trainees.hired_date DESC
    ''').fetchall()

    # Get required module count for certification check
    required_count = conn.execute('SELECT COUNT(*) FROM training_modules WHERE required = 1').fetchone()[0]

    html = STYLE + admin_nav() + '<h1>Trainees</h1>'

    if not trainees:
        html += '<p>No trainees yet. Hire someone from the Applications page to create a trainee.</p>'
    else:
        for t in trainees:
            passed_count = conn.execute(
                'SELECT COUNT(*) FROM module_progress mp JOIN training_modules tm ON mp.module_id = tm.id WHERE mp.trainee_id = ? AND mp.passed = 1 AND tm.required = 1',
                (t['id'],)
            ).fetchone()[0]

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
            </div>
            '''
    conn.close()
    return html


@app.route('/trainee/<int:trainee_id>')
@login_required
def trainee_detail(trainee_id):
    conn = get_db()
    t = conn.execute('''
        SELECT trainees.*, candidates.first_name, candidates.last_name, candidates.phone
        FROM trainees
        LEFT JOIN candidates ON trainees.candidate_id = candidates.id
        WHERE trainees.id = ?
    ''', (trainee_id,)).fetchone()

    if not t:
        conn.close()
        return redirect('/trainees')

    modules = conn.execute('SELECT * FROM training_modules ORDER BY created_date').fetchall()
    progress_rows = conn.execute('SELECT * FROM module_progress WHERE trainee_id = ?', (trainee_id,)).fetchall()
    progress = {p['module_id']: p for p in progress_rows}

    required_count = conn.execute('SELECT COUNT(*) FROM training_modules WHERE required = 1').fetchone()[0]
    passed_required = sum(1 for m in modules if m['required'] and progress.get(m['id']) and progress[m['id']]['passed'])
    certified = passed_required >= required_count and required_count > 0

    conn.close()

    cert_html = '<span class="cert-badge">CERTIFIED</span>' if certified else ''

    html = STYLE + admin_nav() + f'<h1>{t["first_name"]} {t["last_name"]} {cert_html}</h1>'
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

    html += '<h2>Module Progress</h2>'
    if not modules:
        html += '<p>No training modules created yet.</p>'
    else:
        for m in modules:
            p = progress.get(m['id'])
            if p and p['passed']:
                status = '<span class="status-label status-passed">PASSED</span>'
                card_class = 'module-card passed'
            elif p and p['attempts'] > 0:
                status = f'<span class="status-label status-failed">Attempted ({p["attempts"]}x)</span>'
                card_class = 'module-card failed'
            else:
                status = '<span class="status-label status-not-started">Not Started</span>'
                card_class = 'module-card'

            req_label = '(Required)' if m['required'] else '(Optional)'
            html += f'''
            <div class="{card_class}">
                <h3>{m['title']} {req_label}</h3>
                <p>{status}</p>
            </div>
            '''

    return html


# ============ TRAINEE AUTH ============

@app.route('/trainee-login', methods=['GET', 'POST'])
def trainee_login():
    error = ''
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        code = request.form.get('access_code', '').strip().upper()
        conn = get_db()
        trainee = conn.execute(
            'SELECT * FROM trainees WHERE LOWER(email) = ? AND access_code = ?',
            (email, code)
        ).fetchone()
        conn.close()

        if trainee:
            session['trainee_id'] = trainee['id']
            return redirect('/training')
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
    session.pop('trainee_id', None)
    return redirect('/')


# ============ TRAINEE: TRAINING PORTAL ============

@app.route('/training')
@trainee_required
def my_training():
    trainee_id = session.get('trainee_id')
    conn = get_db()
    trainee = conn.execute('''
        SELECT trainees.*, candidates.first_name
        FROM trainees LEFT JOIN candidates ON trainees.candidate_id = candidates.id
        WHERE trainees.id = ?
    ''', (trainee_id,)).fetchone()

    modules = conn.execute('SELECT * FROM training_modules ORDER BY created_date').fetchall()
    progress_rows = conn.execute('SELECT * FROM module_progress WHERE trainee_id = ?', (trainee_id,)).fetchall()
    progress = {p['module_id']: p for p in progress_rows}

    required_count = conn.execute('SELECT COUNT(*) FROM training_modules WHERE required = 1').fetchone()[0]
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
    module = conn.execute('SELECT * FROM training_modules WHERE id = ?', (module_id,)).fetchone()
    if not module:
        conn.close()
        return redirect('/training')

    questions = conn.execute('SELECT * FROM quiz_questions WHERE module_id = ?', (module_id,)).fetchall()
    p = conn.execute('SELECT * FROM module_progress WHERE trainee_id = ? AND module_id = ?',
                     (trainee_id, module_id)).fetchone()
    conn.close()

    video_html = youtube_embed(module['video_url']) if module['video_url'] else ''
    content_html = (module['content'] or '').replace('\n', '<br>')

    html = STYLE + trainee_nav() + f'<h1>{module["title"]}</h1>'
    if p and p['passed']:
        html += '<div class="success">✓ You have already passed this module. Feel free to review.</div>'

    if video_html:
        html += f'<h2>Training Video</h2>{video_html}'

    if content_html:
        html += f'<h2>Instructions</h2><div class="application">{content_html}</div>'

    if questions:
        html += f'<h2>Quiz ({len(questions)} questions)</h2>'
        html += '<p class="form-note">You must answer ALL questions correctly to pass. Take your time.</p>'
        html += f'<form method="POST" action="/training/module/{module_id}/submit">'
        for i, q in enumerate(questions, 1):
            html += f'<div class="quiz-question"><p>Q{i}: {q["question"]}</p>'
            for letter in ['a', 'b', 'c', 'd']:
                opt = q[f'option_{letter}']
                if opt:
                    html += f'<div class="radio-group"><label><input type="radio" name="q_{q["id"]}" value="{letter}" required> {opt.upper() if False else opt}</label></div>'
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
    questions = conn.execute('SELECT * FROM quiz_questions WHERE module_id = ?', (module_id,)).fetchall()

    if not questions:
        conn.close()
        return redirect(f'/training/module/{module_id}')

    correct = 0
    total = len(questions)
    wrong_qids = []
    for q in questions:
        answer = request.form.get(f'q_{q["id"]}', '')
        if answer == q['correct_answer']:
            correct += 1
        else:
            wrong_qids.append(q['id'])

    passed = (correct == total)  # 100% required

    # Upsert progress
    existing = conn.execute('SELECT * FROM module_progress WHERE trainee_id = ? AND module_id = ?',
                            (trainee_id, module_id)).fetchone()
    if existing:
        if passed:
            conn.execute('''UPDATE module_progress
                            SET passed = 1, attempts = attempts + 1,
                                completed_date = CURRENT_TIMESTAMP
                            WHERE id = ?''', (existing['id'],))
        else:
            conn.execute('UPDATE module_progress SET attempts = attempts + 1 WHERE id = ?',
                         (existing['id'],))
    else:
        conn.execute('''INSERT INTO module_progress (trainee_id, module_id, passed, attempts, completed_date)
                        VALUES (?, ?, ?, 1, ?)''',
                     (trainee_id, module_id, 1 if passed else 0,
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
            <p>You got {correct} out of {total} correct. You need 100% to pass this module.</p>
            <p>Review the material and try again — you can attempt as many times as you need.</p>
        </div>
        <p><a class="btn" href="/training/module/{module_id}">Review &amp; Retry</a></p>
        <p><a class="btn" href="/training">Back to My Training</a></p>
        '''
    return html


if __name__ == '__main__':
    # Render uses PORT env variable; locally use 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
