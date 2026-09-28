import io
import re
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import pytesseract
import fitz  # PyMuPDF for PDF to Image conversion

from chatbot import router as chatbot_router  # <-- naya AI chatbot router (Gemini)

# Tesseract-OCR ka path yahan configured hai
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = FastAPI(title="Documents Analyser API", version="3.12")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chatbot ke saare routes (/chatbot/ask) yahan register ho rahe hain
app.include_router(chatbot_router)


def preprocess_image(image_bytes):
    # OpenCV ka use karke image ko sharp aur clear karna
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Otsu thresholding for sharp text contrast
    processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return Image.fromarray(processed)


@app.post("/extract/")
async def extract_document(
    file: UploadFile = File(...),
    query: str = Form(None),
    is_manual: bool = Form(False),  # <--- True hone par AI/OCR skip ho jayega
):
    try:
        # Agar document manually organized hai, toh AI/OCR processing skip karein
        if is_manual:
            return {
                "status": "success",
                "message": "Yeh document manually organized hai, is par AI processing nahi ki gayi.",
                "document_analysis": {
                    "document_type": "Manual / Pre-sorted Document",
                    "fields": [],
                    "raw_text": "AI/OCR skipped for pre-sorted manual document.",
                },
            }

        # Baaki case mein normal OCR run hoga
        contents = await file.read()
        filename_lower = file.filename.lower()

        # AGAR FILE PDF HAI, TOH USE IMAGE MEIN CONVERT KAREIN
        if filename_lower.endswith(".pdf"):
            pdf_document = fitz.open(stream=contents, filetype="pdf")
            if len(pdf_document) > 0:
                page = pdf_document[0]
                pix = page.get_pixmap(dpi=200)
                image_bytes = pix.tobytes("png")
            else:
                raise HTTPException(status_code=400, detail="Uploaded PDF file is empty.")
        else:
            image_bytes = contents

        processed_image = preprocess_image(image_bytes)
        processed_image.thumbnail((1200, 1200))
        img_w, img_h = processed_image.size

        custom_config = r'--oem 3 --psm 3'
        raw_text = pytesseract.image_to_string(processed_image, config=custom_config)
        ocr_data = pytesseract.image_to_data(
            processed_image, config=custom_config, output_type=pytesseract.Output.DICT
        )

        text_upper = raw_text.upper()

        # Document Type Detection
        if any(keyword in text_upper for keyword in ["INVOICE", "BILL", "HSN", "QTY", "TAX", "TOTAL", "RECEIPT"]):
            doc_type = "Invoice / Bill"
        elif "PAN" in text_upper or "INCOME TAX" in text_upper:
            doc_type = "PAN Card"
        elif "AADHAAR" in text_upper or "GOVERNMENT OF INDIA" in text_upper:
            doc_type = "Aadhaar Card"
        elif "DRIVING" in text_upper or "LICENCE" in text_upper:
            doc_type = "Driving License"
        else:
            doc_type = "General Document"

        extracted_fields = []
        n_boxes = len(ocr_data['text'])

        # Saare words ke boxes return karein (UI highlighting ke liye).
        # Chatbot ka asli jawab (ai_answer) ab /chatbot/ask se aata hai,
        # is endpoint se nahi.
        for i in range(n_boxes):
            word = ocr_data['text'][i].strip()
            conf = int(ocr_data['conf'][i])

            if word and conf > 10:
                x, y = ocr_data['left'][i], ocr_data['top'][i]
                w, h = ocr_data['width'][i], ocr_data['height'][i]

                if w > 1 and h > 1:
                    ymin = int((y / img_h) * 1000)
                    xmin = int((x / img_w) * 1000)
                    ymax = int(((y + h) / img_h) * 1000)
                    xmax = int(((x + w) / img_w) * 1000)

                    extracted_fields.append({
                        "label": "Text",
                        "value": word,
                        "box_2d": [ymin, xmin, ymax, xmax],
                    })

        return {
            "status": "success",
            "document_analysis": {
                "document_type": doc_type,
                "fields": extracted_fields,
                "raw_text": raw_text,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)