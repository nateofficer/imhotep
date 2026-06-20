"""
fix_syntax_error2.py
Run from your imhotep folder:
    python fix_syntax_error2.py
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

OLD = """        html += f'''
        <div class="{card_class}">
            <h3>{f["title"]}</h3>
            <p>{status_html}</p>
            {('<p class="form-note">IP recorded: ' + sig["ip_address"] + '</p>') if sig and sig.get("ip_address") else ''}
        </div>
        return redirect(url_for('trainee_documents'))
        html += f'<p><a class="btn" href="/trainee/{trainee_id}">Back to Trainee Profile</a></p>'
        return html"""

NEW = """        html += f'''
        <div class="{card_class}">
            <h3>{f["title"]}</h3>
            <p>{status_html}</p>
            {('<p class="form-note">IP recorded: ' + sig["ip_address"] + '</p>') if sig and sig.get("ip_address") else ''}
        </div>
        '''
    html += f'<p><a class="btn" href="/trainee/{trainee_id}">Back to Trainee Profile</a></p>'
    return html"""

if OLD not in content:
    print("ERROR: Could not find the exact target block.")
    print("Searching for nearby anchor...")
    if "Back to Trainee Profile" in content:
        idx = content.index("Back to Trainee Profile")
        print("Found anchor. Context:")
        print(repr(content[idx-300:idx+100]))
    else:
        print("Anchor not found either.")
else:
    content = content.replace(OLD, NEW, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Fixed! Now run: python fix_blank_documents.py")
