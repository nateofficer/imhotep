patch_file = r"C:\Users\natec\OneDrive\Documents\imhotep\app.py"

with open(patch_file, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    <a href="/applications">Applications</a>
      <a href="/crm">CRM</a>
      <a href="/post-job">Post a Job</a>
      
      <a href="/training-modules">Training</a>
      
      <a href="/trainees">Trainees</a>
      <a href="/admin/documents">Documents</a>'''

new = '''    <a href="/dashboard">Dashboard</a>
      <a href="/applications">Applications</a>
      <a href="/crm">CRM</a>
      <a href="/post-job">Post a Job</a>
      <a href="/trainees">Trainees</a>
      <a href="/admin/documents">Documents</a>
      <a href="/schedule">Scheduling</a>'''

if old in content:
    content = content.replace(old, new)
    print("Fixed with exact match")
else:
    # Line by line approach
    lines = content.split('\n')
    new_lines = []
    for i, line in enumerate(lines):
        # Skip the Training modules link
        if '<a href="/training-modules">Training</a>' in line:
            print(f"Removed Training link at line {i+1}")
            continue
        # Add Dashboard before Applications
        if '<a href="/applications">Applications</a>' in line and i > 295 and i < 340:
            new_lines.append(line.replace(
                '<a href="/applications">Applications</a>',
                '<a href="/dashboard">Dashboard</a>'
            ))
            new_lines.append(line)  # keep Applications too
            print(f"Added Dashboard link at line {i+1}")
            continue
        # Add Scheduling after Documents
        if '<a href="/admin/documents">Documents</a>' in line and i > 295 and i < 340:
            new_lines.append(line)
            new_lines.append(line.replace(
                '<a href="/admin/documents">Documents</a>',
                '<a href="/schedule">Scheduling</a>'
            ))
            print(f"Added Scheduling link at line {i+1}")
            continue
        new_lines.append(line)
    content = '\n'.join(new_lines)
    print("Fixed with line scan")

with open(patch_file, 'w', encoding='utf-8') as f:
    f.write(content)

import subprocess
result = subprocess.run(['python', '-m', 'py_compile', patch_file], capture_output=True, text=True)
if result.returncode == 0:
    print("SYNTAX OK - ready to push!")
else:
    print("SYNTAX ERROR:")
    print(result.stderr)
