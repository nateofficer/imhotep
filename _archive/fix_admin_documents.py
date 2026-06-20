patch_file = r"C:\Users\natec\OneDrive\Documents\imhotep\app.py"

with open(patch_file, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''@app.route('/admin/documents')
def admin_documents():
    if not session.get('trainee_id'):
        return redirect('/trainee-login')'''

new = '''@app.route('/admin/documents')
@login_required
def admin_documents():'''

if old in content:
    content = content.replace(old, new)
    print("Fixed with exact match")
else:
    print("Exact match failed, trying line scan...")
    lines = content.split('\n')
    new_lines = []
    i = 0
    fixed = False
    while i < len(lines):
        line = lines[i]
        if "@app.route('/admin/documents')" in line and i < len(lines) - 4:
            # Check next few lines for the buggy pattern
            window = '\n'.join(lines[i:i+5])
            if "def admin_documents" in window and "session.get('trainee_id')" in window:
                new_lines.append("@app.route('/admin/documents')")
                new_lines.append("@login_required")
                new_lines.append("def admin_documents():")
                # Skip ahead past the old check lines
                j = i + 1
                skip_count = 0
                while j < len(lines) and skip_count < 4:
                    if "def admin_documents" in lines[j]:
                        j += 1
                        skip_count += 1
                        continue
                    if "session.get('trainee_id')" in lines[j] or "redirect('/trainee-login')" in lines[j]:
                        j += 1
                        skip_count += 1
                        continue
                    break
                i = j
                fixed = True
                continue
        new_lines.append(line)
        i += 1
    if fixed:
        content = '\n'.join(new_lines)
        print("Fixed with line scan")
    else:
        print("ERROR: Could not locate the buggy function")

with open(patch_file, 'w', encoding='utf-8') as f:
    f.write(content)

import subprocess
result = subprocess.run(['python', '-m', 'py_compile', patch_file], capture_output=True, text=True)
if result.returncode == 0:
    print("SYNTAX OK - ready to push!")
else:
    print("SYNTAX ERROR:")
    print(result.stderr)
