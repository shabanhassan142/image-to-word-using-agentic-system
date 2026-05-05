"""
Agent Decision Module
Selects the optimal preprocessing strategy and OCR config based on perception report.
Also checks long-term memory for learned preferences.
"""

from agent.memory import get_preference

# Strategy definitions
STRATEGIES = {
    "aggressive_denoise": {
        "description": "Heavy denoising + high contrast boost (best for noisy/handwritten)",
        "clahe_clip": 4.0,
        "blur_kernel": (3, 3),
        "adaptive_block": 21,
        "adaptive_c": 8,
        "morph_kernel": (2, 2),
        "ocr_psm": 6,
        "ocr_oem": 1,
    },
    "standard": {
        "description": "Balanced preprocessing (best for medium quality printed docs)",
        "clahe_clip": 3.0,
        "blur_kernel": (1, 1),
        "adaptive_block": 15,
        "adaptive_c": 10,
        "morph_kernel": (1, 1),
        "ocr_psm": 6,
        "ocr_oem": 3,
    },
    "light_enhance": {
        "description": "Minimal processing (best for high quality printed docs)",
        "clahe_clip": 2.0,
        "blur_kernel": (1, 1),
        "adaptive_block": 11,
        "adaptive_c": 12,
        "morph_kernel": (1, 1),
        "ocr_psm": 3,
        "ocr_oem": 3,
    },
    "handwritten": {
        "description": "Optimized for handwritten text (high contrast, LSTM OCR)",
        "clahe_clip": 5.0,
        "blur_kernel": (3, 3),
        "adaptive_block": 25,
        "adaptive_c": 6,
        "morph_kernel": (2, 2),
        "ocr_psm": 6,
        "ocr_oem": 1,
    },
}


def select_strategy(perception: dict) -> tuple[str, str]:
    """
    Returns (strategy_name, reason) based on perception report and memory.
    """
    doc_type = perception["doc_type"]
    quality = perception["quality"]

    # Check long-term memory first
    learned = get_preference(doc_type)
    if learned and learned.get("success_count", 0) >= 2:
        strategy_name = learned["strategy"]
        reason = f"Learned from {learned['success_count']} previous successful conversions of '{doc_type}' documents."
        return strategy_name, reason

    # Rule-based decision
    if doc_type == "handwritten":
        strategy_name = "handwritten"
        reason = "Handwritten document detected — using LSTM OCR with aggressive contrast enhancement."
    elif quality == "low":
        strategy_name = "aggressive_denoise"
        reason = "Low quality image detected — applying heavy denoising and contrast boost."
    elif quality == "high" and doc_type == "printed":
        strategy_name = "light_enhance"
        reason = "High quality printed document — minimal preprocessing to preserve detail."
    else:
        strategy_name = "standard"
        reason = "Mixed or medium quality document — using balanced preprocessing pipeline."

    return strategy_name, reason


def get_strategy_config(strategy_name: str) -> dict:
    return STRATEGIES.get(strategy_name, STRATEGIES["standard"])
