"""
Imhotep - Add Cloudinary File Upload to Document Library
----------------------------------------------------------
This script:
1. Adds Cloudinary import and config to app.py
2. Adds file_url column to documents table
3. Updates add/edit document routes to handle file uploads
4. Updates the document form template to support both upload and Drive link

Run from your imhotep folder:
    python add_cloudinary_upload.py
"""

import os
import sys

APP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

# ── Step 1: Add Cloudinary import ────────────────────────────────────────────

def patch_imports():
    with open(APP_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'cloudinary' in content:
        print("⚠️  Cloudinary already imported — skipping.")
        return content

    old = "from flask import Flask, render_template, request, redirect, send_from_directory, session, url_for"
    new = """from flask import Flask, render_template, request, redirect, send_from_directory, session, url_for
import cloudinary
import cloudinary.uploader"""

    if old not in content:
        print("❌ Could not find Flask import line.")
        sys.exit(1)

    content = content.replace(old, new)
    print("✅ Cloudinary import added.")
    return content


# ── Step 2: Add Cloudinary config after secret key ───────────────────────────

def patch_cloudinary_config(content):
    if 'cloudinary.config' in content:
        print("⚠️  Cloudinary config already present — skipping.")
        return content

    old = "app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours"
    new = """app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Cloudinary config
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)"""

    if old not in content:
        print("❌ Could not find session lifetime line for Cloudinary config insertion.")
        sys.exit(1)

    content = content.replace(old, new)
    print("✅ Cloudinary config added.")
    return content


# ── Step 3: Update add_document route to handle file upload ──────────────────

def patch_add_route(content):
    if 'cloudinary.uploader.upload' in content:
        print("⚠️  Cloudinary upload already in route — skipping.")
        return content

    old = """@app.route('/admin/documents/add', methods=['GET', 'POST'])
def admin_add_document():
    if not session.get('logged_in'):
        return redirect('/login')
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        doc_type = request.form.get('doc_type', 'signable')
        drive_link = request.form.get('drive_link', '').strip()
        description = request.form.get('description', '').strip()
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO documents (title, doc_type, drive_link, description) VALUES (%s, %s, %s, %s)",
            (title, doc_type, drive_link, description)
        )
        conn.commit()
        return redirect('/admin/documents')
    return render_template('admin_document_form.html', doc=None)"""

    new = """@app.route('/admin/documents/add', methods=['GET', 'POST'])
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
                resource_type='raw',
                folder='imhotep_docs',
                use_filename=True,
                unique_filename=True
            )
            file_url = upload_result.get('secure_url', '')
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO documents (title, doc_type, drive_link, file_url, description) VALUES (%s, %s, %s, %s, %s)",
            (title, doc_type, drive_link, file_url, description)
        )
        conn.commit()
        return redirect('/admin/documents')
    return render_template('admin_document_form.html', doc=None)"""

    if old not in content:
        print("❌ Could not find admin_add_document route.")
        sys.exit(1)

    content = content.replace(old, new)
    print("✅ Add document route updated with file upload.")
    return content


# ── Step 4: Update edit_document route ───────────────────────────────────────

def patch_edit_route(content):
    old = """    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        doc_type = request.form.get('doc_type', 'signable')
        drive_link = request.form.get('drive_link', '').strip()
        description = request.form.get('description', '').strip()
        active = 1 if request.form.get('active') else 0
        cur.execute(
            "UPDATE documents SET title=%s, doc_type=%s, drive_link=%s, description=%s, active=%s WHERE id=%s",
            (title, doc_type, drive_link, description, active, doc_id)
        )"""

    new = """    if request.method == 'POST':
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
                resource_type='raw',
                folder='imhotep_docs',
                use_filename=True,
                unique_filename=True
            )
            file_url = upload_result.get('secure_url', '')
        cur.execute(
            "UPDATE documents SET title=%s, doc_type=%s, drive_link=%s, file_url=%s, description=%s, active=%s WHERE id=%s",
            (title, doc_type, drive_link, file_url, description, active, doc_id)
        )"""

    if old not in content:
        print("❌ Could not find admin_edit_document route update section.")
        sys.exit(1)

    content = content.replace(old, new)
    print("✅ Edit document route updated with file upload.")
    return content


# ── Step 5: DB migration ──────────────────────────────────────────────────────

def run_migration():
    sys.path.insert(0, os.path.dirname(APP_PATH))
    from app import app, get_db
    with app.app_context():
        conn = get_db()
        cur = conn.cursor()
        # Add file_url column if it doesn't exist
        cur.execute("SHOW COLUMNS FROM documents LIKE 'file_url'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE documents ADD COLUMN file_url TEXT")
            conn.commit()
            print("✅ file_url column added to documents table.")
        else:
            print("⚠️  file_url column already exists — skipping.")


# ── Step 6: Update document form template ────────────────────────────────────

ADMIN_DOCUMENT_FORM = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Document Form — Imhotep</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&family=Lora:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --sand: #FAF7F2; --cream: #FFF9F0; --warm-brown: #5C3D2E;
    --terracotta: #C4714A; --sage: #7A9E7E; --text: #2E1F16;
    --text-muted: #7A6358; --border: #E8DDD5; --white: #FFFFFF;
    --shadow: 0 2px 12px rgba(92,61,46,0.08);
  }
  body { font-family: 'Nunito', sans-serif; background: var(--sand); color: var(--text); }
  nav {
    background: var(--warm-brown); padding: 0 32px; height: 56px;
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 100;
  }
  .navbar-brand { font-family: 'Lora', serif; font-size: 20px; color: #FFF9F0; font-weight: 600; text-decoration: none; }
  .navbar-brand span { color: #D4A843; }
  .navbar-links { display: flex; gap: 4px; }
  .navbar-links a { font-size: 13px; font-weight: 700; color: rgba(255,249,240,0.72); text-decoration: none; padding: 6px 12px; border-radius: 6px; }
  .navbar-links a:hover { background: rgba(255,255,255,0.1); color: #FFF9F0; }
  .main { max-width: 640px; margin: 32px auto; padding: 0 24px 60px; }
  .page-title { font-family: 'Lora', serif; font-size: 24px; font-weight: 600; color: var(--warm-brown); border-bottom: 2px solid var(--border); padding-bottom: 12px; margin-bottom: 24px; }
  .card { background: var(--white); border-radius: 14px; border: 1px solid var(--border); box-shadow: var(--shadow); padding: 30px; }
  .form-group { margin-bottom: 20px; }
  label { display: block; font-weight: 700; font-size: 14px; color: var(--text); margin-bottom: 6px; }
  input[type=text], input[type=url], input[type=file], textarea, select {
    width: 100%; padding: 10px 14px; border: 1.5px solid var(--border);
    border-radius: 8px; font-family: 'Nunito', sans-serif; font-size: 14px;
    color: var(--text); background: var(--cream); transition: border 0.2s;
  }
  input[type=file] { padding: 8px; cursor: pointer; }
  input:focus, textarea:focus, select:focus { outline: none; border-color: var(--terracotta); }
  .divider { display: flex; align-items: center; gap: 12px; margin: 20px 0; color: var(--text-muted); font-size: 13px; font-weight: 700; }
  .divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: var(--border); }
  .btn { font-family: 'Nunito', sans-serif; font-size: 14px; font-weight: 800; padding: 10px 24px; border-radius: 8px; background: var(--terracotta); border: none; color: white; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: 8px; transition: all 0.2s; }
  .btn:hover { background: var(--warm-brown); }
  .btn-muted { background: #95a5a6; }
  .btn-muted:hover { background: #7f8c8d; }
  .existing-file { background: var(--sand); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; font-size: 13px; color: var(--text-muted); margin-top: 6px; }
  .existing-file a { color: var(--terracotta); font-weight: 700; }
</style>
</head>
<body>
<nav>
  <a href="/" class="navbar-brand">Casey\'s<span>Cleaning</span></a>
  <div class="navbar-links">
    <a href="/applications">Applications</a>
    <a href="/trainees">Trainees</a>
    <a href="/onboarding-forms">Onboarding</a>
    <a href="/admin/documents">Documents</a>
    <a href="/logout">Logout</a>
  </div>
</nav>
<div class="main">
  <h1 class="page-title">{{ \'Edit Document\' if doc else \'Add Document\' }}</h1>
  <div class="card">
    <form method="POST" enctype="multipart/form-data">

      <div class="form-group">
        <label>Document Title</label>
        <input type="text" name="title" value="{{ doc.title if doc else \'\' }}" required>
      </div>

      <div class="form-group">
        <label>Document Type</label>
        <select name="doc_type">
          <option value="signable" {{ \'selected\' if doc and doc.doc_type == \'signable\' }}>
            Signable — trainee reviews and signs in app
          </option>
          <option value="admin_verified" {{ \'selected\' if doc and doc.doc_type == \'admin_verified\' }}>
            Admin Verified — background check, ID verification, etc.
          </option>
        </select>
      </div>

      <div class="form-group">
        <label>Upload PDF from your computer</label>
        <input type="file" name="document_file" accept=".pdf,.doc,.docx">
        {% if doc and doc.file_url %}
        <div class="existing-file">
          Current file: <a href="{{ doc.file_url }}" target="_blank">View uploaded file</a>
          <input type="hidden" name="existing_file_url" value="{{ doc.file_url }}">
        </div>
        {% endif %}
      </div>

      <div class="divider">OR</div>

      <div class="form-group">
        <label>Google Drive Link</label>
        <input type="url" name="drive_link" value="{{ doc.drive_link if doc else \'\' }}"
               placeholder="https://drive.google.com/...">
      </div>

      <div class="form-group">
        <label>Description <span style="font-weight:400;color:var(--text-muted);">(optional)</span></label>
        <textarea name="description" rows="3">{{ doc.description if doc else \'\' }}</textarea>
      </div>

      {% if doc %}
      <div class="form-group">
        <label style="display:flex;align-items:center;gap:10px;cursor:pointer;">
          <input type="checkbox" name="active" {{ \'checked\' if doc.active }}
                 style="width:18px;height:18px;margin:0;">
          Active (visible for assignment)
        </label>
      </div>
      {% endif %}

      <div style="display:flex;gap:12px;margin-top:24px;">
        <button type="submit" class="btn">Save Document</button>
        <a href="/admin/documents" class="btn btn-muted">Cancel</a>
      </div>

    </form>
  </div>
</div>
</body>
</html>'''


def write_template():
    path = os.path.join(TEMPLATES_DIR, 'admin_document_form.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(ADMIN_DOCUMENT_FORM)
    print("✅ admin_document_form.html updated with file upload.")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("\n🚀 Imhotep - Add Cloudinary File Upload")
    print("=" * 40)

    print("\n[1/5] Running DB migration...")
    run_migration()

    print("\n[2/5] Patching imports...")
    content = patch_imports()

    print("\n[3/5] Adding Cloudinary config...")
    content = patch_cloudinary_config(content)

    print("\n[4/5] Updating routes...")
    content = patch_add_route(content)
    content = patch_edit_route(content)

    with open(APP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print("\n[5/5] Updating document form template...")
    write_template()

    print("\n" + "=" * 40)
    print("✅ Patch complete!")
    print("\nNext steps:")
    print("  git add -A")
    print("  git commit -m 'Add Cloudinary file upload to document library'")
    print("  git push")
