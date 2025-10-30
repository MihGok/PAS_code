from datasets import load_dataset
import os
from PIL import Image


output_dir = "skin_cancer_images"
os.makedirs(output_dir, exist_ok=True)


dataset = load_dataset("marmal88/skin_cancer", split="train[:100]")
subset = dataset.select(range(100))


for i, example in enumerate(subset):
    image = example['image']
    image_id = example['image_id']
    if image_id:
        filename = f"{image_id}.png"
    else:
        filename = f"image_{i:04d}.png"
    file_path = os.path.join(output_dir, filename)
    image.save(file_path, "PNG")
print(f"Загрузка завершена! {len(subset)} изображений сохранено в директорию '{output_dir}'.")