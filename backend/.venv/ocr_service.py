import pytesseract
from PIL import Image
import os

# Tesseract ka path yahan active kar diya hai
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_image(image_path: str) -> str:
    try:
        if not os.path.exists(image_path):
            return "Error: Image file not found."
        
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        return f"OCR Error: {str(e)}"