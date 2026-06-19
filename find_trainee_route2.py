text = open("app.py", encoding="utf-8").read()
idx = text.find("/trainee/<int:trainee_id>")
print(text[idx+1200:idx+3200])
