from flask import Flask, request, redirect, send_from_directory, session, url_for
import sqlite3
import os
import time
from functools import wraps

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
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    ''')
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
    input, textarea { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; font-size: 16px; }
    label { display: block; margin-top: 10px; font-weight: bold; color: #34495e; }
    .application { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .nav { margin-bottom: 20px; }
    .nav a { margin-right: 15px; color: #3498db; text-decoration: none; font-weight: bold; }
    .error { background: #ffe6e6; color: #c0392b; padding: 10px; border-radius: 5px; margin: 10px 0; }
    .admin-badge { background: #2ecc71; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; margin-left: 10px; }
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
        ORDER BY candidates.applied_date DESC
    ''').fetchall()
    conn.close()

    html = STYLE + admin_nav() + '<h1>Job Applications</h1>'

    if not apps:
        html += '<p>No applications yet.</p>'
    else:
        for app_row in apps:
            resume_link = ''
            if app_row['resume_filename']:
                resume_link = f'<p><a class="btn" href="/resume/{app_row["resume_filename"]}" target="_blank">View Resume</a></p>'
            html += f'''
            <div class="application">
                <h2>{app_row['first_name']} {app_row['last_name']}</h2>
                <p><strong>Position:</strong> {app_row['job_title'] or 'N/A'}</p>
                <p><strong>Email:</strong> {app_row['email']}</p>
                <p><strong>Phone:</strong> {app_row['phone'] or 'Not provided'}</p>
                <p><strong>Applied:</strong> {app_row['applied_date']}</p>
                {resume_link}
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

        # Handle resume upload
        resume_filename = None
        if 'resume' in request.files:
            resume_file = request.files['resume']
            if resume_file and resume_file.filename:
                # Add timestamp to avoid filename collisions
                timestamp = str(int(time.time()))
                resume_filename = f"{timestamp}_{resume_file.filename}"
                resume_file.save(os.path.join(UPLOAD_FOLDER, resume_filename))

        conn.execute('''INSERT INTO candidates
                        (first_name, last_name, email, phone, resume_filename, job_id)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (first_name, last_name, email, phone, resume_filename, job_id))
        conn.commit()
        conn.close()

        return STYLE + public_nav() + '''
        <h1>Thank You!</h1>
        <p>Your application has been submitted successfully. We will be in touch soon.</p>
        <a class="btn" href="/">Back to Jobs</a>
        '''

    conn.close()

    if not job:
        return STYLE + public_nav() + '<h1>Job not found</h1><a href="/">Back</a>'

    return STYLE + public_nav() + f'''
    <h1>Apply: {job['title']}</h1>
    <form method="POST" enctype="multipart/form-data">
        <label>First Name:</label>
        <input type="text" name="first_name" required>
        <label>Last Name:</label>
        <input type="text" name="last_name" required>
        <label>Email:</label>
        <input type="email" name="email" required>
        <label>Phone:</label>
        <input type="tel" name="phone">
        <label>Resume (PDF, DOC, etc.):</label>
        <input type="file" name="resume">
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
