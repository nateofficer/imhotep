from flask import Flask, request, redirect, send_from_directory, session, url_for
import sqlite3
import os
import time
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
            FOREIGN KEY (job_id) REFERENCES jobs(id)
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
    form { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    input, textarea, select { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; font-size: 16px; }
    label { display: block; margin-top: 10px; font-weight: bold; color: #34495e; }
    .application { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .application.flagged { border-left: 5px solid #e74c3c; }
    .nav { margin-bottom: 20px; }
    .nav a { margin-right: 15px; color: #3498db; text-decoration: none; font-weight: bold; }
    .error { background: #ffe6e6; color: #c0392b; padding: 10px; border-radius: 5px; margin: 10px 0; }
    .admin-badge { background: #2ecc71; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; margin-left: 10px; }
    .flag-badge { background: #e74c3c; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; margin-left: 10px; font-weight: bold; }
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
</style>
'''


def public_nav():
    return '''
    <div class="nav">
        <a href="/">View Jobs</a>
        <a href="/login">Admin Login</a>
    </div>
    '''


def admin_nav():
    return '''
    <div class="nav">
        <a href="/">View Jobs</a>
        <a href="/applications">View Applications</a>
        <a href="/post-job">Post a Job</a>
        <a href="/logout">Logout</a>
        <span class="admin-badge">ADMIN</span>
    </div>
    '''


def get_nav():
    return admin_nav() if session.get('logged_in') else public_nav()


def yes_no(value):
    """Format a yes/no answer for display."""
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
            score = app_row['score'] if app_row['score'] is not None else 0
            score_html = f'<span class="score-badge {score_class(score)}">Score: {score}/100</span>'
            flagged_class = ' flagged' if app_row['flagged'] else ''

            tech_level = app_row['tech_level'] if app_row['tech_level'] is not None else 'Not answered'

            html += f'''
            <div class="application{flagged_class}">
                <h2>{app_row['first_name']} {app_row['last_name']} {score_html} {flag_html}</h2>
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

                <form method="POST" action="/delete/{app_row['id']}" onsubmit="return confirm('Delete this application?');" style="margin-top:10px; box-shadow:none; padding:0; background:none;">
                    <button class="btn btn-danger" type="submit">Delete</button>
                </form>
            </div>
            '''

    return html


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


@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form.get('phone', '')

        # Screening answers
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

        # Handle resume upload
        resume_filename = None
        if 'resume' in request.files:
            resume_file = request.files['resume']
            if resume_file and resume_file.filename:
                timestamp = str(int(time.time()))
                resume_filename = f"{timestamp}_resume_{resume_file.filename}"
                resume_file.save(os.path.join(UPLOAD_FOLDER, resume_filename))

        # Handle driver's license upload (required)
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


if __name__ == '__main__':
    # Render uses PORT env variable; locally use 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
