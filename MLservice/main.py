# main.py — prediction service entrypoint
import os
import io
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

import torch
import torch.nn.functional as F
from transformers import AutoImageProcessor, AutoModelForImageClassification
from PIL import Image

load_dotenv()

MODEL_DIR = os.getenv("MODEL_DIR", "C:\\Users\\root\\Desktop\\model_skin_trans")
if not MODEL_DIR:
    raise RuntimeError("Переменная окружения MODEL_DIR не установлена. Установите MODEL_DIR перед запуском сервиса.")

MODEL_DIR = Path(MODEL_DIR)
if not MODEL_DIR.exists():
    raise RuntimeError(f"MODEL_DIR='{MODEL_DIR}' не существует или путь неверен.")

app = FastAPI(title="Prediction Service", version="1.0")

# глобальные объекты модели/процессора
processor = None
model = None
device = "cpu"
id2label_fn = None
_model_loaded = False


class PredictResponse(BaseModel):
    label: str
    index: int
    confidence: float
    probabilities: List[float]


def _safe_id2label(config):
    """Возвращает функцию index->label на основе config.id2label"""
    id2label = getattr(config, "id2label", None)
    if not id2label:
        return lambda i: str(i)
    keys = list(id2label.keys())
    if len(keys) == 0:
        return lambda i: str(i)
    first_key = keys[0]
    if isinstance(first_key, str):
        return lambda i: id2label.get(str(i), str(i))
    return lambda i: id2label.get(i, str(i))


@app.on_event("startup")
def load_model():
    global processor, model, device, id2label_fn, _model_loaded
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        processor = AutoImageProcessor.from_pretrained(str(MODEL_DIR))
        model = AutoModelForImageClassification.from_pretrained(str(MODEL_DIR))
        model.to(device)
        model.eval()
        id2label_fn = _safe_id2label(model.config)
        _model_loaded = True
        print(f"[startup] Loaded model from {MODEL_DIR} on device {device}")
    except Exception as e:
        _model_loaded = False
        # пробрасываем ошибку, чтобы сервис не стартовал "тихо"
        raise RuntimeError(f"Не удалось загрузить модель из {MODEL_DIR}: {e}")


def read_image_from_bytes(b: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(b)).convert("RGB")
        return img
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Не удалось прочитать изображение: {e}")


@app.post("/predict", response_model=PredictResponse)
async def predict(image_file: UploadFile = File(...)):
    """
    Принимает multipart/form-data с полем image_file и возвращает:
    {
      "label": "<строка метки>",
      "index": <int>,
      "confidence": <float>,
      "probabilities": [float,...]
    }
    """
    if not _model_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded")

    content = await image_file.read()
    image = read_image_from_bytes(content)

    # preprocess
    inputs = processor(images=image, return_tensors="pt")
    # перенос на устройство
