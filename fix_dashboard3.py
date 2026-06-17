patch_file = r"C:\Users\natec\OneDrive\Documents\imhotep\app.py"

with open(patch_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with the problematic ternary (apps card)
# We'll replace the entire html = STYLE + admin_nav() + f''' block
# by pre-building the conditional sections before it

# Find "html = STYLE + admin_nav() + f'''" in the dashboard function
target_idx = None
for i, line in enumerate(lines):
    if "html = STYLE + admin_nav() + f'''" in line and i > 400 and i < 800:
        target_idx = i
        break

if target_idx is None:
    print("ERROR: Could not find html = STYLE + admin_nav() line in dashboard")
    exit(1)

print(f"Found html assignment at line {target_idx + 1}")

# Insert pre-built variables just before the html = line
insert_lines = [
    "\n",
    "    # Pre-build conditional sections to avoid f-string ternary issues\n",
    "    if recent_apps:\n",
    "        apps_section = '<table><tr><th>Name</th><th>Position</th><th>Date</th><th></th></tr>' + app_rows + '</table>'\n",
    "    else:\n",
    "        apps_section = '<p class=\"empty-msg\">No applications yet.</p>'\n",
    "\n",
    "    if recent_trainees:\n",
    "        trainees_section = '<table><tr><th>Name</th><th>Hired</th><th></th></tr>' + trainee_rows + '</table>'\n",
    "    else:\n",
    "        trainees_section = '<p class=\"empty-msg\">No trainees yet.</p>'\n",
    "\n",
    "    if recent_leads:\n",
    "        leads_section = '<table><tr><th>Name</th><th>Service</th><th>Status</th><th></th></tr>' + lead_rows + '</table>'\n",
    "    else:\n",
    "        leads_section = '<p class=\"empty-msg\">No leads yet.</p>'\n",
    "\n",
]

lines = lines[:target_idx] + insert_lines + lines[target_idx:]

# Now find and fix the three ternary lines in the HTML block
# They look like: {"<table>..." + app_rows + "...</table>" if recent_apps else \'<p...>\'}
content = ''.join(lines)

# Fix apps ternary
old_apps = '''{"<table><tr><th>Name</th><th>Position</th><th>Date</th><th></th></tr>" + app_rows + "</table>" if recent_apps else \'<p class="empty-msg">No applications yet.</p>\'}'''
new_apps = "{apps_section}"
if old_apps in content:
    content = content.replace(old_apps, new_apps, 1)
    print("Fixed apps ternary")
else:
    # Try without escaping
    print("Searching for apps ternary variant...")
    for variant in [
        '''{"<table><tr><th>Name</th><th>Position</th><th>Date</th><th></th></tr>" + app_rows + "</table>" if recent_apps else '<p class="empty-msg">No applications yet.</p>'}''',
    ]:
        if variant in content:
            content = content.replace(variant, new_apps, 1)
            print("Fixed apps ternary (variant)")
            break

# Fix trainees ternary
old_trainees = '''{"<table><tr><th>Name</th><th>Hired</th><th></th></tr>" + trainee_rows + "</table>" if recent_trainees else \'<p class="empty-msg">No trainees yet.</p>\'}'''
new_trainees = "{trainees_section}"
if old_trainees in content:
    content = content.replace(old_trainees, new_trainees, 1)
    print("Fixed trainees ternary")
else:
    for variant in [
        '''{"<table><tr><th>Name</th><th>Hired</th><th></th></tr>" + trainee_rows + "</table>" if recent_trainees else '<p class="empty-msg">No trainees yet.</p>'}''',
    ]:
        if variant in content:
            content = content.replace(variant, new_trainees, 1)
            print("Fixed trainees ternary (variant)")
            break

# Fix leads ternary
old_leads = '''{"<table><tr><th>Name</th><th>Service</th><th>Status</th><th></th></tr>" + lead_rows + "</table>" if recent_leads else \'<p class="empty-msg">No leads yet.</p>\'}'''
new_leads = "{leads_section}"
if old_leads in content:
    content = content.replace(old_leads, new_leads, 1)
    print("Fixed leads ternary")
else:
    for variant in [
        '''{"<table><tr><th>Name</th><th>Service</th><th>Status</th><th></th></tr>" + lead_rows + "</table>" if recent_leads else '<p class="empty-msg">No leads yet.</p>'}''',
    ]:
        if variant in content:
            content = content.replace(variant, new_leads, 1)
            print("Fixed leads ternary (variant)")
            break

with open(patch_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE. Verify with: python -m py_compile app.py")
