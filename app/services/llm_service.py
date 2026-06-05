from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

Api_key=os.getenv("DEEPSEEK_API_KEY")
if not Api_key:
    raise ValueError("未找到API_KEY，请去检查.env文件")

client=OpenAI(
    api_key=Api_key,
    base_url="https://api.deepseek.com/v1",
    timeout=60
)

def chat(prompt):
    if not prompt or not prompt.strip():
        return ""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role":"user","content":prompt}
        ],
        temperature=0
    )
    content=response.choices[0].message.content
    return content.strip() if content else ""


def chat_stream(prompt):
    """流式调用 LLM，逐 token 返回文本块"""
    if not prompt or not prompt.strip():
        yield ""
        return
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        stream=True,
    )
    for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            yield content