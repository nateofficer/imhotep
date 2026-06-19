patch_file = r"C:\Users\natec\OneDrive\Documents\imhotep\templates\admin_documents.html"

with open(patch_file, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''  <a href="/applications">Applications</a>
      <a href="/trainees">Trainees</a>
      <a href="/onboarding-forms">Onboarding</a>
      <a href="/admin/documents">Documents</a>
      <a href="/logout">Logout</a>'''

new = '''  <a href="/dashboard">Dashboard</a>
      <a href="/applications">Applications</a>
      <a href="/crm">CRM</a>
      <a href="/post-job">Post a Job</a>
      <a href="/trainees">Trainees</a>
      <a href="/admin/documents">Documents</a>
      <a href="/schedule">Scheduling</a>
      <a href="/logout">Logout</a>'''

if old in content:
    content = content.replace(old, new)
    print("Fixed with exact match")
else:
    print("Exact match failed - trying line removal of Onboarding only")
    lines = content.split('\n')
    new_lines = [l for l in lines if '/onboarding-forms">Onboarding</a>' not in l]
    if len(new_lines) < len(lines):
        content = '\n'.join(new_lines)
        print("Removed Onboarding link only (nav not fully synced, but unblocked)")
    else:
        print("ERROR: could not find onboarding link to remove")

with open(patch_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done.")
