with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

insert = """
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name="dy48z1wnj",
    api_key="526198438561634",
    api_secret="GYhG6NcLfeW_MD2Y_VsshUT34IU",
    secure=True
)
"""

content = content.replace(
    'os.makedirs(UPLOAD_FOLDER, exist_ok=True)',
    'os.makedirs(UPLOAD_FOLDER, exist_ok=True)' + insert
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
