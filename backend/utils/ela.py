# backend/utils/ela.py

from PIL import Image, ImageChops, ImageEnhance
import os
import uuid
from typing import Union

def convert_to_ela_image(image: Union[str, Image.Image], quality: int = 90) -> Image.Image:
    """
    이미지 경로(str) 또는 PIL.Image.Image 객체를 받아서 ELA (Error Level Analysis) 이미지로 변환

    :param image: 원본 이미지 파일 경로(str) 또는 PIL.Image.Image 객체
    :param quality: JPEG 저장 품질 (보통 90 사용)
    :return: 조작 여부 분석에 사용할 ELA 이미지 객체
    """
    # 1. 원본 이미지 열기
    if isinstance(image, str):
        original = Image.open(image).convert("RGB")
    else:
        original = image.convert("RGB")

    # 2. JPEG로 재저장 (압축)
    temp_filename = f"temp_ela_{uuid.uuid4().hex}.jpg"
    original.save(temp_filename, "JPEG", quality=quality)

    # 3. 재저장된 이미지 다시 열기
    compressed = Image.open(temp_filename)

    # 4. 차이 계산 (편집 흔적 강조)
    diff = ImageChops.difference(original, compressed)

    # 5. 차이값에 따라 밝기 증가시켜 시각화
    extrema = diff.getextrema()
    # Robust handling for both RGB and grayscale
    if isinstance(extrema, tuple) and isinstance(extrema[0], tuple):  # RGB
        max_diff = max([ex[1] for ex in extrema if isinstance(ex, tuple)])
    elif isinstance(extrema, tuple) and len(extrema) == 2 and all(isinstance(x, (int, float)) for x in extrema):  # Grayscale
        max_diff = extrema[1]
    else:
        max_diff = 1.0  # fallback
    # Ensure max_diff is a number
    if isinstance(max_diff, tuple):
        max_diff = max_diff[1] if len(max_diff) > 1 else 1.0
    if not isinstance(max_diff, (int, float)):
        max_diff = 1.0
    scale = 255.0 / max_diff if max_diff != 0 else 1.0
    ela_image = ImageEnhance.Brightness(diff).enhance(scale)

    # 6. 임시 파일 삭제
    os.remove(temp_filename)

    return ela_image
