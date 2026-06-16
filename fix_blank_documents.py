"""
fix_blank_documents.py
Run from your imhotep folder:
    python fix_blank_documents.py

What it does:
  1. Lists ALL documents in the DB so you can see what's there.
  2. Identifies blank/unnamed entries (name is NULL, empty, or whitespace-only).
  3. Prompts you to confirm before deleting them.
"""

import sys
import os

# ── Make sure we can import app ──────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

# ── Adjust this import to match your actual model name ──────────────────────
# Common names: Document, TrainingDocument, LibraryDocument
try:
    from app import Document
    MODEL_NAME = "Document"
except ImportError:
    try:
        from app import TrainingDocument as Document
        MODEL_NAME = "TrainingDocument"
    except ImportError:
        print("ERROR: Could not import Document model. Check the class name in app.py.")
        sys.exit(1)

with app.app_context():
    print(f"\n=== Using model: {MODEL_NAME} ===\n")

    # ── 1. List ALL documents ────────────────────────────────────────────────
    all_docs = Document.query.all()
    print(f"Total documents in DB: {len(all_docs)}\n")
    print(f"{'ID':<6} {'Name':<40} {'Drive Link / URL':<50}")
    print("-" * 100)
    for d in all_docs:
        name = getattr(d, 'name', None) or getattr(d, 'title', None) or '(no name field)'
        link = getattr(d, 'drive_link', None) or getattr(d, 'url', None) or getattr(d, 'file_url', None) or ''
        print(f"{d.id:<6} {str(name):<40} {str(link):<50}")

    print()

    # ── 2. Identify blanks ───────────────────────────────────────────────────
    def is_blank(d):
        name = getattr(d, 'name', None) or getattr(d, 'title', None)
        return not name or str(name).strip() == ''

    blanks = [d for d in all_docs if is_blank(d)]
    print(f"Blank/unnamed entries found: {len(blanks)}")

    if not blanks:
        print("Nothing to delete. All done!")
        sys.exit(0)

    print("\nThese will be deleted:")
    for d in blanks:
        link = getattr(d, 'drive_link', None) or getattr(d, 'url', None) or getattr(d, 'file_url', None) or '(no link)'
        print(f"  ID {d.id} — link: {link}")

    # ── 3. Confirm before deleting ───────────────────────────────────────────
    confirm = input("\nDelete these entries? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Aborted. Nothing was deleted.")
        sys.exit(0)

    for d in blanks:
        db.session.delete(d)
    db.session.commit()
    print(f"\n✅ Deleted {len(blanks)} blank document(s). Done!")
