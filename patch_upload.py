with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """if 'form_file' in request.files:
            f = request.files['form_file']
            if f and f.filename:
                timestamp = str(int(time.time()))
                file_filename = f"{timestamp}_form_{f.filename}"
                f.save(os.path.join(UPLOAD_FOLDER, file_filename))"""

new_block = """if 'form_file' in request.files:
            f = request.files['form_file']
            if f and f.filename:
                timestamp = str(int(time.time()))
                public_id = f"imhotep_forms/{timestamp}_form_{f.filename}"
                result = cloudinary.uploader.upload(
                    f,
                    public_id=public_id,
                    resource_type="raw"
                )
                file_filename = result['secure_url']"""

count = content.count(old_block)
print(f"Found {count} block(s) to replace")

content = content.replace(old_block, new_block)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
