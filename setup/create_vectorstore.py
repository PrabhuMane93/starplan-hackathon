from openai import OpenAI

client = OpenAI()
vector_store = client.vector_stores.create(
    name="EOI_Documents_VS",
)
client.vector_stores.list()