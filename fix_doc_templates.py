"""
Imhotep - Fix Document Library Templates
-----------------------------------------
Replaces the 5 new templates that used base.html
with proper standalone HTML matching your existing design system.

Run from your imhotep folder:
    python fix_doc_templates.py
"""

import os

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

# ── Shared header/styles ──────────────────────────────────────────────────────

def make_page(title, nav_links, content):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Imhotep</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&family=Lora:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --sand: #FAF7F2; --cream: #FFF9F0; --warm-brown: #5C3D2E;
    --terracotta: #C4714A; --terra-light: #E8957A; --sage: #7A9E7E;
    --sage-light: #B5CEB8; --gold: #D4A843; --text: #2E1F16;
    --text-muted: #7A6358; --border: #E8DDD5; --white: #FFFFFF;
    --shadow: 0 2px 12px rgba(92,61,46,0.08);
    --shadow-md: 0 4px 24px rgba(92,61,46,0.12);
  }}
  body {{ font-family: 'Nunito', sans-serif; background: var(--sand); color: var(--text); }}
  nav {{
    background: var(--warm-brown); padding: 0 32px; height: 56px;
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 100;
  }}
  .navbar-brand {{
    font-family: 'Lora', serif; font-size: 20px; color: var(--cream);
    font-weight: 600; letter-spacing: 0.5px; text-decoration: none;
  }}
  .navbar-brand span {{ color: var(--gold); }}
  .navbar-links {{ display: flex; align-items: center; gap: 4px; }}
  .navbar-links a {{
    font-size: 13px; font-weight: 700; color: rgba(255,249,240,0.72);
    text-decoration: none; padding: 6px 12px; border-radius: 6px;
    transition: background 0.2s, color 0.2s;
  }}
  .navbar-links a:hover {{ background: rgba(255,255,255,0.1); color: var(--cream); }}
  .main {{ max-width: 860px; margin: 32px auto; padding: 0 24px 60px; }}
  .page-title {{
    font-family: 'Lora', serif; font-size: 24px; font-weight: 600;
    color: var(--warm-brown); border-bottom: 2px solid var(--border);
    padding-bottom: 12px; margin-bottom: 24px;
  }}
  .card {{
    background: var(--white); border-radius: 14px; border: 1px solid var(--border);
    box-shadow: var(--shadow); overflow: hidden; margin-bottom: 16px;
  }}
  .btn {{
    font-family: 'Nunito', sans-serif; font-size: 14px; font-weight: 800;
    padding: 10px 24px; border-radius: 8px; background: var(--terracotta);
    border: none; color: white; cursor: pointer; text-decoration: none;
    display: inline-flex; align-items: center; gap: 8px; transition: all 0.2s;
  }}
  .btn:hover {{ background: var(--warm-brown); }}
  .btn-sage {{ background: var(--sage); }}
  .btn-sage:hover {{ background: #5a7e5e; }}
  .btn-muted {{ background: #95a5a6; }}
  .btn-muted:hover {{ background: #7f8c8d; }}
  label {{ font-weight: 700; font-size: 14px; color: var(--text); }}
  input[type=text], input[type=url], textarea, select {{
    width: 100%; padding: 10px 14px; border: 1.5px solid var(--border);
    border-radius: 8px; font-family: 'Nunito', sans-serif; font-size: 14px;
    color: var(--text); background: var(--cream); margin-top: 6px;
    transition: border 0.2s;
  }}
  input:focus, textarea:focus, select:focus {{
    outline: none; border-color: var(--terracotta);
  }}
  .form-group {{ margin-bottom: 18px; }}
  .badge {{
    display: inline-block; padding: 3px 12px; border-radius: 12px;
    font-size: 12px; font-weight: 700;
  }}
  .badge-green {{ background: #e8f5e9; color: #2e7d32; }}
  .badge-orange {{ background: #fff3e0; color: #e65100; }}
  .badge-blue {{ background: #e3f2fd; color: #1565c0; }}
  .badge-red {{ background: #fce4ec; color: #c62828; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: var(--warm-brown); color: var(--cream); padding: 12px 16px; text-align: left; font-size: 13px; }}
  td {{ padding: 12px 16px; border-bottom: 1px solid var(--border); font-size: 14px; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: var(--sand); }}
  .empty-state {{ text-align: center; padding: 60px 20px; color: var(--text-muted); }}
  .empty-state p {{ font-size: 16px; margin-bottom: 16px; }}
</style>
</head>
<body>
<nav>
  <a href="/" class="navbar-brand">Casey's<span>Cleaning</span></a>
  <div class="navbar-links">
    {nav_links}
  </div>
</nav>
<div class="main">
{content}
</div>
</body>
</html>"""

ADMIN_NAV = """<a href="/applications">Applications</a>
    <a href="/trainees">Trainees</a>
    <a href="/onboarding-forms">Onboarding</a>
    <a href="/admin/documents">Documents</a>
    <a href="/logout">Logout</a>"""

TRAINEE_NAV = """<a href="/onboarding">Onboarding</a>
    <a href="/trainee/documents">My Documents</a>
    <a href="/trainee-logout">Logout</a>"""

# ── Template: admin_documents.html ───────────────────────────────────────────

ADMIN_DOCUMENTS = make_page("Document Library", ADMIN_NAV, """
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
  <h1 class="page-title" style="border:none;margin:0;">Document Library</h1>
  <a href="/admin/documents/add" class="btn">+ Add Document</a>
</div>

{% if documents %}
<div class="card">
  <table>
    <thead>
      <tr>
        <th>Title</th>
        <th>Type</th>
        <th>Status</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for doc in documents %}
      <tr>
        <td><strong>{{ doc.title }}</strong></td>
        <td>
          {% if doc.doc_type == 'signable' %}
            <span class="badge badge-green">Signable</span>
          {% else %}
            <span class="badge badge-orange">Admin Verified</span>
          {% endif %}
        </td>
        <td>
          {% if doc.active %}
            <span style="color:#27ae60;">&#9679; Active</span>
          {% else %}
            <span style="color:#e74c3c;">&#9679; Inactive</span>
          {% endif %}
        </td>
        <td style="display:flex;gap:12px;align-items:center;">
          <a href="/admin/documents/edit/{{ doc.id }}" style="color:var(--terracotta);font-weight:700;">Edit</a>
          {% if doc.drive_link %}
          <a href="{{ doc.drive_link }}" target="_blank" style="color:var(--sage);font-weight:700;">View</a>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% else %}
<div class="card">
  <div class="empty-state">
    <p>No documents in your library yet.</p>
    <a href="/admin/documents/add" class="btn">Add Your First Document</a>
  </div>
</div>
{% endif %}
""")

# ── Template: admin_document_form.html ───────────────────────────────────────

ADMIN_DOCUMENT_FORM = make_page("{{ 'Edit' if doc else 'Add' }} Document", ADMIN_NAV, """
<h1 class="page-title">{{ 'Edit Document' if doc else 'Add Document' }}</h1>

<div class="card" style="padding:30px;">
  <form method="POST">
    <div class="form-group">
      <label>Document Title</label>
      <input type="text" name="title" value="{{ doc.title if doc else '' }}" required>
    </div>

    <div class="form-group">
      <label>Document Type</label>
      <select name="doc_type">
        <option value="signable" {{ 'selected' if doc and doc.doc_type == 'signable' }}>
          Signable — trainee reviews and signs in app
        </option>
        <option value="admin_verified" {{ 'selected' if doc and doc.doc_type == 'admin_verified' }}>
          Admin Verified — background check, ID verification, etc.
        </option>
      </select>
    </div>

    <div class="form-group">
      <label>Google Drive Link</label>
      <input type="url" name="drive_link" value="{{ doc.drive_link if doc else '' }}"
             placeholder="https://drive.google.com/...">
    </div>

    <div class="form-group">
      <label>Description <span style="font-weight:400;color:var(--text-muted);">(optional)</span></label>
      <textarea name="description" rows="3">{{ doc.description if doc else '' }}</textarea>
    </div>

    {% if doc %}
    <div class="form-group">
      <label style="display:flex;align-items:center;gap:10px;cursor:pointer;">
        <input type="checkbox" name="active" {{ 'checked' if doc.active }}
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
""")

# ── Template: admin_assign_documents.html ────────────────────────────────────

ADMIN_ASSIGN = make_page("Assign Documents", ADMIN_NAV, """
<h1 class="page-title">
  Assign Documents &mdash; {{ trainee.first_name }} {{ trainee.last_name }}
</h1>

<div class="card" style="padding:30px;">
  <form method="POST">
    {% if documents %}
      {% for doc in documents %}
      <label style="display:flex;align-items:flex-start;gap:14px;padding:16px;
                    border:1.5px solid var(--border);border-radius:10px;
                    margin-bottom:10px;cursor:pointer;background:var(--cream);">
        <input type="checkbox" name="document_ids" value="{{ doc.id }}"
               {{ 'checked' if doc.id in assigned_ids }}
               style="width:18px;height:18px;margin-top:2px;flex-shrink:0;">
        <div>
          <div style="font-weight:700;color:var(--warm-brown);">{{ doc.title }}</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">
            {% if doc.doc_type == 'signable' %}
              <span class="badge badge-green">Signable</span>
            {% else %}
              <span class="badge badge-orange">Admin Verified</span>
            {% endif %}
            {% if doc.description %} &nbsp;{{ doc.description }}{% endif %}
          </div>
        </div>
      </label>
      {% endfor %}
    {% else %}
      <div class="empty-state">
        <p>No documents in library yet.</p>
        <a href="/admin/documents/add" class="btn">Add a Document First</a>
      </div>
    {% endif %}

    <div style="display:flex;gap:12px;margin-top:24px;">
      <button type="submit" class="btn">Save Assignments</button>
      <a href="/trainees" class="btn btn-muted">Cancel</a>
    </div>
  </form>
</div>
""")

# ── Template: trainee_documents.html ─────────────────────────────────────────

TRAINEE_DOCUMENTS = make_page("My Documents", TRAINEE_NAV, """
<h1 class="page-title">My Documents</h1>

{% if documents %}
  {% for doc in documents %}
  <div class="card" style="padding:20px;display:flex;justify-content:space-between;align-items:center;gap:16px;">
    <div>
      <div style="font-family:'Lora',serif;font-size:17px;font-weight:600;
                  color:var(--warm-brown);margin-bottom:6px;">{{ doc.title }}</div>
      {% if doc.description %}
      <div style="font-size:13px;color:var(--text-muted);margin-bottom:8px;">{{ doc.description }}</div>
      {% endif %}
      <div>
        {% if doc.status == 'signed' %}
          <span class="badge badge-green">&#10003; Signed</span>
        {% elif doc.status == 'verified' %}
          <span class="badge badge-blue">&#10003; Verified by {{ doc.verified_by }}</span>
        {% else %}
          <span class="badge badge-orange">&#9203; Action Required</span>
        {% endif %}
      </div>
    </div>
    <div style="display:flex;gap:10px;flex-shrink:0;">
      {% if doc.drive_link %}
      <a href="{{ doc.drive_link }}" target="_blank" class="btn btn-sage">View</a>
      {% endif %}
      {% if doc.doc_type == 'signable' and doc.status == 'pending' %}
      <a href="/trainee/documents/sign/{{ doc.assignment_id }}" class="btn">Sign</a>
      {% endif %}
    </div>
  </div>
  {% endfor %}
{% else %}
<div class="card">
  <div class="empty-state">
    <p>No documents assigned yet. Check back soon.</p>
  </div>
</div>
{% endif %}
""")

# ── Template: trainee_sign_document.html ─────────────────────────────────────

TRAINEE_SIGN = make_page("Sign Document", TRAINEE_NAV, """
<h1 class="page-title">Sign: {{ assignment.title }}</h1>

{% if assignment.drive_link %}
<div class="card" style="padding:20px;margin-bottom:20px;display:flex;align-items:center;gap:16px;">
  <span style="font-size:24px;">&#128196;</span>
  <div>
    <div style="font-weight:700;margin-bottom:4px;">Review this document before signing</div>
    <a href="{{ assignment.drive_link }}" target="_blank" class="btn btn-sage" style="font-size:13px;">
      Open Document
    </a>
  </div>
</div>
{% endif %}

<div class="card" style="padding:30px;">
  <p style="font-weight:700;margin-bottom:16px;color:var(--warm-brown);">
    Sign below to confirm you have read and agree to this document:
  </p>

  <canvas id="signatureCanvas" width="700" height="200"
          style="border:2px solid var(--border);border-radius:8px;
                 cursor:crosshair;touch-action:none;width:100%;
                 background:white;"></canvas>

  <div style="margin-top:12px;">
    <button onclick="clearSig()" class="btn btn-muted" style="font-size:13px;">Clear</button>
  </div>

  <form method="POST" style="margin-top:24px;">
    <input type="hidden" name="signature_data" id="signatureData">
    <button type="submit" onclick="return captureSignature()" class="btn"
            style="width:100%;padding:14px;font-size:16px;justify-content:center;">
      Submit Signature
    </button>
  </form>
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
canvas.addEventListener('mousemove', e => { if (!drawing) return; const p = getPos(e); ctx.lineTo(p.x, p.y); ctx.strokeStyle = '#5C3D2E'; ctx.lineWidth = 2; ctx.stroke(); });
canvas.addEventListener('mouseup', () => drawing = false);
canvas.addEventListener('mouseleave', () => drawing = false);
canvas.addEventListener('touchstart', e => { e.preventDefault(); drawing = true; ctx.beginPath(); const p = getPos(e); ctx.moveTo(p.x, p.y); });
canvas.addEventListener('touchmove', e => { e.preventDefault(); if (!drawing) return; const p = getPos(e); ctx.lineTo(p.x, p.y); ctx.strokeStyle = '#5C3D2E'; ctx.lineWidth = 2; ctx.stroke(); });
canvas.addEventListener('touchend', () => drawing = false);

function clearSig() { ctx.clearRect(0, 0, canvas.width, canvas.height); }
function captureSignature() {
  document.getElementById('signatureData').value = canvas.toDataURL();
  return true;
}
</script>
""")

# ── Write all templates ───────────────────────────────────────────────────────

templates = {
    'admin_documents.html': ADMIN_DOCUMENTS,
    'admin_document_form.html': ADMIN_DOCUMENT_FORM,
    'admin_assign_documents.html': ADMIN_ASSIGN,
    'trainee_documents.html': TRAINEE_DOCUMENTS,
    'trainee_sign_document.html': TRAINEE_SIGN,
}

for filename, content in templates.items():
    path = os.path.join(TEMPLATES_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ {filename}")

print("\n✅ All templates updated!")
print("\nNext steps:")
print("  git add -A")
print("  git commit -m 'Fix document library templates - standalone HTML'")
print("  git push")
