"""
fix_syntax_error.py
Run from your imhotep folder:
    python fix_syntax_error.py
"""

import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

OLD = """        {f'<p class="form-note">IP recorded: {sig["ip_address"]}</p>' if sig and sig.get("ip_address") else ''}"""

NEW = """        {('<p class="form-note">IP recorded: ' + sig["ip_address"] + '</p>') if sig and sig.get("ip_address") else ''}"""

if OLD not in content:
    print("ERROR: Could not find the target string. It may already be fixed or look slightly different.")
    print("Searching for partial match...")
    if 'IP recorded:' in content:
        # Find and print surrounding lines
        idx = content.index('IP recorded:')
        print("Found 'IP recorded:' at char", idx)
        print("Context:", repr(content[idx-100:idx+150]))
    else:
        print("'IP recorded:' not found at all in app.py")
else:
    content = content.replace(OLD, NEW, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Syntax error fixed! Now run: python fix_blank_documents.py")
