"""
Imhotep - Document Library Patch
Casey's Cleaning Company
--------------------------
This script:
1. Creates the `documents` table (document library)
2. Creates the `trainee_documents` table (per-trainee assignment + tracking)
3. Adds all required Flask routes to app.py
4. Creates HTML templates for document library admin and trainee view

Run from your imhotep folder:
    python doc_library_patch.py
"""

import os
import sys

APP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

# ─────────────────────────────────────────────
# STEP 1: Create new DB tables
# ─────────────────────────────────────────────

DB_MIGRATION = """
# ── DB Migration ──────────────────────────────────────────────────────────────
def run_doc_library_migration():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(\"\"\"
        CREATE TABLE IF NOT EXISTS documents (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            doc_type ENUM('signable', 'admin_verified') NOT NULL DEFAULT 'signable',
            drive_link TEXT,
            description TEXT,
            active INT DEFAULT 1,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    \"\"\")

    cur.execute(\"\"\"
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
    \"\"\")

    conn.commit()
    print("✅ documents and trainee_documents tables created.")
# ── End DB Migration ──────────────────────────────────────────────────────────
"""

# ─────────────────────────────────────────────
# STEP 2: Flask Routes
# ─────────────────────────────────────────────

ROUTES = """
# ── Document Library Routes ───────────────────────────────────────────────────

@app.route('/admin/documents')
def admin_documents():
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents ORDER BY title")
    docs = cur.fetchall()
    return render_template('admin_documents.html', documents=docs)


@app.route('/admin/documents/add', methods=['GET', 'POST'])
def admin_add_document():
    if not session.get('logged_in') or session.get('role') != 'admin':
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
    return render_template('admin_document_form.html', doc=None)


@app.route('/admin/documents/edit/<int:doc_id>', methods=['GET', 'POST'])
def admin_edit_document(doc_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        doc_type = request.form.get('doc_type', 'signable')
        drive_link = request.form.get('drive_link', '').strip()
        description = request.form.get('description', '').strip()
        active = 1 if request.form.get('active') else 0
        cur.execute(
            "UPDATE documents SET title=%s, doc_type=%s, drive_link=%s, description=%s, active=%s WHERE id=%s",
            (title, doc_type, drive_link, description, active, doc_id)
        )
        conn.commit()
        return redirect('/admin/documents')
    cur.execute("SELECT * FROM documents WHERE id=%s", (doc_id,))
    doc = cur.fetchone()
    return render_template('admin_document_form.html', doc=doc)


@app.route('/admin/documents/assign/<int:trainee_id>', methods=['GET', 'POST'])
def admin_assign_documents(trainee_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
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
        return redirect(f'/admin/trainees/{trainee_id}')
    cur.execute("SELECT * FROM trainees WHERE id=%s", (trainee_id,))
    trainee = cur.fetchone()
    cur.execute("SELECT * FROM documents WHERE active=1 ORDER BY title")
    all_docs = cur.fetchall()
    cur.execute("SELECT document_id FROM trainee_documents WHERE trainee_id=%s", (trainee_id,))
    assigned_ids = {row['document_id'] for row in cur.fetchall()}
    return render_template('admin_assign_documents.html', trainee=trainee, documents=all_docs, assigned_ids=assigned_ids)


@app.route('/admin/documents/verify/<int:assignment_id>', methods=['POST'])
def admin_verify_document(assignment_id):
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    cur = conn.cursor()
    verified_by = session.get('username', 'Admin')
    cur.execute(
        "UPDATE trainee_documents SET status='verified', verified_by=%s, verified_date=NOW() WHERE id=%s",
        (verified_by, assignment_id)
    )
    conn.commit()
    cur.execute("SELECT trainee_id FROM trainee_documents WHERE id=%s", (assignment_id,))
    row = cur.fetchone()
    return redirect(f"/admin/trainees/{row['trainee_id']}")


@app.route('/trainee/documents')
def trainee_documents():
    if not session.get('logged_in'):
        return redirect('/login')
    trainee_id = session.get('trainee_id')
    conn = get_db()
    cur = conn.cursor()
    cur.execute(\"\"\"
        SELECT td.id as assignment_id, d.title, d.doc_type, d.drive_link, d.description,
               td.status, td.signed_date, td.verified_date, td.verified_by
        FROM trainee_documents td
        JOIN documents d ON td.document_id = d.id
        WHERE td.trainee_id = %s
        ORDER BY d.title
    \"\"\", (trainee_id,))
    docs = cur.fetchall()
    return render_template('trainee_documents.html', documents=docs)


@app.route('/trainee/documents/sign/<int:assignment_id>', methods=['GET', 'POST'])
def trainee_sign_document(assignment_id):
    if not session.get('logged_in'):
        return redirect('/login')
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
    cur.execute(\"\"\"
        SELECT td.*, d.title, d.drive_link, d.description
        FROM trainee_documents td
        JOIN documents d ON td.document_id = d.id
        WHERE td.id=%s
    \"\"\", (assignment_id,))
    assignment = cur.fetchone()
    return render_template('trainee_sign_document.html', assignment=assignment)

# ── End Document Library Routes ───────────────────────────────────────────────
"""

# ─────────────────────────────────────────────
# STEP 3: HTML Templates
# ─────────────────────────────────────────────

TEMPLATE_ADMIN_DOCUMENTS = """{% extends "base.html" %}
{% block content %}
<div style="max-width:900px;margin:0 auto;padding:20px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
    <h1 style="color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;">Document Library</h1>
    <a href="/admin/documents/add" class="btn">+ Add Document</a>
  </div>

  {% if documents %}
  <table style="width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
    <thead>
      <tr style="background:#3498db;color:white;">
        <th style="padding:12px 16px;text-align:left;">Title</th>
        <th style="padding:12px 16px;text-align:left;">Type</th>
        <th style="padding:12px 16px;text-align:left;">Status</th>
        <th style="padding:12px 16px;text-align:left;">Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for doc in documents %}
      <tr style="border-bottom:1px solid #eee;">
        <td style="padding:12px 16px;">{{ doc.title }}</td>
        <td style="padding:12px 16px;">
          {% if doc.doc_type == 'signable' %}
            <span style="background:#e8f5e9;color:#2e7d32;padding:3px 10px;border-radius:12px;font-size:13px;">Signable</span>
          {% else %}
            <span style="background:#fff3e0;color:#e65100;padding:3px 10px;border-radius:12px;font-size:13px;">Admin Verified</span>
          {% endif %}
        </td>
        <td style="padding:12px 16px;">
          {% if doc.active %}
            <span style="color:#27ae60;">● Active</span>
          {% else %}
            <span style="color:#e74c3c;">● Inactive</span>
          {% endif %}
        </td>
        <td style="padding:12px 16px;">
          <a href="/admin/documents/edit/{{ doc.id }}" style="color:#3498db;margin-right:12px;">Edit</a>
          {% if doc.drive_link %}
          <a href="{{ doc.drive_link }}" target="_blank" style="color:#27ae60;">View Doc</a>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div style="text-align:center;padding:60px;background:white;border-radius:8px;color:#888;">
    <p style="font-size:18px;">No documents yet.</p>
    <a href="/admin/documents/add" class="btn" style="margin-top:12px;">Add Your First Document</a>
  </div>
  {% endif %}
</div>
{% endblock %}
"""

TEMPLATE_ADMIN_DOCUMENT_FORM = """{% extends "base.html" %}
{% block content %}
<div style="max-width:600px;margin:0 auto;padding:20px;">
  <h1 style="color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;">
    {{ 'Edit Document' if doc else 'Add Document' }}
  </h1>
  <form method="POST" style="background:white;padding:30px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);margin-top:20px;">
    <div style="margin-bottom:18px;">
      <label style="display:block;font-weight:bold;margin-bottom:6px;">Document Title</label>
      <input type="text" name="title" value="{{ doc.title if doc else '' }}" required
             style="width:100%;padding:10px;border:1px solid #ddd;border-radius:4px;box-sizing:border-box;">
    </div>

    <div style="margin-bottom:18px;">
      <label style="display:block;font-weight:bold;margin-bottom:6px;">Document Type</label>
      <select name="doc_type" style="width:100%;padding:10px;border:1px solid #ddd;border-radius:4px;">
        <option value="signable" {{ 'selected' if doc and doc.doc_type == 'signable' }}>Signable (trainee signs in app)</option>
        <option value="admin_verified" {{ 'selected' if doc and doc.doc_type == 'admin_verified' }}>Admin Verified (background check, ID, etc.)</option>
      </select>
    </div>

    <div style="margin-bottom:18px;">
      <label style="display:block;font-weight:bold;margin-bottom:6px;">Google Drive Link</label>
      <input type="url" name="drive_link" value="{{ doc.drive_link if doc else '' }}"
             placeholder="https://drive.google.com/..."
             style="width:100%;padding:10px;border:1px solid #ddd;border-radius:4px;box-sizing:border-box;">
    </div>

    <div style="margin-bottom:18px;">
      <label style="display:block;font-weight:bold;margin-bottom:6px;">Description (optional)</label>
      <textarea name="description" rows="3"
                style="width:100%;padding:10px;border:1px solid #ddd;border-radius:4px;box-sizing:border-box;">{{ doc.description if doc else '' }}</textarea>
    </div>

    {% if doc %}
    <div style="margin-bottom:18px;">
      <label style="display:flex;align-items:center;gap:8px;font-weight:bold;">
        <input type="checkbox" name="active" {{ 'checked' if doc.active }}> Active
      </label>
    </div>
    {% endif %}

    <div style="display:flex;gap:12px;margin-top:24px;">
      <button type="submit" class="btn">Save Document</button>
      <a href="/admin/documents" class="btn" style="background:#95a5a6;">Cancel</a>
    </div>
  </form>
</div>
{% endblock %}
"""

TEMPLATE_ADMIN_ASSIGN = """{% extends "base.html" %}
{% block content %}
<div style="max-width:600px;margin:0 auto;padding:20px;">
  <h1 style="color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;">
    Assign Documents — {{ trainee.first_name }} {{ trainee.last_name }}
  </h1>
  <form method="POST" style="background:white;padding:30px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);margin-top:20px;">
    {% if documents %}
      {% for doc in documents %}
      <label style="display:flex;align-items:center;gap:12px;padding:14px;border:1px solid #eee;border-radius:6px;margin-bottom:10px;cursor:pointer;">
        <input type="checkbox" name="document_ids" value="{{ doc.id }}"
               {{ 'checked' if doc.id in assigned_ids }}
               style="width:18px;height:18px;">
        <div>
          <div style="font-weight:bold;">{{ doc.title }}</div>
          <div style="font-size:13px;color:#888;">
            {% if doc.doc_type == 'signable' %}Trainee signs in app{% else %}Admin verified{% endif %}
          </div>
        </div>
      </label>
      {% endfor %}
    {% else %}
      <p style="color:#888;">No documents in library yet. <a href="/admin/documents/add">Add one first.</a></p>
    {% endif %}

    <div style="display:flex;gap:12px;margin-top:24px;">
      <button type="submit" class="btn">Save Assignments</button>
      <a href="/admin/trainees/{{ trainee.id }}" class="btn" style="background:#95a5a6;">Cancel</a>
    </div>
  </form>
</div>
{% endblock %}
"""

TEMPLATE_TRAINEE_DOCUMENTS = """{% extends "base.html" %}
{% block content %}
<div style="max-width:800px;margin:0 auto;padding:20px;">
  <h1 style="color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;">My Documents</h1>

  {% if documents %}
    {% for doc in documents %}
    <div style="background:white;border-radius:8px;padding:20px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.08);display:flex;justify-content:space-between;align-items:center;">
      <div>
        <div style="font-size:18px;font-weight:bold;color:#2c3e50;">{{ doc.title }}</div>
        {% if doc.description %}
        <div style="color:#888;font-size:14px;margin-top:4px;">{{ doc.description }}</div>
        {% endif %}
        <div style="margin-top:8px;">
          {% if doc.status == 'signed' %}
            <span style="background:#e8f5e9;color:#2e7d32;padding:4px 12px;border-radius:12px;font-size:13px;">✅ Signed {{ doc.signed_date.strftime('%b %d, %Y') if doc.signed_date }}</span>
          {% elif doc.status == 'verified' %}
            <span style="background:#e3f2fd;color:#1565c0;padding:4px 12px;border-radius:12px;font-size:13px;">✅ Verified by {{ doc.verified_by }}</span>
          {% else %}
            <span style="background:#fff3e0;color:#e65100;padding:4px 12px;border-radius:12px;font-size:13px;">⏳ Action Required</span>
          {% endif %}
        </div>
      </div>
      <div style="display:flex;gap:10px;align-items:center;">
        {% if doc.drive_link %}
        <a href="{{ doc.drive_link }}" target="_blank" class="btn" style="background:#27ae60;">View</a>
        {% endif %}
        {% if doc.doc_type == 'signable' and doc.status == 'pending' %}
        <a href="/trainee/documents/sign/{{ doc.assignment_id }}" class="btn">Sign</a>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  {% else %}
  <div style="text-align:center;padding:60px;background:white;border-radius:8px;color:#888;">
    <p>No documents assigned yet.</p>
  </div>
  {% endif %}
</div>
{% endblock %}
"""

TEMPLATE_TRAINEE_SIGN = """{% extends "base.html" %}
{% block content %}
<div style="max-width:700px;margin:0 auto;padding:20px;">
  <h1 style="color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;">Sign: {{ assignment.title }}</h1>

  {% if assignment.drive_link %}
  <div style="margin-bottom:24px;">
    <a href="{{ assignment.drive_link }}" target="_blank" class="btn" style="background:#27ae60;">
      📄 View Document Before Signing
    </a>
  </div>
  {% endif %}

  {% if assignment.description %}
  <p style="color:#555;margin-bottom:20px;">{{ assignment.description }}</p>
  {% endif %}

  <div style="background:white;padding:30px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
    <p style="font-weight:bold;margin-bottom:12px;">Sign below to confirm you have read and agree to this document:</p>
    <canvas id="signatureCanvas" width="600" height="200"
            style="border:2px solid #ddd;border-radius:4px;cursor:crosshair;touch-action:none;width:100%;"></canvas>
    <div style="margin-top:10px;display:flex;gap:10px;">
      <button onclick="clearSig()" class="btn" style="background:#95a5a6;">Clear</button>
    </div>

    <form method="POST" style="margin-top:20px;">
      <input type="hidden" name="signature_data" id="signatureData">
      <button type="submit" onclick="return captureSignature()" class="btn" style="width:100%;padding:14px;font-size:16px;">
        Submit Signature
      </button>
    </form>
  </div>
</div>

<script>
const canvas = document.getElementById('signatureCanvas');
const ctx = canvas.getContext('2d');
let drawing = false;

function getPos(e) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  if (e.touches) {
    return { x: (e.touches[0].clientX - rect.left) * scaleX, y: (e.touches[0].clientY - rect.top) * scaleY };
  }
  return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY };
}

canvas.addEventListener('mousedown', e => { drawing = true; ctx.beginPath(); const p = getPos(e); ctx.moveTo(p.x, p.y); });
canvas.addEventListener('mousemove', e => { if (!drawing) return; const p = getPos(e); ctx.lineTo(p.x, p.y); ctx.strokeStyle = '#2c3e50'; ctx.lineWidth = 2; ctx.stroke(); });
canvas.addEventListener('mouseup', () => drawing = false);
canvas.addEventListener('touchstart', e => { e.preventDefault(); drawing = true; ctx.beginPath(); const p = getPos(e); ctx.moveTo(p.x, p.y); });
canvas.addEventListener('touchmove', e => { e.preventDefault(); if (!drawing) return; const p = getPos(e); ctx.lineTo(p.x, p.y); ctx.strokeStyle = '#2c3e50'; ctx.lineWidth = 2; ctx.stroke(); });
canvas.addEventListener('touchend', () => drawing = false);

function clearSig() { ctx.clearRect(0, 0, canvas.width, canvas.height); }
function captureSignature() {
  document.getElementById('signatureData').value = canvas.toDataURL();
  return true;
}
</script>
{% endblock %}
"""

# ─────────────────────────────────────────────
# STEP 4: Write everything
# ─────────────────────────────────────────────

def write_templates():
    templates = {
        'admin_documents.html': TEMPLATE_ADMIN_DOCUMENTS,
        'admin_document_form.html': TEMPLATE_ADMIN_DOCUMENT_FORM,
        'admin_assign_documents.html': TEMPLATE_ADMIN_ASSIGN,
        'trainee_documents.html': TEMPLATE_TRAINEE_DOCUMENTS,
        'trainee_sign_document.html': TEMPLATE_TRAINEE_SIGN,
    }
    for filename, content in templates.items():
        path = os.path.join(TEMPLATES_DIR, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content.strip())
        print(f"✅ Template written: {filename}")


def patch_app():
    with open(APP_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'run_doc_library_migration' in content:
        print("⚠️  Migration already patched in app.py — skipping.")
    else:
        # Insert migration function before first route (before @app.route)
        insert_point = content.find('\n@app.route')
        if insert_point == -1:
            print("❌ Could not find route insertion point in app.py")
            sys.exit(1)
        content = content[:insert_point] + '\n' + DB_MIGRATION + content[insert_point:]
        print("✅ Migration function added to app.py")

    if 'admin_documents' in content:
        print("⚠️  Document routes already patched in app.py — skipping.")
    else:
        content = content + '\n' + ROUTES
        print("✅ Document library routes added to app.py")

    with open(APP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)


def run_migration():
    sys.path.insert(0, os.path.dirname(APP_PATH))
    from app import app, get_db
    with app.app_context():
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
        print("✅ Database tables created successfully.")


if __name__ == '__main__':
    print("\n🚀 Imhotep Document Library Patch")
    print("=" * 40)

    print("\n[1/3] Running database migration...")
    run_migration()

    print("\n[2/3] Patching app.py...")
    patch_app()

    print("\n[3/3] Writing HTML templates...")
    write_templates()

    print("\n" + "=" * 40)
    print("✅ Patch complete!")
    print("\nNext steps:")
    print("  1. git add -A")
    print("  2. git commit -m 'Add document library with per-trainee assignment'")
    print("  3. git push")
    print("\nNew pages live after deploy:")
    print("  /admin/documents         — Document library")
    print("  /admin/documents/add     — Add a document")
    print("  /admin/documents/assign/<trainee_id>  — Assign docs to trainee")
    print("  /trainee/documents       — Trainee's document list")
