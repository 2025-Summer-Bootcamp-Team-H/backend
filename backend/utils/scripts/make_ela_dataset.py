import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.ela import convert_to_ela_image
from PIL import Image

def save_ela_images(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    print(f"입력 폴더: {input_dir}, 출력 폴더: {output_dir}")
    for fname in os.listdir(input_dir):
        print(f"처리 시도: {fname}")  # 추가
        if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
            try:
                img = Image.open(os.path.join(input_dir, fname))
                ela_img = convert_to_ela_image(img)
                ela_img.save(os.path.join(output_dir, fname))
                print(f"성공: {fname}")
            except Exception as e:
                print(f"Error processing {fname}: {e}")
        else:
            print(f"확장자 무시: {fname}")

if __name__ == "__main__":
    # 폴더명에 맞게 경로 지정
    base_in = "normal"
    base_out = "normal_ela"

    for sub in ["Original", "Tampered"]:
        in_dir = os.path.join(base_in, sub)
        out_dir = os.path.join(base_out, sub)
        save_ela_images(in_dir, out_dir)

    print("ELA 변환 완료!")