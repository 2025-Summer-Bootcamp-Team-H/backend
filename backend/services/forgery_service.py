import sys
import os
from pathlib import Path
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.ela import convert_to_ela_image
from services.forgery_detector import predict_forgery

def analyze_forgery_from_local_path(image_path: str) -> dict:
    """
    로컬 이미지 경로를 받아 위조분석 결과 반환
    """
    path_obj = Path(image_path)
    if path_obj.is_absolute():
        full_path = path_obj
    else:
        BASE_DIR = Path(__file__).resolve().parent.parent
        full_path = BASE_DIR / image_path

    if not full_path.exists():
        raise FileNotFoundError(f"파일이 존재하지 않습니다: {full_path}")

    img = Image.open(full_path)
    ela_image = convert_to_ela_image(img)
    result = predict_forgery(ela_image)
    return result


# 여러분이 가진 테스트 이미지 경로
# image_path = "C:/sample/test_f.jpg"
# result = analyze_forgery_from_local_path(image_path)
# print(result)