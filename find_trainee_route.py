text = open("app.py", encoding="utf-8").read()
idx = text.find("/trainee/<int:trainee_id>")
print(text[max(0,idx-200):idx+1200])
