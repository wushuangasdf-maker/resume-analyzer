#经行文本项目的提取
import re


def extract_projects(text):
    if not text or not text.strip():
        return []
    projects = []
    seen = set()
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    keywords=["项目",
        "project",
        "projects",
        "项目经历",
        "科研项目",
        "毕业设计"]
    for line in lines:
        line_lower=line.lower()
        if any(keyword.lower() in line_lower for keyword in keywords):
            cleaned = re.sub(r"\s","",line).strip()
            if len(cleaned)>120:
                continue
            key = cleaned.lower()
            if key in seen:
                seen.add(key)
                projects.append(cleaned)
            if len(projects) >= 5:
                break
    return projects
