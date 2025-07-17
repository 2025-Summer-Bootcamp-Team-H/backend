# backend/services/forgery_detector.py

import torch
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import os

# 1. 모델 로딩
resnet_model = models.resnet18()
resnet_model.fc = torch.nn.Linear(resnet_model.fc.in_features, 2)

# 학습된 가중치 불러오기 (경로는 실제 pth 파일 위치에 맞게 수정)
resnet_model.load_state_dict(torch.load("resnet18_ela.pth", map_location="cpu"))
resnet_model.eval()  # 추론 모드

# 2. 이미지 전처리 (ResNet 입력 맞춤)
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

# 3. 위조 여부 판단 함수
def predict_forgery(ela_image: Image.Image) -> dict:
    """
    ELA 이미지 입력 → 위조 여부 판별 결과 반환

    :param ela_image: ELA 전처리된 PIL 이미지
    :return: {
        "is_forged": True/False,
        "confidence": 0.932,
        "predicted_class": "forged" or "authentic"
    }
    """
    tensor_img = transform(ela_image)
    if not isinstance(tensor_img, torch.Tensor):
        tensor_img = transforms.ToTensor()(tensor_img)
    input_tensor = tensor_img.unsqueeze(0)
    with torch.no_grad():
        output = resnet_model(input_tensor)
        probs = torch.softmax(output, dim=1)
        confidence, pred_class = torch.max(probs, 1)

    return {
        "is_forged": bool(pred_class.item()),  # 0: 정상, 1: 위조
        "confidence": round(confidence.item(), 4),
        "predicted_class": "forged" if pred_class.item() == 1 else "authentic"
    }
