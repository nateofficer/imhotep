from flask import Flask, request, redirect, send_from_directory
import mysql.connector
import os
import time

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'NewPassword123!',
    'database': 'imhotep_db'
}

def get_db():
    return mysql.connector.connect(**db_config)

STYLE = """
<style>
    body { font-family: Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 0; }
    .header { background: #1a3a5c; color: white; padding: 20px 40px; }
    .header h1 { margin: 0; font-size: 28px; }
    .header p { margin: 5px 0 0 0; color: #b8d4e8; }
    .container { max-width: 900px; margin: 30px auto; padding: 0 20px; }
    .job-card { background: white; border-radius: 8px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .job-card h2 { color: #1a3a5c; margin-top: 0; }
    .dept { display: inline-block; background: #e8f0fa; color: #1a3a5c; padding: 5px 12px; border-radius: 20px; font-size: 14px; margin-bottom: 10px; }
    .btn { background: #1a3a5c; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; font-size: 15px; }
    .btn:hover { background: #2a5080; }
    .btn-green { background: #2e8b57; }
    .btn-green:hover { background: #3ca066; }
    form { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    form label { display: block; margin-top: 15px; font-weight: bold; color: #333; }
    form input[type=text], form input[type=email], form textarea { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ddd; border-radius: 5px; font-size: 15px; box-sizing: border-box; }
    form textarea { resize: vertical; }
    table { width: 100%; background: white; border-collapse: collapse; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    table th { background: #1a3a5c; color: white; padding: 12px; text-align: left; }
    table td { padding: 12px; border-bottom: 1px solid #eee; }
    table tr:last-child td { border-bottom: none; }
    .success { background: #d4edda; color: #155724; padding: 20px; border-radius: 8px; text-align: center; }
    a { color: #1a3a5c; }
</style>
"""

@app.route('/')
def show_jobs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs")
    jobs = cursor.fetchall()
    cursor.close()
    conn.close()

    html = STYLE
    html += "<div class='header'><h1>🏛️ IMHOTEP</h1><p>Current Job Openings at Casey's Cleaning</p></div>"
    html += "<div class='container'>"
    html += "<a href='/post-job' class='btn'>+ Post New Job (Admin)</a> "
    html += "<a href='/applications' class='btn btn-green'>View Applications</a><br><br>"

    for job in jobs:
        html += f"<div class='job-card'><h2>{job[1]}</h2>"
        html += f"<span class='dept'>{job[3]}</span>"
        html += f"<p>{job[2]}</p>"
        html += f"<a href='/apply/{job[0]}' class='btn'>Apply Now</a></div>"

    html += "</div>"
    return html

@app.route('/post-job', methods=['GET', 'POST'])
def post_job():
    if request.method == 'POST':
        title = request.form['title']
        department = request.form['department']
        description = request.form['description']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (job_title, job_description, department) VALUES (%s, %s, %s)",
            (title, description, department)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/')

    html = STYLE
    html += "<div class='header'><h1>Post a New Job</h1></div>"
    html += "<div class='container'>"
    html += """
    <form method='POST'>
        <label>Job Title</label>
        <input type='text' name='title' required>
        <label>Department</label>
        <input type='text' name='department' required>
        <label>Job Description</label>
        <textarea name='description' rows='6'></textarea>
        <br><br>
        <button type='submit' class='btn'>Post Job</button>
        <a href='/' class='btn btn-green'>Cancel</a>
    </form>
    """
    html += "</div>"
    return html

@app.route('/applications')
def view_applications():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.candidate_id, c.first_name, c.last_name, c.email, c.phone, j.job_title, a.application_date, c.resume_path
        FROM job_applications a
        JOIN candidates c ON a.candidate_id = c.candidate_id
        JOIN jobs j ON a.job_id = j.job_id
        ORDER BY a.application_date DESC
    """)
    applications = cursor.fetchall()
    cursor.close()
    conn.close()

    html = STYLE
    html += "<div class='header'><h1>Applications Received</h1></div>"
    html += "<div class='container'>"
    html += "<a href='/' class='btn'>← Back to Jobs</a><br><br>"
    html += "<table>"
    html += "<tr><th>Name</th><th>Email</th><th>Phone</th><th>Job</th><th>Resume</th><th>Date</th><th>Action</th></tr>"

    for app_row in applications:
        resume_link = f"<a href='/resume/{app_row[7]}'>View</a>" if app_row[7] else "None"
        html += f"<tr><td>{app_row[1]} {app_row[2]}</td><td>{app_row[3]}</td><td>{app_row[4]}</td><td>{app_row[5]}</td><td>{resume_link}</td><td>{app_row[6]}</td>"
        html += f"<td><a href='/delete/{app_row[0]}' onclick='return confirm(\"Delete this application?\")' style='color:red'>Delete</a></td></tr>"

    html += "</table></div>"
    return html

@app.route('/delete/<int:candidate_id>')
def delete_application(candidate_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job_applications WHERE candidate_id = %s", (candidate_id,))
    cursor.execute("DELETE FROM candidates WHERE candidate_id = %s", (candidate_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/applications')

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        cover_letter = request.form.get('cover_letter', '')

        resume_path = ''
        if 'resume' in request.files:
            resume = request.files['resume']
            if resume.filename:
                safe_name = resume.filename.replace(' ', '_')
                resume_filename = f"{int(time.time())}_{safe_name}"
                full_path = os.path.join(UPLOAD_FOLDER, resume_filename)
                resume.save(full_path)
                resume_path = resume_filename

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO candidates (first_name, last_name, email, phone, resume_path) VALUES (%s, %s, %s, %s, %s)",
            (first_name, last_name, email, phone, resume_path)
        )
        candidate_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO job_applications (candidate_id, job_id) VALUES (%s, %s)",
            (candidate_id, job_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        html = STYLE
        html += "<div class='header'><h1>🏛️ IMHOTEP</h1></div>"
        html += "<div class='container'><div class='success'>"
        html += "<h1>✓ Thank you for applying!</h1>"
        html += "<p>We have received your application and will contact you soon.</p>"
        html += "<a href='/' class='btn'>Back to Jobs</a>"
        html += "</div></div>"
        return html

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,))
    job = cursor.fetchone()
    cursor.close()
    conn.close()

    html = STYLE
    html += f"<div class='header'><h1>Apply for: {job[1]}</h1><p>{job[3]}</p></div>"
    html += "<div class='container'>"
    html += f"<div class='job-card'><p>{job[2]}</p></div>"
    html += """
    <form method='POST' enctype='multipart/form-data'>
        <label>First Name</label>
        <input type='text' name='first_name' required>
        <label>Last Name</label>
        <input type='text' name='last_name' required>
        <label>Email</label>
        <input type='email' name='email' required>
        <label>Phone</label>
        <input type='text' name='phone'>
        <label>Upload Resume (PDF, Word, etc.)</label>
        <input type='file' name='resume'>
        <label>Cover Letter</label>
        <textarea name='cover_letter' rows='6'></textarea>
        <br><br>
        <button type='submit' class='btn'>Submit Application</button>
        <a href='/' class='btn btn-green'>Cancel</a>
    </form>
    """
    html += "</div>"
    return html

@app.route('/resume/<filename>')
def download_resume(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
