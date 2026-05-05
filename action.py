"""
Agent Action Module
Executes the chosen preprocessing strategy and runs OCR.
Returns extracted text, confidence scores, and formatting info.
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import platform

# Configure Tesseract path on Windows
if platform.system() == "Windows":
    for path in [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe".format(os.getenv("USERNAME", "")),
    ]:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break


def preprocess(image: Image.Image, config: dict) -> np.ndarray:
    """Apply the strategy config to the image and return a processed numpy array."""
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img

    # Upscale if too small
    h, w = gray.shape
    if h < 1000:
        scale = 1000 / h
        gray = cv2.resize(gray, (int(w * scale), 1000), interpolation=cv2.INTER_CUBIC)

    # Blur
    k = config["blur_kernel"]
    if k[0] > 1:
        gray = cv2.GaussianBlur(gray, k, 0)

    # CLAHE contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=config["clahe_clip"], tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Adaptive threshold
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        config["adaptive_block"],
        config["adaptive_c"]
    )

    # Morphological cleanup
    mk = config["morph_kernel"]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, mk)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Final median blur
    binary = cv2.medianBlur(binary, 3)
    return binary


def run_ocr(processed_img: np.ndarray, config: dict) -> dict:
    """
    Run Tesseract OCR and return:
      - plain_text
      - word_data (list of word dicts with confidence, bbox)
      - avg_confidence
      - low_confidence_words (confidence < 60)
    """
    ocr_config = f"--oem {config['ocr_oem']} --psm {config['ocr_psm']}"

    try:
        data = pytesseract.image_to_data(
            processed_img,
            output_type=pytesseract.Output.DICT,
            config=ocr_config
        )
        plain_text = pytesseract.image_to_string(processed_img, config=ocr_config)

        word_data = []
        confidences = []
        low_conf_words = []

        for i in range(len(data["text"])):
            word = data["text"][i].strip()
            conf = int(data["conf"][i])
            if word and conf > 0:
                entry = {
                    "text": word,
                    "conf": conf,
                    "left": data["left"][i],
                    "top": data["top"][i],
                    "width": data["width"][i],
                    "height": data["height"][i],
                }
                word_data.append(entry)
                confidences.append(conf)
                if conf < 60:
                    low_conf_words.append(entry)

        avg_conf = round(sum(confidences) / len(confidences), 1) if confidences else 0.0

        return {
            "plain_text": plain_text,
            "word_data": word_data,
            "avg_confidence": avg_conf,
            "low_confidence_words": low_conf_words,
        }

    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "TESSERACT_NOT_FOUND"
        )
    except Exception as e:
        raise RuntimeError(f"OCR failed: {e}")
