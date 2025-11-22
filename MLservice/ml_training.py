
!pip install -q --upgrade pip
!pip install -q torch torchvision pytorch-lightning transformers datasets wandb evaluate

import os
import json
from pathlib import Path
from typing import Optional, List, Dict

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

import numpy as np
from PIL import Image

from datasets import load_dataset

from transformers import (
    AutoImageProcessor,
    AutoConfig,
    AutoModelForImageClassification,
    get_scheduler,
    default_data_collator,
)

import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.loggers import WandbLogger

import evaluate

SEED = 42
pl.seed_everything(SEED, workers=True)

class HuggingFaceImageDataset(Dataset):
    def __init__(self, hf_ds, image_col: str, label_col: str):
        self.hf_ds = hf_ds
        self.image_col = image_col
        self.label_col = label_col

    def __len__(self):
        return len(self.hf_ds)

    def __getitem__(self, idx):
        item = self.hf_ds[idx]
        return {
            "image": item[self.image_col],
            "label": item[self.label_col],
        }

class SkinCancerDataModule(pl.LightningDataModule):
    def __init__(
        self,
        dataset_name: str = "marmal88/skin_cancer",
        model_checkpoint: str = "google/vit-base-patch16-224",
        batch_size: int = 16,
        num_workers: int = 4,
    ):
        super().__init__()
        self.dataset_name = dataset_name
        self.model_checkpoint = model_checkpoint
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.processor = AutoImageProcessor.from_pretrained(self.model_checkpoint)
        self.hf_ds = None
        self.train_ds = None
        self.val_ds = None
        self.test_ds = None
        self.image_col = None
        self.label_col = None
        self.id2label = None
        self.label2id = None
        self.num_labels = None

    def prepare_data(self):
        load_dataset(self.dataset_name)

    def setup(self, stage: Optional[str] = None):
        self.hf_ds = load_dataset(self.dataset_name)
        splits = list(self.hf_ds.keys())
        if "train" in splits and "validation" in splits and "test" in splits:
            train_ds = self.hf_ds["train"]
            val_ds = self.hf_ds["validation"]
            test_ds = self.hf_ds["test"]
        elif "train" in splits and "test" in splits:
            overall = self.hf_ds["train"]
            overall = overall.train_test_split(test_size=0.1, seed=SEED)
            train_ds = overall["train"]
            val_ds = overall["test"]
            test_ds = self.hf_ds["test"]
        else:
            overall = self.hf_ds[splits[0]]
            overall = overall.train_test_split(test_size=0.15, seed=SEED)
            tmp = overall["train"].train_test_split(test_size=0.15, seed=SEED)
            train_ds = tmp["train"]
            val_ds = tmp["test"]
            test_ds = overall["test"]

        candidates_image = ["image", "img", "image_file_path", "image_path", "image_filepath", "file_path"]
        cols = train_ds.column_names
        image_col = next((c for c in candidates_image if c in cols), None)
        if image_col is None:
            for c in cols:
                sample = train_ds[0][c]
                if isinstance(sample, Image.Image):
                    image_col = c
                    break
        if image_col is None:
            raise RuntimeError(f"Не удалось найти столбец с изображениями. Доступные колонки: {cols}")

        candidates_label = ["label", "labels", "dx", "diagnosis", "diagnosis_label", "target", "label_idx", "class", "label_id"]
        label_col = next((c for c in candidates_label if c in cols), None)
        if label_col is None:
            for c in cols:
                if c == image_col:
                    continue
                uniq = train_ds.unique(c)
                if uniq is None:
                    continue
                if 2 <= len(uniq) <= 50:
                    label_col = c
                    break
        if label_col is None:
            raise RuntimeError(f"Не удалось найти столбец с метками. Доступные колонки: {cols}")

        self.image_col = image_col
        self.label_col = label_col

        train_labels = train_ds.unique(self.label_col)
        labels_str = [str(x) for x in sorted(train_labels, key=lambda x: str(x))]
        self.id2label = {i: lab for i, lab in enumerate(labels_str)}
        self.label2id = {lab: i for i, lab in self.id2label.items()}
        self.num_labels = len(self.id2label)

        def _map_label(example):
            lab = example[self.label_col]
            lab_s = str(lab)
            return {"label": self.label2id[lab_s]}

        train_ds = train_ds.map(_map_label)
        val_ds = val_ds.map(_map_label)
        test_ds = test_ds.map(_map_label)

        self.train_ds = HuggingFaceImageDataset(train_ds, self.image_col, "label")
        self.val_ds = HuggingFaceImageDataset(val_ds, self.image_col, "label")
        self.test_ds = HuggingFaceImageDataset(test_ds, self.image_col, "label")

    def collate_fn(self, batch):
        images = []
        labels = []
        for item in batch:
            img = item["image"]
            if isinstance(img, dict) and "bytes" in img:
                from io import BytesIO
                images.append(Image.open(BytesIO(img["bytes"])).convert("RGB"))
            elif isinstance(img, str):
                images.append(Image.open(img).convert("RGB"))
            elif isinstance(img, Image.Image):
                images.append(img.convert("RGB"))
            else:
                try:
                    arr = np.array(img)
                    images.append(Image.fromarray(arr).convert("RGB"))
                except Exception as e:
                    raise RuntimeError(f"Не удалось преобразовать изображение: {type(img)} -> {e}")
            labels.append(int(item["label"]))
        inputs = self.processor(images=images, return_tensors="pt")
        inputs["labels"] = torch.tensor(labels, dtype=torch.long)
        return inputs

    def train_dataloader(self):
        return DataLoader(
            self.train_ds,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers,
            collate_fn=self.collate_fn,
            pin_memory=True,
        )

    def val_dataloader(self):
        return DataLoader(
            self.val_ds,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            collate_fn=self.collate_fn,
            pin_memory=True,
        )

    def test_dataloader(self):
        return DataLoader(
            self.test_ds,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            collate_fn=self.collate_fn,
            pin_memory=True,
        )

class SkinCancerLitModule(pl.LightningModule):
    def __init__(self, model_checkpoint: str, num_labels: int, id2label: Dict[int, str],
                 lr: float = 5e-5, weight_decay: float = 0.01,
                 lr_scheduler_type: str = "linear", warmup_ratio: float = 0.06,
                 adam_eps: float = 1e-8, monitor: str = "val/loss"):
        super().__init__()
        self.save_hyperparameters(ignore=["id2label"])
        self.lr = lr
        self.weight_decay = weight_decay
        self.lr_scheduler_type = lr_scheduler_type
        self.warmup_ratio = warmup_ratio
        self.adam_eps = adam_eps
        self.monitor = monitor

        config = AutoConfig.from_pretrained(
            model_checkpoint,
            num_labels=num_labels,
            id2label=id2label,
            label2id={v: k for k, v in id2label.items()},
        )
        self.model = AutoModelForImageClassification.from_pretrained(
            model_checkpoint, config=config, ignore_mismatched_sizes=True
        )

        self.metric_acc = evaluate.load("accuracy")
        self.metric_f1 = evaluate.load("f1")

        # для хранения предсказаний / меток за эпоху
        self._val_preds: List[np.ndarray] = []
        self._val_labels: List[np.ndarray] = []

    def forward(self, **batch):
        return self.model(**batch)

    def training_step(self, batch, batch_idx):
        outputs = self.model(**{k: v.to(self.device) for k, v in batch.items()})
        loss = outputs.loss
        logits = outputs.logits
        preds = torch.argmax(logits, dim=-1)
        labels = batch["labels"].to(self.device)
        self.log("train/loss", loss, prog_bar=True, on_step=True, on_epoch=True)
        return loss

    def validation_step(self, batch, batch_idx):
        outputs = self.model(**{k: v.to(self.device) for k, v in batch.items()})
        loss = outputs.loss
        logits = outputs.logits
        preds = torch.argmax(logits, dim=-1).cpu().numpy()
        labels = batch["labels"].cpu().numpy()
        self._val_preds.append(preds)
        self._val_labels.append(labels)
        self.log("val/loss", loss, prog_bar=True, on_step=False, on_epoch=True)
        return loss

    def on_validation_epoch_end(self):
        preds = np.concatenate(self._val_preds, axis=0)
        labels = np.concatenate(self._val_labels, axis=0)
        acc = self.metric_acc.compute(predictions=preds, references=labels)
        f1 = self.metric_f1.compute(predictions=preds, references=labels, average="macro")
        self.log("val/accuracy", acc["accuracy"], prog_bar=True,  on_epoch = True)
        self.log("val/f1_macro", f1["f1"], prog_bar=True, on_epoch = True)
        self._val_preds.clear()
        self._val_labels.clear()

    def test_step(self, batch, batch_idx):
        outputs = self.model(**{k: v.to(self.device) for k, v in batch.items()})
        logits = outputs.logits
        preds = torch.argmax(logits, dim=-1).cpu().numpy()
        labels = batch["labels"].cpu().numpy()
        # можно аналогично хранить для test, если нужен on_test_epoch_end
        self.metric_acc.add_batch(predictions=preds, references=labels)
        self.metric_f1.add_batch(predictions=preds, references=labels)

    def on_test_epoch_end(self):
        acc = self.metric_acc.compute()
        f1 = self.metric_f1.compute(average="macro")
        self.log("test/accuracy", acc["accuracy"],  on_epoch = True)
        self.log("test/f1_macro", f1["f1"],  on_epoch = True)
        # сбросим метрики, если планируешь ещё тестировать
        self.metric_acc = evaluate.load("accuracy")
        self.metric_f1 = evaluate.load("f1")

    def configure_optimizers(self):
        no_decay = ["bias", "LayerNorm.weight"]
        optimizer_grouped_parameters = [
            {
                "params": [p for n, p in self.named_parameters() if not any(nd in n for nd in no_decay) and p.requires_grad],
                "weight_decay": self.weight_decay,
            },
            {
                "params": [p for n, p in self.named_parameters() if any(nd in n for nd in no_decay) and p.requires_grad],
                "weight_decay": 0.0,
            },
        ]
        optimizer = torch.optim.AdamW(optimizer_grouped_parameters, lr=self.lr, eps=self.adam_eps)
        total_steps = None
        if hasattr(self, "trainer") and getattr(self.trainer, "max_epochs", None) is not None:
            try:
                train_loader = self.trainer.datamodule.train_dataloader()
                num_update_steps_per_epoch = len(train_loader)
                total_steps = num_update_steps_per_epoch * self.trainer.max_epochs
            except Exception:
                total_steps = None
        if total_steps is None:
            return optimizer

        warmup_steps = int(self.warmup_ratio * total_steps)
        if self.lr_scheduler_type in ("linear", "cosine", "cosine_with_restarts"):
            scheduler = get_scheduler(
                name=self.lr_scheduler_type,
                optimizer=optimizer,
                num_warmup_steps=warmup_steps,
                num_training_steps=total_steps,
            )
            scheduler_config = {
                "scheduler": scheduler,
                "interval": "step",
                "frequency": 1,
                "reduce_on_plateau": False,
                "monitor": self.monitor,
            }
            return {"optimizer": optimizer, "lr_scheduler": scheduler_config}
        elif self.lr_scheduler_type == "reduce_on_plateau":
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=2)
            scheduler_config = {
                "scheduler": scheduler,
                "interval": "epoch",
                "frequency": 1,
                "reduce_on_plateau": True,
                "monitor": self.monitor,
            }
            return {"optimizer": optimizer, "lr_scheduler": scheduler_config}
        else:
            return optimizer

def train_model(
    dataset_name: str = "marmal88/skin_cancer",
    model_checkpoint: str = "google/vit-base-patch16-224",
    output_dir: str = "./saved_skin_model",
    batch_size: int = 16,
    max_epochs: int = 3,
    gpus: int = 1,
    run_name: str = "skin_vit_run",
    use_wandb: bool = True,
    lr_scheduler_type: str = "linear",
    monitor_metric: str = "val/loss",
):
    os.makedirs(output_dir, exist_ok=True)
    dm = SkinCancerDataModule(dataset_name=dataset_name, model_checkpoint=model_checkpoint, batch_size=batch_size, num_workers=4)
    dm.prepare_data()
    dm.setup()
    lit = SkinCancerLitModule(model_checkpoint=model_checkpoint, num_labels=dm.num_labels, id2label=dm.id2label, lr=3e-5, lr_scheduler_type=lr_scheduler_type, monitor=monitor_metric)
    logger = None
    if use_wandb:
        logger = WandbLogger(project="skin_cancer_finetune", name=run_name)
        logger.log_hyperparams({"model_checkpoint": model_checkpoint, "batch_size": batch_size, "max_epochs": max_epochs, "lr_scheduler_type": lr_scheduler_type})
    checkpoint_cb = ModelCheckpoint(
        monitor=monitor_metric,
        mode="min",
        save_top_k=1,
        filename="best-{epoch:02d}-{val/loss:.4f}"
    )
    trainer_args = dict(
        max_epochs=max_epochs,
        callbacks=[checkpoint_cb],
        logger=logger,
        deterministic=True,
    )
    if torch.cuda.is_available() and gpus > 0:
        trainer_args["accelerator"] = "gpu"
        trainer_args["devices"] = gpus
    else:
        trainer_args["accelerator"] = "cpu"
    trainer = pl.Trainer(**trainer_args)
    trainer.fit(lit, datamodule=dm)
    test_res = trainer.test(lit, datamodule=dm, ckpt_path="best")
    best_path = checkpoint_cb.best_model_path
    model_save_dir = Path(output_dir) / "transformer_model"
    model_save_dir.mkdir(parents=True, exist_ok=True)
    if best_path:
        lit = SkinCancerLitModule.load_from_checkpoint(best_path, model_checkpoint=model_checkpoint, num_labels=dm.num_labels, id2label=dm.id2label)
        lit.model.save_pretrained(str(model_save_dir))
        lit.model.config.id2label = dm.id2label
        lit.model.config.label2id = dm.label2id
        dm.processor.save_pretrained(str(model_save_dir))
    else:
        lit.model.save_pretrained(str(model_save_dir))
        dm.processor.save_pretrained(str(model_save_dir))
    metrics_path = Path(output_dir) / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(test_res, f, ensure_ascii=False, indent=2)
    return {"model_dir": str(model_save_dir), "metrics": test_res}

res = train_model(
    dataset_name="marmal88/skin_cancer",
    model_checkpoint="google/vit-base-patch16-224",
    output_dir="./saved_skin_model",
    batch_size=8,
    max_epochs=3,
    gpus=1,
    run_name="skin_vit_colab_run",
    use_wandb=True,
    lr_scheduler_type="cosine",
    monitor_metric="val/loss",
)
print(res)

from google.colab import files
import shutil

# Создаем архив
shutil.make_archive('saved_skin_model', 'zip', '/content/saved_skin_model')

# Скачиваем
files.download('saved_skin_model.zip')

import shutil
from google.colab import drive

drive.mount('/content/drive')

# Путь назначения на Google Disk
destination_path = '/content/drive/MyDrive/saved_skin_model'

# Копируем папку
shutil.copytree('/content/saved_skin_model', destination_path)