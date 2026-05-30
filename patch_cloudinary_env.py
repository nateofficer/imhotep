with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_config = '''cloudinary.config(
    cloud_name="dy48z1wnj",
    api_key="526198438561634",
    api_secret="GYhG6NcLfeW_MD2Y_VsshUT34IU",
    secure=True
)'''

new_config = '''cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", "dy48z1wnj"),
    api_key=os.environ.get("CLOUDINARY_API_KEY", "526198438561634"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET", "GYhG6NcLfeW_MD2Y_VsshUT34IU"),
    secure=True
)'''

if old_config in content:
    content = content.replace(old_config, new_config)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Done!')
else:
    print('Config block not found')
