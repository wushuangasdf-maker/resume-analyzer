from PyPDF2 import PdfReader
import logging
from app.parsers.text_clean import safe_text
from app.utils.decorators import trace

logger = logging.getLogger(__name__)

#pdf文件的读取
@trace
def read_pdf(file_path):
    try:
      reader = PdfReader(file_path)
      text=""
      for page in reader.pages:
          content = page.extract_text()
          if content:
              text +=content + "\n"
      return safe_text(text)
    except Exception as e:
        logger.warning("pdf解析失败：%s", e)
        return ""
