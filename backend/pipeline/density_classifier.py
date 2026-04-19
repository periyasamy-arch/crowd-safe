import logging
import os
from typing import Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

logger = logging.getLogger(__name__)

CLASS_NAMES       = ["LOW", "MEDIUM", "HIGH"]
IMG_SIZE          = 224
MAX_DENSITY_VALUE = 50

_TRANSFORM = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std =[0.229, 0.224, 0.225]
    ),
])


class _DensityNet(nn.Module):
    def __init__(self, num_classes: int = 3):
        super().__init__()
        backbone        = models.resnet18(weights=None)
        self.features   = nn.Sequential(*list(backbone.children())[:-1])
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


class DensityClassifier:
    def __init__(self, checkpoint_path: str = None, device: str = "cpu"):
        self.device        = torch.device(device)
        self.model         = None
        self.fallback_mode = True

        if checkpoint_path and os.path.isfile(checkpoint_path):
            self._load(checkpoint_path)
        else:
            logger.warning(
                f"[DensityClassifier] No checkpoint at '{checkpoint_path}'. "
                "Using heuristic fallback."
            )

    def _load(self, path: str):
        try:
            model = _DensityNet(num_classes=3)
            state = torch.load(path, map_location=self.device)
            if isinstance(state, dict) and "model_state_dict" in state:
                state = state["model_state_dict"]
            model.load_state_dict(state)
            model.eval()
            model.to(self.device)
            self.model         = model
            self.fallback_mode = False
            logger.info(f"[DensityClassifier] Loaded: {path}")
        except Exception as e:
            logger.error(f"[DensityClassifier] Load failed: {e}")
            self.fallback_mode = True

    def _fallback_classify(self, frame: np.ndarray) -> Tuple[str, float]:
        gray     = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        lap      = cv2.Laplacian(gray, cv2.CV_64F)
        variance = float(np.var(lap))
        if variance < 200:
            return "LOW",    1.0
        elif variance < 800:
            return "MEDIUM", 1.0
        else:
            return "HIGH",   1.0

    def classify(self, frame: np.ndarray) -> Tuple[str, float]:
        if self.fallback_mode or self.model is None:
            return self._fallback_classify(frame)
        try:
            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            tensor = _TRANSFORM(Image.fromarray(rgb)).unsqueeze(0).to(self.device)
            with torch.no_grad():
                probs = torch.softmax(self.model(tensor), dim=1)
                idx   = int(probs.argmax(dim=1).item())
                conf  = float(probs[0, idx].item())
            return CLASS_NAMES[idx], conf
        except Exception as e:
            logger.error(f"[DensityClassifier] Inference error: {e}")
            return self._fallback_classify(frame)

    @property
    def using_cnn(self) -> bool:
        return not self.fallback_mode

    @property
    def max_density_value(self) -> int:
        return MAX_DENSITY_VALUE