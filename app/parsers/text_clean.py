from app.utils.pasers_utils import compress_text,clean_text_up
#文件数据简单的清洗
def safe_text(text):
    if not text:
        return ""

    text=text.encode('utf-8','ignore').decode('utf-8')
    text=text.strip()
    text=clean_text_up(text)
    text=compress_text(text)
    return text