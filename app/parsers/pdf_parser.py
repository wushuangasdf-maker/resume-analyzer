from PyPDF2 import PdfReader
from app.parsers.text_clean import safe_text
#pdf文件的读取
def read_pdf(file_path):
    reader = PdfReader(file_path)
    text=""
    for page in reader.pages:
        content = page.extract_text()
        if content:
            text +=content + "\n"
        return safe_text(text)