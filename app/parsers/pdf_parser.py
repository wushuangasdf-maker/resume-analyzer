from PyPDF2 import PdfReader
from app.parsers.text_clean import safe_text
from app.utils.decorators import trace
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
        print(f"pdf解析失败：{e}")
        return ""
