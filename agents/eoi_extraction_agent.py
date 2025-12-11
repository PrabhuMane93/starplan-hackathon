import os
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from convert_document import save_pdf_from_content_bytes

load_dotenv()

class PurchaserModel(BaseModel):
    First_Name: str
    Last_Name: str
    Purchaser_Email: str
    Purchaser_Mobile: str


class EOIExtractedModel(BaseModel):
    Purchaser: List[PurchaserModel]
    Residential_Address: str
    Lot_Number: str
    Property_Address: str
    Project_Name: str
    Total_Price: str
    Land_Price: str
    Build_Price: str
    Finance_Terms: str
    Solicitor_Name: str
    Solicitor_Email: str
    Finance_Provider: Optional[str] = None


def upload_file_to_openai(client, file_path: str):
    with open(file_path, "rb") as f:
        uploaded = client.files.create(
            file=f,
            purpose="assistants"   # required for responses API
        )
    return uploaded.id

def ingest_eoi_to_vector_store(EOI_JSON, sender_email):
    client = OpenAI()
    vector_store_id = os.getenv("OPENAI_VS_ID")
    with open("temp.txt", "w", encoding="utf-8") as f:
        f.write(EOI_JSON)
    response = client.vector_stores.files.upload_and_poll(vector_store_id=vector_store_id,
                                                        file=open("temp.txt", "rb"),
                                                        attributes=
                                                            {
                                                                "sender_email": sender_email,                                                  
                                                            }
                                                        ,                                                        
                                                        poll_interval_ms=2000)
    os.remove("temp.txt")
    return response


def eoi_extractor(state):
    email = state["email"]

    attachments = email.get("attachments")
    from_email  = email.get("from")
    body        = email.get("body")

    client = OpenAI()

    for attachment in attachments:
        pdf_path = attachment

    # 1️⃣ Upload file first → get file_id
    file_id = upload_file_to_openai(client, pdf_path)
    os.remove(pdf_path)

    PROMPT_TEMPLATE = """
    You are an expert document extraction AI. You will be given:

    1. An Expression of Interest (EOI) PDF.
    2. The full email body that accompanied the EOI PDF:
    ---
    {email_text}
    ---

    Your job:

    Extract ONLY the following fields and output **VALID JSON** in EXACTLY this structure:

    {{
    "Purchaser":[
        {{
            "First_Name": "<str>",
            "Last_Name": "<str>",
            "Purchaser_Email": "<str>",
            "Purchaser_Mobile": "<str>"
        }}
    ],
    "Residential_Address": "<str>",
    "Lot_Number": "<str>",
    "Property_Address": "<str>",
    "Project_Name": "<str>",
    "Total_Price": "<str>",
    "Land_Price": "<str>",
    "Build_Price": "<str>",
    "Finance_Terms": "<str>",
    "Solicitor_Name": "<str>",
    "Solicitor_Email": "<str>",
    "Finance_Provider": "<str or null>"
    }}

    Rules:

    1. Extract fields **from the PDF first**.
    2. If a field is missing in the PDF, search for it in the accompanying email text.
    3. If still missing, return an empty string (""), EXCEPT:
    - Finance_Provider → return null when not available.
    4. DO NOT add any extra keys.
    5. Purchaser should be a list of objects, even if there is only one.
    6. Return only the JSON. No explanation or markdown.
    """

    prompt = PROMPT_TEMPLATE.format(email_text=body)

    # 2️⃣ Reference the file via file_id in the input
    response = client.responses.parse(
        model="gpt-4.1",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_file", "file_id": file_id}
                ]
            }
        ],
        text_format=EOIExtractedModel  # Pydantic automatic validation!
    )
    ingest_eoi_to_vector_store(response.output_text, from_email)

    return state

