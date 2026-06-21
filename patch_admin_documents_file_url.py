"""
Patch: fix the admin Document Library list page (/admin/documents) so the
"View" link shows up for documents added via file upload too, not just
ones with a Drive Link. Same root cause as the trainee-facing pages we
already fixed -- this template only ever checked drive_link.

Run from your project root (same folder as app.py):
    python patch_admin_documents_file_url.py
"""

import shutil
from datetime import datetime

FILE = "templates/admin_documents.html"

OLD = """          <a href="/admin/documents/edit/{{ doc.id }}" style="color:var(--terracotta);font-weight:700;">Edit</a>
          {% if doc.drive_link %}
          <a href="{{ doc.drive_link }}" target="_blank" style="color:var(--sage);font-weight:700;">View</a>
          {% endif %}"""

NEW = """          <a href="/admin/documents/edit/{{ doc.id }}" style="color:var(--terracotta);font-weight:700;">Edit</a>
          {% set doc_link = doc.drive_link or doc.file_url %}
          {% if doc_link %}
          <a href="{{ doc_link }}" target="_blank" style="color:var(--sage);font-weight:700;">View</a>
          {% endif %}"""


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    if OLD not in content:
        print("Could not find the expected block -- the template may have changed.")
        print("No changes made.")
        return

    if content.count(OLD) != 1:
        print(f"Found {content.count(OLD)} matches, expected exactly 1 -- aborting to be safe.")
        return

    backup_name = f"{FILE}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(FILE, backup_name)
    print(f"Backup saved as {backup_name}")

    content = content.replace(OLD, NEW)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("Done. The admin Document Library View link now works for")
    print("uploaded files too, not just Drive Links.")


if __name__ == "__main__":
    main()
