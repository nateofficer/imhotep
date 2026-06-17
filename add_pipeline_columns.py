"""
add_pipeline_columns.py
Run from your imhotep folder:
    python add_pipeline_columns.py

Adds:
  - candidates.status VARCHAR(20) DEFAULT 'Applied'
  - documents.phase VARCHAR(20) DEFAULT 'training'
  - Tags onboarding documents with phase='onboarding'
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, get_db

with app.app_context():
    conn = get_db()
    cur = conn.cursor()

    # Add status to candidates
    try:
        cur.execute("ALTER TABLE candidates ADD COLUMN status VARCHAR(20) DEFAULT 'Applied'")
        conn.commit()
        print("✅ Added candidates.status column")
    except Exception as e:
        print(f"candidates.status: {e}")

    # Add phase to documents
    try:
        cur.execute("ALTER TABLE documents ADD COLUMN phase VARCHAR(20) DEFAULT 'training'")
        conn.commit()
        print("✅ Added documents.phase column")
    except Exception as e:
        print(f"documents.phase: {e}")

    # Tag onboarding documents
    onboarding_titles = ['non compete', 'W4', 'I9', 'W9', 'W92']
    for title in onboarding_titles:
        try:
            cur.execute("UPDATE documents SET phase='onboarding' WHERE title=%s", (title,))
            print(f"✅ Tagged '{title}' as onboarding")
        except Exception as e:
            print(f"Tagging '{title}': {e}")
    conn.commit()

    # Set existing hired candidates to Onboarding status
    try:
        cur.execute("UPDATE candidates SET status='Onboarding' WHERE hired=1")
        conn.commit()
        print("✅ Set existing hired candidates to Onboarding status")
    except Exception as e:
        print(f"Updating hired candidates: {e}")

    conn.close()
    print("\n✅ All done!")
