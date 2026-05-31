from docx import Document
from app.parsers.text_clean import safe_text
from app.utils.decorators import trace
#.docx文件读取
@trace
def read_docx(file_path):
     try:
      doc = Document(file_path)
      text = ""
      for para in doc.paragraphs:
          text += para.text + "\n"
      return safe_text(text)
     except Exception as e:
         print(f"docx解析失败:{e}")
         return ""