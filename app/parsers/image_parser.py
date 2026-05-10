from PIL import Image
import pytesseract
from app.parsers.text_clean import safe_text


def read_image(image_path):
    try:
        img = Image.open(image_path)

        text = pytesseract.image_to_string(
            img,
            lang="chi_sim+eng"
        )

        return safe_text(text)

    except Exception as e:
        return {"error": str(e)}