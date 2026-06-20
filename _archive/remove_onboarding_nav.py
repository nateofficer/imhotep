"""
remove_onboarding_nav.py
Run from your imhotep folder:
    python remove_onboarding_nav.py

Removes the Onboarding link from the admin nav bar.
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove from admin nav
removed = 0

candidates = [
    '<a href="/onboarding-forms">Onboarding</a>',
    '<a href="/onboarding">Onboarding</a>',
    '<a href="/onboarding-forms">Onboarding</a>',
]

for candidate in candidates:
    if candidate in content:
        content = content.replace(candidate, '', 1)
        print(f"✅ Removed: {candidate}")
        removed += 1

if removed == 0:
    print("Could not find exact nav link. Searching...")
    if 'Onboarding' in content:
        # Find all lines with Onboarding in nav context
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'Onboarding' in line and 'href' in line and 'admin_nav' not in line:
                print(f"Line {i+1}: {repr(line)}")
    else:
        print("No Onboarding references found.")
else:
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("\n✅ Done! Now run:")
    print("  git add -A")
    print("  git commit -m \"remove onboarding nav link\"")
    print("  git push")
