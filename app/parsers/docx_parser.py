from docx import Document
from app.parsers.text_clean import safe_text
#.docx文件读取
def read_docx(file_path):
    doc = Document(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return safe_text(text)