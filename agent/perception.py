"""
Agent Perception Module
Analyzes image quality, detects document type, and produces a perception report.
"""

import cv2
import numpy as np
from PIL import Image


def analyze_image(image: Image.Image) -> dict:
    """
    Perceive the input image and return a structured quality/type report.
    Returns:
        doc_type: 'printed' | 'handwritten' | 'mixed' | 'form'
        quality:  'high' | 'medium' | 'low'
        issues:   list of detected issues
        metrics:  raw numeric metrics
    """
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    h, w = gray.shape
    issues = []

    # --- Blur / sharpness ---
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 50:
        issues.append("Image is blurry")

    # --- Brightness ---
    mean_brightness = float(np.mean(gray))
    if mean_brightness < 60:
        issues.append("Image is too dark")
    elif mean_brightness > 210:
        issues.append("Image is overexposed")

    # --- Contrast ---
    contrast = float(gray.std())
    if contrast < 30:
        issues.append("Low contrast detected")

    # --- Resolution ---
    if h < 400 or w < 400:
        issues.append("Low resolution image")

    # --- Noise estimation ---
    noise = _estimate_noise(gray)

    # --- Document type heuristic ---
    doc_type = _classify_doc_type(gray, laplacian_var)

    # --- Overall quality ---
    quality = _score_quality(laplacian_var, contrast, mean_brightness, noise)

    return {
        "doc_type": doc_type,
        "quality": quality,
        "issues": issues,
        "metrics": {
            "sharpness": round(laplacian_var, 2),
            "brightness": round(mean_brightness, 2),
            "contrast": round(contrast, 2),
            "noise": round(noise, 2),
            "resolution": f"{w}x{h}"
        }
    }


def _estimate_noise(gray: np.ndarray) -> float:
    """Estimate noise level using high-frequency content."""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    diff = cv2.absdiff(gray, blurred)
    return float(diff.mean())


def _classify_doc_type(gray: np.ndarray, sharpness: float) -> str:
    """
    Heuristic classification:
    - High sharpness + uniform strokes → printed
    - Low sharpness / irregular strokes → handwritten
    """
    # Edge density as proxy for stroke regularity
    edges = cv2.Canny(gray, 50, 150)
    edge_density = edges.mean()

    if sharpness > 300 and edge_density > 5:
        return "printed"
    elif sharpness < 100:
        return "handwritten"
    else:
        return "mixed"


def _score_quality(sharpness: float, contrast: float, brightness: float, noise: float) -> str:
    score = 0
    if sharpness > 200:
        score += 2
    elif sharpness > 80:
        score += 1

    if contrast > 60:
        score += 2
    elif contrast > 35:
        score += 1

    if 80 <= brightness <= 200:
        score += 2
    elif 60 <= brightness <= 220:
        score += 1

    if noise < 5:
        score += 1

    if score >= 6:
        return "high"
    elif score >= 3:
        return "medium"
    else:
        return "low"
