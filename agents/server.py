import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from master_agent import master_graph  # import the graph


app = FastAPI()

# -----------------------------------------
# Email Schema
# -----------------------------------------


class EmailModel(BaseModel):
    subject: str
    body: str
    from_email: str
    to_email: str
    attachments: Optional[List[str]] = None



# -----------------------------------------
# Main route for incoming emails
# -----------------------------------------
@app.post("/incoming-email")
async def incoming_email(email: EmailModel):
    print("🔥 Email received by FastAPI")

    await master_graph.ainvoke({
        "email": {
            "from": email.from_email,
            "to": email.to_email,
            "subject": email.subject,
            "body": email.body,
            "attachments": email.attachments or []
        }
    })

    return {"status": "processed"}

if __name__ == "__main__":
    print("Backend service running at http://localhost:2000")
    uvicorn.run(app, host="0.0.0.0", port=2000)