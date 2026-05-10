import json
import re


def clean_json(text):
    text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        text = text[start:end+1]

    return text

def safe_json_loads(response,fallback=None):
    if fallback in None:
        fallback={}
    try:
        response =response.strip()
        response = re.sub(r"^```json\s*", "", response)
        response = re.sub(r"^```\s*", "", response)
        response = re.sub(r"\s*```$", "", response)
        start = response.find("{")
        end =response.find("}")
        if start != -1 and end !=-1:
            response =response[start:end + 1]
        data =json.loads((response))
        if isinstance(data,dict):
            return data
        return fallback
    except Exception:
        return fallback