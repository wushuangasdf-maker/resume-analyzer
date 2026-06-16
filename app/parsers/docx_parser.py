from docx import Document
import logging
from app.parsers.text_clean import safe_text
from app.utils.decorators import trace

logger = logging.getLogger(__name__)

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
         logger.warning("docx解析失败：%s", e)
         return ""