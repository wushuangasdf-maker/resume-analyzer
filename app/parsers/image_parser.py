from PIL import Image
import pytesseract
import logging
from app.parsers.text_clean import safe_text
from app.utils.decorators import trace

logger = logging.getLogger(__name__)

@trace
def read_image(image_path):
    try:
        img = Image.open(image_path)

        text = pytesseract.image_to_string(
            img,
            lang="chi_sim+eng"
        )

        return safe_text(text)

    except Exception as e:
        logger.warning("图片解析失败：%s", e)
        return ""