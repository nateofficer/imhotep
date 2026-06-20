"""
Imhotep - Fix Session Cookie for Render
-----------------------------------------
Adds secure session cookie configuration so sessions
persist properly on Render's HTTPS environment.

Run from your imhotep folder:
    python fix_session.py
"""

import os

APP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')

with open(APP_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the secret key line and add session config after it
old = "app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')"
new = """app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours"""

if old not in content:
    print("❌ Could not find secret key line — check app.py manually.")
else:
    content = content.replace(old, new)
    with open(APP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Session cookie settings added to app.py")

print("\nNext steps:")
print("  git add -A")
print("  git commit -m 'Fix session cookie for Render HTTPS'")
print("  git push")
