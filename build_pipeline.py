"""
build_pipeline.py
Run from your imhotep folder:
    python build_pipeline.py

What it does:
  1. Adds 'status' column to candidates table (Applied/Reviewing/Vetted/Hired/Onboarding/Training/Active/Scheduling)
  2. Adds 'phase' column to documents table (onboarding/training)
  3. Tags existing documents with correct phase
  4. Updates the hire route to auto-assign onboarding docs and set status=Onboarding
  5. Adds status dropdown to Applications page
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ── STEP 1: Add ALTER TABLE statements to init_db ───────────────────────────
# Find the init_db function and add ALTER TABLE statements after the CREATE TABLEs

OLD_INIT = "    conn.commit()\n    conn.close()\n\ninit_db()"

NEW_INIT = """    # Add columns if they don't exist (safe to run multiple times)
    try:
        cursor.execute("ALTER TABLE candidates ADD COLUMN status VARCHAR(20) DEFAULT 'Applied'")
        conn.commit()
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN phase VARCHAR(20) DEFAULT 'training'")
        conn.commit()
    except Exception:
        pass
    # Tag onboarding documents
    onboarding_titles = ['non compete', 'W4', 'I9', 'W9', 'W92']
    for title in onboarding_titles:
        try:
            cursor.execute("UPDATE documents SET phase='onboarding' WHERE title=%s", (title,))
        except Exception:
            pass
    conn.commit()
    conn.close()

init_db()"""

if OLD_INIT not in content:
    print("WARNING: Could not find init_db closing block. Skipping step 1.")
else:
    content = content.replace(OLD_INIT, NEW_INIT, 1)
    print("✅ Step 1: Added ALTER TABLE statements to init_db")

# ── STEP 2: Update hire route to auto-assign onboarding docs ────────────────

OLD_HIRE = """    cursor.execute('INSERT INTO trainees (candidate_id, email, access_code) VALUES (%s, %s, %s)',
                   (candidate_id, candidate['email'], code))
    cursor.execute('UPDATE candidates SET hired = 1 WHERE id = %s', (candidate_id,))
    trainee_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return redirect(f'/trainee/{trainee_id}')"""

NEW_HIRE = """    cursor.execute('INSERT INTO trainees (candidate_id, email, access_code) VALUES (%s, %s, %s)',
                   (candidate_id, candidate['email'], code))
    cursor.execute('UPDATE candidates SET hired = 1, status = %s WHERE id = %s',
                   ('Onboarding', candidate_id))
    trainee_id = cursor.lastrowid
    # Auto-assign onboarding documents
    cursor.execute("SELECT id FROM documents WHERE phase='onboarding'")
    onboarding_docs = cursor.fetchall()
    for doc in onboarding_docs:
        try:
            cursor.execute(
                "INSERT IGNORE INTO trainee_documents (trainee_id, document_id, status) VALUES (%s, %s, 'pending')",
                (trainee_id, doc['id'])
            )
        except Exception:
            pass
    conn.commit()
    conn.close()
    return redirect(f'/trainee/{trainee_id}')"""

if OLD_HIRE not in content:
    print("WARNING: Could not find hire route block. Checking for partial match...")
    if 'INSERT INTO trainees (candidate_id, email, access_code)' in content:
        idx = content.index('INSERT INTO trainees (candidate_id, email, access_code)')
        print("Found partial at char", idx, "- context:")
        print(repr(content[idx-50:idx+300]))
    else:
        print("ERROR: Could not find hire INSERT at all.")
else:
    content = content.replace(OLD_HIRE, NEW_HIRE, 1)
    print("✅ Step 2: Updated hire route to auto-assign onboarding docs")

# ── STEP 3: Add status dropdown to Applications page ────────────────────────
# Find where the hired badge is rendered and add a status dropdown below it

OLD_APP_STATUS = """                {hire_button}
                <form method="POST" action="/delete/{app_row['id']}" onsubmit="return confirm('Delete this application?');" style="display:inline-block; margin-top:10px; box-shadow:none; padding:0; background:none;">
                    <button class="btn btn-danger" type="submit">Delete</button>
                </form>"""

NEW_APP_STATUS = """                {hire_button}
                <form method="POST" action="/update-status/{app_row['id']}" style="display:inline-block; margin-left:10px;">
                    <select name="status" onchange="this.form.submit()" style="padding:4px 8px; border-radius:4px; border:1px solid #ccc; font-size:13px;">
                        {''.join(f'<option value="{s}" {"selected" if app_row.get("status")==s else ""}>{s}</option>'
                            for s in ['Applied','Reviewing','Vetted','Hired','Onboarding','Training','Active','Scheduling'])}
                    </select>
                </form>
                <form method="POST" action="/delete/{app_row['id']}" onsubmit="return confirm('Delete this application?');" style="display:inline-block; margin-top:10px; box-shadow:none; padding:0; background:none;">
                    <button class="btn btn-danger" type="submit">Delete</button>
                </form>"""

if OLD_APP_STATUS not in content:
    print("WARNING: Could not find application status block for dropdown. Skipping step 3.")
    print("This can be added manually later.")
else:
    content = content.replace(OLD_APP_STATUS, NEW_APP_STATUS, 1)
    print("✅ Step 3: Added status dropdown to Applications page")

# ── STEP 4: Add update-status route ─────────────────────────────────────────

OLD_DELETE_ROUTE = "@app.route('/delete/<int:candidate_id>', methods=['POST'])"

NEW_STATUS_ROUTE = """@app.route('/update-status/<int:candidate_id>', methods=['POST'])
@login_required
def update_candidate_status(candidate_id):
    status = request.form.get('status', 'Applied')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE candidates SET status=%s WHERE id=%s', (status, candidate_id))
    conn.commit()
    conn.close()
    return redirect('/applications')

@app.route('/delete/<int:candidate_id>', methods=['POST'])"""

if OLD_DELETE_ROUTE not in content:
    print("WARNING: Could not find delete route to insert status route before. Skipping step 4.")
else:
    content = content.replace(OLD_DELETE_ROUTE, NEW_STATUS_ROUTE, 1)
    print("✅ Step 4: Added update-status route")

# ── Write file ───────────────────────────────────────────────────────────────
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ All done! Now run:")
print("  git add -A")
print("  git commit -m \"add hiring pipeline and onboarding auto-assign\"")
print("  git push")
