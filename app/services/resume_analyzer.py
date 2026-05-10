import json
from app.services.llm_service import chat
from app.utils.json_utils import clean_json

#将文本经行分析处理然后以JSON格式的方式返回
def analyze_resume_structured(data):
    prompt=f"""
    请基于以下结构化简历信息进行分析：
    {json.dumps(data,ensure_ascii=False)}
    请严格输出JSON格式:
    {{
    1. 评分(参考岗位匹配分数)：0-100
    2. 优点
    3. 缺点
    4. 推荐岗位
    5. 技能情况
    }}
"""
    result = chat(prompt)
    result = clean_json(result)
    try:
        return json.loads(result)
    except:
        return {"raw":result}
#综合引用
def analyze_resume_v2(text):

    result = analyze_resume_structured(text)
    if isinstance(result,str):
        result=clean_json(result)
        try:
            result=json.loads(result)
        except:
            return {"raw": result}
    return  result