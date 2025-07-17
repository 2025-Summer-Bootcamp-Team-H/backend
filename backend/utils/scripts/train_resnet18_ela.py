import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import models
from ela_dataset import ELAImageDataset

# 하이퍼파라미터
BATCH_SIZE = 32
EPOCHS = 5
LR = 1e-4

# 데이터셋 및 DataLoader
dataset = ELAImageDataset("normal_ela")
dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

# 모델 준비
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = models.resnet18(pretrained=True)
model.fc = nn.Linear(model.fc.in_features, 2)
model = model.to(device)

# 손실함수/옵티마이저
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=LR)

# 학습 루프
for epoch in range(EPOCHS):
    model.train()
    running_loss = 0.0
    for imgs, labels in dataloader:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(imgs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item() * imgs.size(0)
    avg_loss = running_loss / len(dataset)
    print(f"Epoch {epoch+1}/{EPOCHS} - Loss: {avg_loss:.4f}")

# 모델 저장
torch.save(model.state_dict(), "resnet18_ela.pth")
print("모델 저장 완료: resnet18_ela.pth")