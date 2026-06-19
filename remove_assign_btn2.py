text = open("app.py", encoding="utf-8").read()
old = "        <a class=\"btn\" href=\"/admin/documents/assign/{trainee_id}\">Assign Documents</a>\n        <p class=\"form-note\">Send this code to {t[\"first_name\"]} along with the training login URL. They will use their email ({t[\"email\"]}) and this code to log in.</p>\n"
count = text.count(old)
print("Found", count, "matches")
