import os
from torch.utils.data import DataLoader
from ela_dataset import ELAImageDataset  # 같은 폴더에 ela_dataset.py가 있다고 가정

if __name__ == "__main__":
    # ELA 변환된 데이터셋 경로
    dataset_dir = "normal_ela"  # PowerShell 위치가 backend/backend일 때

    # 데이터셋 및 DataLoader 생성
    dataset = ELAImageDataset(dataset_dir)
    dataloader = DataLoader(dataset, batch_size=8, shuffle=True)

    # 첫 배치 확인
    for imgs, labels in dataloader:
        print("배치 shape:", imgs.shape)
        print("라벨:", labels)
        break