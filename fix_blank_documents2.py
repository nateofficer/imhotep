"""
fix_blank_documents2.py
Run from your imhotep folder:
    python fix_blank_documents2.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, get_db

with app.app_context():
    conn = get_db()
    cur = conn.cursor()

    # ── 1. List ALL documents ────────────────────────────────────────────────
    cur.execute("SELECT * FROM documents")
    all_docs = cur.fetchall()

    if not all_docs:
        # Try alternate table name
        cur.execute("SHOW TABLES")
        tables = [list(t.values())[0] for t in cur.fetchall()]
        print("No rows found in 'documents'. Tables in DB:", tables)
        sys.exit(1)

    print(f"\nTotal documents in DB: {len(all_docs)}\n")

    # Print column names
    cur.execute("DESCRIBE documents")
    cols = [c['Field'] for c in cur.fetchall()]
    print(f"Columns: {cols}\n")

    # Print all rows
    print(f"{'ID':<6} {'Name':<40} {'Extra'}")
    print("-" * 80)
    for d in all_docs:
        doc_id = d.get('id', '?')
        name = d.get('name') or d.get('title') or '(blank)'
        extra = d.get('drive_link') or d.get('url') or d.get('file_url') or d.get('document_text') or ''
        print(f"{str(doc_id):<6} {str(name):<40} {str(extra)[:60]}")

    print()

    # ── 2. Find blanks ───────────────────────────────────────────────────────
    name_col = 'name' if 'name' in cols else 'title' if 'title' in cols else None
    if not name_col:
        print(f"ERROR: Can't find name/title column. Columns are: {cols}")
        sys.exit(1)

    blanks = [d for d in all_docs if not d.get(name_col) or str(d.get(name_col)).strip() == '']
    print(f"Blank/unnamed entries: {len(blanks)}")

    if not blanks:
        print("Nothing to delete. All done!")
        sys.exit(0)

    print("\nThese will be deleted:")
    for d in blanks:
        print(f"  ID {d['id']} — {d}")

    confirm = input("\nDelete these? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Aborted.")
        sys.exit(0)

    for d in blanks:
        cur.execute("DELETE FROM documents WHERE id=%s", (d['id'],))
    conn.commit()
    print(f"\n✅ Deleted {len(blanks)} blank document(s).")
