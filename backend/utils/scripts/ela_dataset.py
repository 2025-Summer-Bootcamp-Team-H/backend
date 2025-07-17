import os
from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image

class ELAImageDataset(Dataset):
    def __init__(self, root_dir):
        self.samples = []
        for label, sub in enumerate(['Original', 'Tampered']):
            folder = os.path.join(root_dir, sub)
            for fname in os.listdir(folder):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                    self.samples.append((os.path.join(folder, fname), label))
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert('RGB')
        return self.transform(img), label

# 사용 예시
if __name__ == "__main__":
    dataset = ELAImageDataset("normal_ela")
    print("총 샘플 수:", len(dataset))
    img, label = dataset[0]
    print("첫번째 샘플 shape:", getattr(img, "shape", None), "라벨:", label)