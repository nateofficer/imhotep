"""
fix_trainee_documents_auth.py
Run from your imhotep folder:
    python fix_trainee_documents_auth.py
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

OLD = """@app.route('/trainee/documents')
def trainee_documents():
    if not session.get('logged_in'):
        return redirect('/login')
    trainee_id = session.get('trainee_id')"""

NEW = """@app.route('/trainee/documents')
def trainee_documents():
    if not session.get('trainee_id'):
        return redirect('/trainee-login')
    trainee_id = session.get('trainee_id')"""

if OLD not in content:
    print("ERROR: Could not find exact block. Printing context...")
    if "def trainee_documents():" in content:
        idx = content.index("def trainee_documents():")
        print(repr(content[idx-30:idx+200]))
    else:
        print("trainee_documents not found at all.")
else:
    content = content.replace(OLD, NEW, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Fixed! Now run:")
    print("  git add -A")
    print("  git commit -m \"fix trainee documents auth check\"")
    print("  git push")
