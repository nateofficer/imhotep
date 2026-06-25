"""
Patch script: adds a /admin/documents/delete/<doc_id> route to app.py

Usage:
    1. Place this file in the same folder as app.py
       (C:\\Users\\natec\\OneDrive\\Documents\\imhotep)
    2. Open a real PowerShell window in that folder
    3. Run: python patch_add_delete_document.py
    4. It will print SUCCESS or tell you what went wrong.
"""

import re

APP_FILE = "app.py"

MARKER = "@app.route('/admin/documents/edit/<int:doc_id>', methods=['GET', 'POST'])"

NEW_ROUTE = '''@app.route('/admin/documents/delete/<int:doc_id>')
def delete_document(doc_id):
    if not session.get('logged_in'):
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM documents WHERE id=%s", (doc_id,))
    conn.commit()
    return redirect('/admin/documents')


'''

with open(APP_FILE, "r", encoding="utf-8") as f:
    content = f.read()

if "def delete_document(" in content:
    print("SKIPPED: delete_document route already exists in app.py. No changes made.")
elif MARKER not in content:
    print("ERROR: Could not find the expected marker line in app.py.")
    print("Marker searched for:")
    print(MARKER)
    print("No changes were made. Paste this output back to Claude.")
else:
    new_content = content.replace(MARKER, NEW_ROUTE + MARKER, 1)
    with open(APP_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("SUCCESS: delete_document route added to app.py, right before the edit_document route.")
