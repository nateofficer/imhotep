from flask import Flask, request, redirect, send_from_directory, session, url_for
import pymysql
import pymysql.cursors
import os
import time
import random
import string
import json
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Secret key for sessions
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')

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

    conn.commit()
    conn.close()


# Initialize database on startup
init_db()


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

@app.route('/')
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
    cursor = conn.cursor()
    cursor.execute('''
        SELECT candidates.*, jobs.title as job_title
        FROM candidates
        LEFT JOIN jobs ON candidates.job_id = jobs.id
        ORDER BY candidates.flagged ASC, candidates.score DESC, candidates.applied_date DESC
    ''')
    apps = cursor.fetchall()
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
    cursor.execute('UPDATE candidates SET hired = 1 WHERE id = %s', (candidate_id,))
    trainee_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return redirect(f'/trainee/{trainee_id}')


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
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM trainees WHERE LOWER(email) = %s AND access_code = %s',
            (email, code)
        )
        trainee = cursor.fetchone()
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
        return redirect('/training')

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
        html += '<p class="form-note">You must answer ALL questions correctly to pass. Take your time.</p>'
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

    passed = (correct == total)

    cursor.execute('SELECT * FROM module_progress WHERE trainee_id = %s AND module_id = %s',
                   (trainee_id, module_id))
    existing = cursor.fetchone()

    if existing:
        if passed:
            cursor.execute('''UPDATE module_progress
                              SET passed = 1, attempts = attempts + 1, completed_date = NOW()
                              WHERE id = %s''', (existing['id'],))
        else:
            cursor.execute('UPDATE module_progress SET attempts = attempts + 1 WHERE id = %s',
                           (existing['id'],))
    else:
        cursor.execute('''INSERT INTO module_progress (trainee_id, module_id, passed, attempts, completed_date)
                          VALUES (%s, %s, %s, 1, %s)''',
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
