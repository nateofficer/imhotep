with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find("def trainee_onboarding()")
if idx != -1:
    chunk = content[idx:idx+150]
    print("RAW repr:", repr(chunk))
else:
    print("Function not found!")
