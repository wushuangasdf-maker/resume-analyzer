#文件数据简单的清洗
def safe_text(text):
    if not text:
        return ""

    text=text.encode('utf-8','ignore').decode('utf-8')

    text=text.strip()
    return text