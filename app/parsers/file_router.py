from app.parsers.pdf_parser import read_pdf
from app.parsers.docx_parser import read_docx
from app.parsers.image_parser import read_image

#文件的判断
def parse_resume(file_path):
    if file_path.endswith(".pdf"):
        return read_pdf(file_path)
    elif file_path.endswith(".docx"):
        return read_docx(file_path)
    elif file_path.endswith((".png",".jpg",".jpeg")):
        return read_image(file_path)
    else:
        raise ValueError("仅支持PDF,DOCX和图片")