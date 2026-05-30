with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """        html += f'''
        <div class="{card_class}">
            <h2><span class="step-number {step_class}">{i}</span>{f["title"]}</h2>
            <p>{f["description"] or ""}</p>
            {action_html}
        </div>
        '''"""

new_block = """        download_html = ''
        if f['file_filename']:
            download_html = f'<a class="btn" href="{f["file_filename"]}" target="_blank" style="background:#17a2b8;color:white;margin-right:8px;">⬇ Download Form</a>'

        html += f'''
        <div class="{card_class}">
            <h2><span class="step-number {step_class}">{i}</span>{f["title"]}</h2>
            <p>{f["description"] or ""}</p>
            {download_html}
            {action_html}
        </div>
        '''"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Done! Download button added.')
else:
    print('Block not found - trying alternate spacing...')
    # Try to find it with different whitespace
    import re
    pattern = r'html \+= f\'\'\'\s*<div class="\{card_class\}">'
    match = re.search(pattern, content)
    if match:
        print(f'Found at position {match.start()} - manual edit needed')
    else:
        print('Could not locate block automatically')
