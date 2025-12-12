from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, Any
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

# Import other agents
from eoi_extraction_agent import eoi_extractor
from contract_checker_agent import contract_checker
from signing_agent import signing_agent
from sla_agent import sla_check
from void_agent import void

class RouterOutput(BaseModel):
    route: str

# ------------------------------------------------------
# Shared state structure
# ------------------------------------------------------
class MemoryState(TypedDict):
    email: Dict[str, Any]

# ------------------------------------------------------
# Master agent node
# ------------------------------------------------------
def master_agent_node(state: MemoryState) -> MemoryState:
    email = state["email"]

    print("\n📨 MASTER AGENT RECEIVED EMAIL")
    print("-----------------------------------")
    print("From:", email.get("from"))
    print("To:", email.get("to"))
    print("Subject:", email.get("subject"))
    print("Body:", email.get("body"))
    print("-----------------------------------\n")   

    attachments = email.get("attachments")
    from_email  = email.get("from")
    to_email    = email.get("to")
    subject     = email.get("subject")
    body        = email.get("body")

    llm = ChatOpenAI(model="gpt-4.1-mini")

    ROUTING_PROMPT = """
    You are the MASTER ROUTER AGENT for OneCorp Australia.

    Based ONLY on the email's subject, body, and attachments,
    route the email to the correct agent.

    Possible routes:

    1. EOI_EXTRACTOR  
    - If the email contains an Expression of Interest PDF.
    - Keywords: "EOI", "Expression of Interest", "Signed EOI".
    - Attachment name usually contains "EOI".

    2. CONTRACT_CHECKER  
    - Email from vendor containing a Contract PDF.
    - Keywords: "Contract of Sale", "Contract Request", "RE: Contract".
    - Attachment is usually a contract PDF.

    3. SIGNING_DATE
    - Email from Solicitor
    - Completed Review of the Contract
    - A Signing date with the client is generated.
    
    4. SIGNING_STATUS  
    - Email from DocuSign
    - Buyer or vendor signing updates
    - Keywords: "buyer has completed signing", "envelope completed",
                "all parties have signed".

    5. OTHER  
    - Anything that does NOT match the above.

    Return a JSON object:

    {
    "route": "<EOI_EXTRACTOR | CONTRACT_CHECKER | SIGNING_DATE | SIGNING_STATUS | OTHER>"
    }
    """
    msgs = [
        {"role": "system", "content": ROUTING_PROMPT},
        {"role": "user", "content": f"Email:\nSubject: {subject}\nBody: {body}"}
    ]

    res = llm.invoke(msgs)
    return RouterOutput.model_validate_json(res.content).dict()


# ------------------------------------------------------
# Compile LangGraph
# ------------------------------------------------------
workflow = StateGraph(MemoryState)
workflow.add_node("router", master_agent_node)
workflow.add_node("EOI_EXTRACTOR", eoi_extractor)
workflow.add_node("CONTRACT_CHECKER", contract_checker)
workflow.add_node("SIGNING_DATE", signing_agent)
workflow.add_node("SIGNING_STATUS", sla_check)
workflow.add_node("OTHER", void)


workflow.set_entry_point("router")

workflow.add_conditional_edges(
    "router",
    lambda out: out["route"],
    {
        "EOI_EXTRACTOR": "EOI_EXTRACTOR",
        "CONTRACT_CHECKER": "CONTRACT_CHECKER",
        "SIGNING_DATE": "SIGNING_DATE",
        "SIGNING_STATUS": "SIGNING_STATUS",
        "OTHER":"OTHER"
    }
)
workflow.add_edge("EOI_EXTRACTOR", END)
workflow.add_edge("CONTRACT_CHECKER", END)
workflow.add_edge("SIGNING_DATE", END)
workflow.add_edge("SIGNING_STATUS", END)
workflow.add_edge("OTHER", END)
master_graph = workflow.compile()
