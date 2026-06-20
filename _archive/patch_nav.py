import re

path = r'C:\Users\natec\OneDrive\Documents\imhotep\app.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_func = [
    'def admin_nav():\n',
    '    return \'\'\'\n',
    '<style>\n',
    'nav{background:#5C3D2E;padding:0 32px;height:56px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}\n',
    '.navbar-brand{font-family:\'Lora\',serif;font-size:20px;color:#FFF9F0;font-weight:600;letter-spacing:0.5px;text-decoration:none;}\n',
    '.navbar-brand span{color:#D4A843;}\n',
    '.navbar-links{display:flex;align-items:center;gap:4px;}\n',
    '.navbar-links a{font-size:13px;font-weight:700;color:rgba(255,249,240,0.72);text-decoration:none;padding:6px 12px;border-radius:6px;}\n',
    '.navbar-links a:hover{background:rgba(255,249,240,0.12);color:#FFF9F0;}\n',
    '</style>\n',
    '<nav>\n',
    '  <a href="/" class="navbar-brand">Casey\'s<span>Cleaning</span></a>\n',
    '  <div class="navbar-links">\n',
    '    <a href="/applications">Applications</a>\n',
    '    <a href="/crm">CRM</a>\n',
    '    <a href="/post-job">Post a Job</a>\n',
    '    <a href="/training-modules">Training</a>\n',
    '    <a href="/onboarding-forms">Onboarding</a>\n',
    '    <a href="/trainees">Trainees</a>\n',
    '    <a href="/admin/documents">Documents</a>\n',
    '    <a href="/logout">Logout</a>\n',
    '  </div>\n',
    '</nav>\n',
    '\'\'\'\n',
    '\n',
]

lines[302:317] = new_func

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Done')
