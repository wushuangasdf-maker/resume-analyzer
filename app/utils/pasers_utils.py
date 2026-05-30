
import re
Max_length = 6000



def clean_text_up(text):
    if not text:
        return ""
    #目的：去掉首位的空白
    text =text.strip()
    # 目的：将多空格经行压缩
    text = re.sub(r"[\t]+","",text)
    # 目的：将多换行经行压缩
    text = re.sub(r"\n{2,}","\n",text)
    # 目的：删去特殊字符
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    # 目的：去除重复的分隔符
    text = re.sub(r"[-_=]{3,}", "", text)
    return text

def compress_text(text):
    text = clean_text_up(text)
    if len(text)<=Max_length:
        return text
    head = text[:4000]
    tail = text[-2000:]
    return head+"\n....\n"+tail