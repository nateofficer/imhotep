import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """        download_html = ''
        if f['file_filename']:
            download_html = f'<a class="btn" href="{f["file_filename"]}" target="_blank" style="background:#17a2b8;color:white;margin-right:8px;">⬇ Download Form</a>'"""

new_block = """        download_html = ''
        desc = f['description'] or ''
        if desc.startswith('http'):
            download_html = f'<a class="btn" href="{desc}" target="_blank" style="background:#17a2b8;color:white;margin-right:8px;display:inline-block;margin-bottom:8px;">⬇ Download Form</a>'
        elif f['file_filename'] and f['file_filename'].startswith('http'):
            download_html = f'<a class="btn" href="{f["file_filename"]}" target="_blank" style="background:#17a2b8;color:white;margin-right:8px;display:inline-block;margin-bottom:8px;">⬇ Download Form</a>'"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Done! Download button updated.')
else:
    print('Block not found - checking for original...')
    # Try adding fresh if patch_download was never applied
    old2 = """        html += f'''
        <div class="{card_class}">
            <h2><span class="step-number {step_class}">{i}</span>{f["title"]}</h2>
            <p>{f["description"] or ""}</p>
            {action_html}
        </div>
        '''"""
    new2 = """        download_html = ''
        desc = f['description'] or ''
        if desc.startswith('http'):
            download_html = f'<a class="btn" href="{desc}" target="_blank" style="background:#17a2b8;color:white;margin-right:8px;display:inline-block;margin-bottom:8px;">⬇ Download Form</a>'
        elif f['file_filename'] and f['file_filename'].startswith('http'):
            download_html = f'<a class="btn" href="{f["file_filename"]}" target="_blank" style="background:#17a2b8;color:white;margin-right:8px;display:inline-block;margin-bottom:8px;">⬇ Download Form</a>'

        html += f'''
        <div class="{card_class}">
            <h2><span class="step-number {step_class}">{i}</span>{f["title"]}</h2>
            {download_html}
            {action_html}
        </div>
        '''"""
    if old2 in content:
        content = content.replace(old2, new2)
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('Done! Download button added fresh.')
    else:
        print('Could not find block - manual edit needed')
