import base64
import os


def save_attachment_stream(name: str, file_bytes: bytes):
    base_dir = os.path.dirname(os.getcwd())
    target_dir = os.path.join(base_dir, "agents", "data")
    os.makedirs(target_dir, exist_ok=True)

    filepath = os.path.join(target_dir, name)

    with open(filepath, "wb") as f:
        f.write(file_bytes)

    return filepath

