import base64
import os

def save_pdf_from_content_bytes(name: str, content_bytes: str):
    # Decode base64 content
    file_bytes = base64.b64decode(content_bytes)

    # Save to CWD
    filepath = os.path.join(os.getcwd(), name)

    with open(filepath, "wb") as f:
        f.write(file_bytes)

    return filepath
