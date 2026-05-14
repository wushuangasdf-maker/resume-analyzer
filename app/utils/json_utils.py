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
    if fallback is None:
        fallback={}
    if not response:
        return fallback
    try:
        response =str(response).strip()
        response = re.sub(r"^```json\s*", "", response)
        response = re.sub(r"^```\s*", "", response)
        response = re.sub(r"\s*```$", "", response)
        match = re.search(r"\{.*\}", response, re.S)
        if match:
            response=match.group()
        data =json.loads(response)
        if isinstance(data,dict):
            return data
        return fallback
    except Exception:
        return fallback