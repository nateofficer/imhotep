with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find("download_html = ''")
if idx > -1:
    chunk = content[idx:idx+600]
    print(repr(chunk))
else:
    print('Not found')
