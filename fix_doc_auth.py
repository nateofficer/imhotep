"""
Imhotep - Fix Document Library Auth
-------------------------------------
Your login only sets session['logged_in'] = True
The new document routes were checking session['role'] == 'admin' which never passes.
This script fixes all doc library routes to just check session['logged_in'].

Run from your imhotep folder:
    python fix_doc_auth.py
"""

import os

APP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')

with open(APP_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

old = "if not session.get('logged_in') or session.get('role') != 'admin':\n        return redirect('/login')"
new = "if not session.get('logged_in'):\n        return redirect('/login')"

count = content.count(old)

if count == 0:
    print("⚠️  No matching auth checks found — may already be fixed or pattern is different.")
else:
    content = content.replace(old, new)
    with open(APP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Fixed {count} auth check(s) in app.py")

print("\nNext steps:")
print("  git add -A")
print("  git commit -m 'Fix doc library auth check'")
print("  git push")
