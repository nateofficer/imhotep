import os

templates_dir = r"C:\Users\natec\OneDrive\Documents\imhotep\templates"

# ── FIX 1: Remove Onboarding link from trainee_documents.html and trainee_sign_document.html
for filename in ['trainee_documents.html', 'trainee_sign_document.html']:
    path = os.path.join(templates_dir, filename)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old = '        <a href="/onboarding">Onboarding</a>\n        <a href="/trainee/documents">My Documents</a>'
    new = '        <a href="/trainee/documents">My Documents</a>'
    
    if old in content:
        content = content.replace(old, new)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"FIX 1 OK: Removed Onboarding tab from {filename}")
    else:
        # Try alternate spacing
        old2 = '      <a href="/onboarding">Onboarding</a>\n      <a href="/trainee/documents">My Documents</a>'
        new2 = '      <a href="/trainee/documents">My Documents</a>'
        if old2 in content:
            content = content.replace(old2, new2)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"FIX 1 OK (alt spacing): Removed Onboarding tab from {filename}")
        else:
            # Line-by-line fallback
            lines = content.split('\n')
            new_lines = [l for l in lines if not ('<a href="/onboarding">Onboarding</a>' in l)]
            if len(new_lines) < len(lines):
                with open(path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                print(f"FIX 1 OK (line scan): Removed Onboarding tab from {filename}")
            else:
                print(f"FIX 1 SKIP: Onboarding tab not found in {filename}")

# ── FIX 2: Update trainee_onboarding.html nav - remove My Onboarding, add My Documents
path = os.path.join(templates_dir, 'trainee_onboarding.html')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '    <a href="/training">My Training</a>\n      <a href="/onboarding" class="active">My Onboarding</a>'
new = '    <a href="/training">My Training</a>\n      <a href="/trainee/documents">My Documents</a>'

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("FIX 2 OK: Updated trainee_onboarding.html nav")
else:
    # Line-by-line fallback
    lines = content.split('\n')
    new_lines = []
    for l in lines:
        if '<a href="/onboarding"' in l and 'My Onboarding' in l:
            new_lines.append(l.replace('<a href="/onboarding"', '<a href="/trainee/documents"').replace('My Onboarding', 'My Documents').replace(' class="active"', ''))
        else:
            new_lines.append(l)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    print("FIX 2 OK (line scan): Updated trainee_onboarding.html nav")

print("\nAll done. Run: python -m py_compile app.py to verify no app.py issues.")
