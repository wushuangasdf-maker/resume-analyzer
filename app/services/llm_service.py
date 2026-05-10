from openai import OpenAI

client=OpenAI(
    api_key="sk-d697de97068045b69588fac00c694320",
    base_url="https://api.deepseek.com/v1"
)

def chat(prompt):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role":"user","content":prompt}
        ],
        temperature=0
    )
    return response.choices[0].message.content