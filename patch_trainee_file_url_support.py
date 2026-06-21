"""
Patch: make the Cloudinary file upload option actually work for trainees.

Right now, both the "My Documents" page and the "Sign" page only ever look
at the drive_link field to build the View / Open Document buttons. If a
document was added via file upload instead of a Drive link, the trainee
never sees a working button at all -- even though the file uploaded fine
on the backend.

This patch:
  1. Pulls d.file_url into both trainee-facing queries
  2. Updates both templates to use drive_link if it's set, otherwise
     fall back to file_url

After this patch, uploading a file through the admin Documents form
(instead of pasting a Drive link) will work end-to-end for trainees.

Run from your project root (same folder as app.py):
    python patch_trainee_file_url_support.py
"""

import shutil
from datetime import datetime

APP_FILE = "app.py"
DOCS_TEMPLATE = "templates/trainee_documents.html"
SIGN_TEMPLATE = "templates/trainee_sign_document.html"

APP_REPLACEMENTS = [
    (
"""    cur.execute(\"\"\"
        SELECT td.id as assignment_id, d.title, d.doc_type, d.drive_link, d.description,
               td.status, td.signed_date, td.verified_date, td.verified_by
        FROM trainee_documents td
        JOIN documents d ON td.document_id = d.id
        WHERE td.trainee_id = %s
        ORDER BY d.title
    \"\"\", (trainee_id,))""",
"""    cur.execute(\"\"\"
        SELECT td.id as assignment_id, d.title, d.doc_type, d.drive_link, d.file_url, d.description,
               td.status, td.signed_date, td.verified_date, td.verified_by
        FROM trainee_documents td
        JOIN documents d ON td.document_id = d.id
        WHERE td.trainee_id = %s
        ORDER BY d.title
    \"\"\", (trainee_id,))"""
    ),
    (
"""    cur.execute(\"\"\"
        SELECT td.*, d.title, d.drive_link, d.description
        FROM trainee_documents td
        JOIN documents d ON td.document_id = d.id
        WHERE td.id=%s
    \"\"\", (assignment_id,))""",
"""    cur.execute(\"\"\"
        SELECT td.*, d.title, d.drive_link, d.file_url, d.description
        FROM trainee_documents td
        JOIN documents d ON td.document_id = d.id
        WHERE td.id=%s
    \"\"\", (assignment_id,))"""
    ),
]

DOCS_TEMPLATE_OLD = """    <div style="display:flex;gap:10px;flex-shrink:0;">
      {% if doc.drive_link %}
      <a href="{{ doc.drive_link }}" target="_blank" class="btn btn-sage">View</a>
      {% endif %}
      {% if doc.doc_type == 'signable' and doc.status == 'pending' %}
      <a href="/trainee/documents/sign/{{ doc.assignment_id }}" class="btn">Sign</a>
      {% endif %}
    </div>"""

DOCS_TEMPLATE_NEW = """    <div style="display:flex;gap:10px;flex-shrink:0;">
      {% set doc_link = doc.drive_link or doc.file_url %}
      {% if doc_link %}
      <a href="{{ doc_link }}" target="_blank" class="btn btn-sage">View</a>
      {% endif %}
      {% if doc.doc_type == 'signable' and doc.status == 'pending' %}
      <a href="/trainee/documents/sign/{{ doc.assignment_id }}" class="btn">Sign</a>
      {% endif %}
    </div>"""

SIGN_TEMPLATE_OLD = """{% if assignment.drive_link %}
<div class="card" style="padding:20px;margin-bottom:20px;display:flex;align-items:center;gap:16px;">
  <span style="font-size:24px;">&#128196;</span>
  <div>
    <div style="font-weight:700;margin-bottom:4px;">Review this document before signing</div>
    <a href="{{ assignment.drive_link }}" target="_blank" class="btn btn-sage" style="font-size:13px;">
      Open Document
    </a>
  </div>
</div>
{% endif %}"""

SIGN_TEMPLATE_NEW = """{% set doc_link = assignment.drive_link or assignment.file_url %}
{% if doc_link %}
<div class="card" style="padding:20px;margin-bottom:20px;display:flex;align-items:center;gap:16px;">
  <span style="font-size:24px;">&#128196;</span>
  <div>
    <div style="font-weight:700;margin-bottom:4px;">Review this document before signing</div>
    <a href="{{ doc_link }}" target="_blank" class="btn btn-sage" style="font-size:13px;">
      Open Document
    </a>
  </div>
</div>
{% endif %}"""


def patch_file(path, replacements):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    for i, (old, new) in enumerate(replacements, start=1):
        if old not in content:
            print(f"[{path}] block {i}: not found — file may have changed. Aborting, no changes made to this file.")
            return False
        if content.count(old) != 1:
            print(f"[{path}] block {i}: found {content.count(old)} matches, expected 1 — aborting to be safe.")
            return False

    backup_name = f"{path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(path, backup_name)
    print(f"Backup saved as {backup_name}")

    for old, new in replacements:
        content = content.replace(old, new)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Patched {path}")
    return True


def main():
    ok1 = patch_file(APP_FILE, APP_REPLACEMENTS)
    ok2 = patch_file(DOCS_TEMPLATE, [(DOCS_TEMPLATE_OLD, DOCS_TEMPLATE_NEW)])
    ok3 = patch_file(SIGN_TEMPLATE, [(SIGN_TEMPLATE_OLD, SIGN_TEMPLATE_NEW)])

    if ok1 and ok2 and ok3:
        print("\nAll three files patched successfully.")
        print("Trainees will now see a working View/Open Document button whether")
        print("a document was set up with a Drive link OR an uploaded file.")
    else:
        print("\nOne or more files were not patched -- check the messages above.")


if __name__ == "__main__":
    main()
