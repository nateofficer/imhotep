with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """        download_html = ''
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

new_block = """        download_html = ''
        desc = f['description'] or ''
        display_desc = '' if desc.startswith('http') else desc
        if desc.startswith('http'):
            download_html = f'<a class="btn" href="{desc}" target="_blank" style="background:#17a2b8;color:white;margin-right:8px;display:inline-block;margin-bottom:8px;">&#11015; Download Form</a>'
        elif f['file_filename'] and f['file_filename'].startswith('http'):
            download_html = f'<a class="btn" href="{f["file_filename"]}" target="_blank" style="background:#17a2b8;color:white;margin-right:8px;display:inline-block;margin-bottom:8px;">&#11015; Download Form</a>'

        html += f\'\'\'
        <div class="{card_class}">
            <h2><span class="step-number {step_class}">{i}</span>{f["title"]}</h2>
            <p>{display_desc}</p>
            {download_html}
            {action_html}
        </div>
        \'\'\'"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Done!')
else:
    print('Block not found')
    # Show what we have around download_html for debugging
    idx = content.find('download_html = f\'<a class="btn" href="{desc}"')
    if idx > -1:
        print(content[idx-300:idx+500])
