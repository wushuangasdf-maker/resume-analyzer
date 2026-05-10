#经行文本项目的提取
def extract_projects(text):
    projects=[]
    # 按关键词切分（简单策略）
    lines =text.split("\n")
    for line in lines:
        if "项目" in line or "Project" in line:
            projects.append(line.strip())
    return projects[:5]