import base64
import os

def save_pdf_from_content_bytes(name: str, content_bytes: str):
    # Decode base64 content
    file_bytes = base64.b64decode(content_bytes)

    # Path: go back one folder → enter agents/data
    base_dir = os.path.dirname(os.getcwd())              # ../
    target_dir = os.path.join(base_dir, "agents", "data")

    # Ensure folder exists
    os.makedirs(target_dir, exist_ok=True)

    filepath = os.path.join(target_dir, name)

    # Write file
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    return filepath
