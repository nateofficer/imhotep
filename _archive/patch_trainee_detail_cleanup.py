"""
Patch: remove the 'Module Progress' section AND the 'CERTIFIED' badge from the
admin trainee detail page (/trainee/<id>). Keeps the Trainee Access Code card.

DO NOT run this if you already ran patch_remove_module_progress.py — this one
assumes app.py is still in its original (unpatched) state for this route.

Run from your project root (same folder as app.py):
    python patch_trainee_detail_cleanup.py
"""

import shutil
from datetime import datetime

FILE = "app.py"

OLD = """    cursor.execute('SELECT * FROM training_modules ORDER BY created_date')
    modules = cursor.fetchall()
    cursor.execute('SELECT * FROM module_progress WHERE trainee_id = %s', (trainee_id,))
    progress_rows = cursor.fetchall()
    progress = {p['module_id']: p for p in progress_rows}

    cursor.execute('SELECT COUNT(*) as cnt FROM training_modules WHERE required = 1')
    required_count = cursor.fetchone()['cnt']
    passed_required = sum(1 for m in modules if m['required'] and progress.get(m['id']) and progress[m['id']]['passed'])
    certified = passed_required >= required_count and required_count > 0
    conn.close()

    cert_html = '<span class="cert-badge">CERTIFIED</span>' if certified else ''

    html = STYLE + admin_nav() + f'<h1>{t["first_name"]} {t["last_name"]} {cert_html}</h1>'
    html += f'''
    <div class="application">
        <p><strong>Email:</strong> {t['email']}</p>
        <p><strong>Phone:</strong> {t['phone'] or 'Not provided'}</p>
        <p><strong>Hired Date:</strong> {t['hired_date']}</p>
        <h3>Trainee Access Code</h3>
        <div class="access-code-display">{t['access_code']}</div>
        
        <p class="form-note">Send this code to {t['first_name']} along with the training login URL. They will use their email ({t['email']}) and this code to log in.</p>
    </div>
    '''

    html += '<h2>Module Progress</h2>'
    if not modules:
        html += '<p>No training modules created yet.</p>'
    else:
        for m in modules:
            p = progress.get(m['id'])
            if p and p['passed']:
                status = '<span class="status-label status-passed">PASSED</span>'
                card_class = 'module-card passed'
            elif p and p['attempts'] > 0:
                status = f'<span class="status-label status-failed">Attempted ({p["attempts"]}x)</span>'
                card_class = 'module-card failed'
            else:
                status = '<span class="status-label status-not-started">Not Started</span>'
                card_class = 'module-card'

            req_label = '(Required)' if m['required'] else '(Optional)'
            html += f'''
            <div class="{card_class}">
                <h3>{m['title']} {req_label}</h3>
                <p>{status}</p>
            </div>
            '''
    return html"""

NEW = """    conn.close()

    html = STYLE + admin_nav() + f'<h1>{t["first_name"]} {t["last_name"]}</h1>'
    html += f'''
    <div class="application">
        <p><strong>Email:</strong> {t['email']}</p>
        <p><strong>Phone:</strong> {t['phone'] or 'Not provided'}</p>
        <p><strong>Hired Date:</strong> {t['hired_date']}</p>
        <h3>Trainee Access Code</h3>
        <div class="access-code-display">{t['access_code']}</div>
        
        <p class="form-note">Send this code to {t['first_name']} along with the training login URL. They will use their email ({t['email']}) and this code to log in.</p>
    </div>
    '''
    return html"""


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    if OLD not in content:
        print("Could not find the expected original block in app.py.")
        print("This usually means the file has already been edited.")
        print("No changes made — let Nate's Claude know and a smaller patch can be made.")
        return

    count = content.count(OLD)
    if count != 1:
        print(f"Found {count} matches, expected exactly 1 — aborting to be safe.")
        return

    backup_name = f"{FILE}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(FILE, backup_name)
    print(f"Backup saved as {backup_name}")

    content = content.replace(OLD, NEW)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("Done. Removed:")
    print(" - Module Progress section")
    print(" - CERTIFIED badge + related queries")
    print("Kept: Trainee Access Code card.")


if __name__ == "__main__":
    main()
