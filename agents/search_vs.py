import os
import json
from openai import OpenAI
from dotenv import load_dotenv


def search_vector_store(email: str):
    load_dotenv()
    vector_store_id = os.getenv("OPENAI_VS_ID")
    client = OpenAI()

    query = """
    Extract the purchaser(s) name and property address from the following email regarding the Contract of Sale:
    ```
    {email}
    ```
    In the following Format:
    Purchaser(s) Name: <Full Name(s)>
    Property Address: <Full Address>
    """
    response = client.chat.completions.create(
        model="gpt-4.1-mini",   # or your preferred model
        messages=[
            {"role": "user", "content": query.format(email=email)}
        ],
        temperature=0.2
    )

    results = client.vector_stores.search(
        vector_store_id=vector_store_id,
        query=response.choices[0].message.content,
        max_num_results=1)

    res = json.loads(results.data[0].content[0].text)
    return res