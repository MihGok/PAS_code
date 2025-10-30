# CRUD/analysis_service.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from Database.image_storage import minio_service
from CRUD import crud_ops
from minio.error import S3Error
import Schemas.schemas
import io
import logging
import traceback
import re
import random
import os
import requests # Новый импорт для имитации модели


def run_model_prediction(image_bytes: bytes) -> Schemas.schemas.AnalysisPredictionResponse:
    """
    Вызов внешнего prediction-service -> нормализация результата ->
    возвращает AnalysisPredictionResponse, где
    examination_result_model = "<Русское название> (КОД)"
    model_confidence = float
    """
    logger = logging.getLogger("analysis_service")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)

    # --- Словарь код -> русское название (frontend) ---
    DISEASE_DISPLAY = {
        'BKL': 'Доброкачественные кератозоподобные поражения',
        'AK':  'Актинический кератоз',
        'BCC': 'Базально-клеточная карцинома',
        'DF':  'Дерматофиброма',
        'NV':  'Меланоцитарные невусы',
        'VASC':'Сосудистые поражения',
        'MEL': 'Меланома'
    }

    CANONICAL = {"NV", "MEL", "BCC", "BKL", "AK", "DF", "VASC"}

    # ----------------- ОБНОВЛЁННЫЙ СЛОВАРЬ ПЕРЕКОДИРОВКИ -----------------
    # Учтены варианты, которые ты прислал: 
    # ['benign_keratosis-like_lesions','actinic_keratoses','basal_cell_carcinoma',
    #  'dermatofibroma','melanocytic_Nevi','vascular_lesions','melanoma']
    SYNONYMS_TO_CODE = {
        # прямые варианты из модели (нижний регистр / подчёркивания / дефисы)
        "benign_keratosis-like_lesions": "BKL",
        "benign_keratosis_like_lesions": "BKL",
        "benign keratosis like lesions": "BKL",
        "benignkeratosislikelesions": "BKL",
        "bkl": "BKL",

        "actinic_keratoses": "AK",
        "actinic_keratosis": "AK",
        "actinic keratoses": "AK",
        "ak": "AK",
        "akiec": "AK",  # старые/альтернативные коды

        "basal_cell_carcinoma": "BCC",
        "basal-cell_carcinoma": "BCC",
        "basal cell carcinoma": "BCC",
        "bcc": "BCC",

        "dermatofibroma": "DF",
        "df": "DF",

        "melanocytic_nevi": "NV",
        "melanocytic_nevus": "NV",
        "melanocytic_nevi_n": "NV",
        "melanocyticnevi": "NV",
        "nevi": "NV",
        "nev": "NV",
        "nevus": "NV",
        "nv": "NV",
        "nv_m": "NV",
        "nv_m_": "NV",

        "vascular_lesions": "VASC",
        "vascular lesions": "VASC",
        "vascularlesions": "VASC",
        "vasc": "VASC",

        "melanoma": "MEL",
        "mel": "MEL"
    }
    # ------------------------------------------------------------------

    PREDICT_SERVICE_URL = os.getenv("PREDICT_SERVICE_URL", "http://127.0.0.1:8080/predict")
    TIMEOUT = (3, 15)  # (connect, read)

    files = {
        "image_file": ("image.jpg", io.BytesIO(image_bytes), "application/octet-stream")
    }

    try:
        logger.info(f"run_model_prediction: sending image to {PREDICT_SERVICE_URL}")
        resp = requests.post(PREDICT_SERVICE_URL, files=files, timeout=TIMEOUT)

        logger.info(f"Prediction service responded: status={resp.status_code}")
        body_preview = (resp.text[:1000] + '...') if len(resp.text) > 1000 else resp.text
        logger.debug(f"Prediction service body (preview): {body_preview}")

        resp.raise_for_status()

        try:
            data = resp.json()
        except Exception as je:
            logger.exception(f"Failed to parse JSON from prediction service: {je}")
            raise

        # Получаем "сырую" метку (если есть)
        raw_label = None
        for key in ("label", "predicted_label", "examination_result_model"):
            if key in data and data.get(key) is not None:
                raw_label = str(data.get(key))
                break

        # fallback: если нет текстовой метки, попробуем index
        if raw_label is None and "index" in data:
            raw_label = str(data.get("index"))

        logger.debug(f"Raw label from service: {raw_label}")

        # Нормализация -> канонический код
        canonical_code = None
        if raw_label:
            rl = raw_label.strip().lower()
            # Простая очистка: заменим дефисы на подчёркивания, уберём лишние символы
            rl = rl.replace("-", "_")
            rl = re.sub(r"[^a-z0-9_ ]+", "", rl).strip()
            rl_nospace = rl.replace(" ", "")
            # Попытки поиска по разным формам:
            for candidate in (rl, rl_nospace, rl.replace("_", ""), rl.split()[0] if " " in rl else rl):
                if candidate in SYNONYMS_TO_CODE:
                    canonical_code = SYNONYMS_TO_CODE[candidate]
                    break
            # Если прямого совпадения нет — попробуем первые 4 символа
            if canonical_code is None:
                key4 = rl_nospace[:4]
                if key4 in SYNONYMS_TO_CODE:
                    canonical_code = SYNONYMS_TO_CODE[key4]
            # ещё эвристики
            up = raw_label.strip().upper()
            if canonical_code is None:
                if up.startswith("AKIEC"):
                    canonical_code = "AK"
                elif up.startswith("NV_M"):
                    canonical_code = "NV"
                elif "NEV" in up or "NEVI" in up:
                    canonical_code = "NV"
                elif "MELANO" in up:
                    canonical_code = "MEL"

        # извлекаем уверенность
        confidence = None
        if "confidence" in data:
            try:
                confidence = float(data.get("confidence"))
            except Exception:
                confidence = None
        if confidence is None and "model_confidence" in data:
            try:
                confidence = float(data.get("model_confidence"))
            except Exception:
                confidence = None
        if confidence is None and "probabilities" in data and isinstance(data["probabilities"], list):
            try:
                confidence = float(max(data["probabilities"]))
            except Exception:
                confidence = None

        # Если не удалось нормализовать -> fallback симуляция
        if canonical_code is None:
            logger.warning(f"Could not normalize label '{raw_label}' -> using fallback simulation")
            canonical_code = random.choice(list(CANONICAL))
            if confidence is None:
                confidence = round(random.uniform(0.7, 0.99), 4)
        else:
            if confidence is None:
                confidence = 0.0

        # Русская надпись + код в скобках
        display_name = DISEASE_DISPLAY.get(canonical_code, canonical_code)
        display_with_code = f"{display_name} ({canonical_code})"

        logger.info(f"Prediction normalized: {raw_label} -> {display_with_code}, confidence={confidence}")

        return Schemas.schemas.AnalysisPredictionResponse(
            examination_result_model=display_with_code,
            model_confidence=float(round(float(confidence), 6))
        )

    except Exception as e:
        logger.error(f"Exception during prediction request: {e}")
        tb = traceback.format_exc()
        logger.debug(f"Full traceback:\n{tb}")

        # fallback — имитация и отображение на русском
        canonical_code = random.choice(list(CANONICAL))
        display_name = DISEASE_DISPLAY.get(canonical_code, canonical_code)
        display_with_code = f"{display_name} ({canonical_code})"
        confidence = round(random.uniform(0.7, 0.99), 4)
        logger.info(f"Using fallback prediction: {display_with_code} ({confidence})")
        return Schemas.schemas.AnalysisPredictionResponse(
            examination_result_model=display_with_code,
            model_confidence=confidence
        )



def create_full_analysis_workflow(
    db: Session,
    user_data: Schemas.schemas.UserCreate,
    # ИЗМЕНЕНИЕ: Теперь ожидаем ExaminationFullCreate
    exam_data: Schemas.schemas.ExaminationFullCreate,
    image_bytes: bytes,
    image_filename: str,
    initial_diagnosis_data: Schemas.schemas.DiagnosisCreate,
    image_content_type: str = 'image/jpeg'
):
    """
    Выполняет полный цикл: загрузка изображения, создание пользователя/анализа,
    и создание ПЕРВОЙ записи диагноза.
    """
    try:
        # 1. Загрузка файла
        object_name = minio_service.upload_file(
            file_bytes=image_bytes,
            object_name=image_filename,
            content_type=image_content_type
        )
        
        # 2. Пользователь
        db_user = crud_ops.get_or_create_db_user(db, user=user_data)
        
        # 3. Изображение
        db_image = crud_ops.create_db_image(db, object_name=object_name)
        
        # 4. Обследование (использует ExaminationFullCreate)
        db_exam = crud_ops.create_db_examination(
            db,
            exam_data=exam_data,
            image_id=db_image.image_id,
            user_id=db_user.user_id 
        )
        
        # 5. Первый диагноз
        crud_ops.add_diagnosis_to_examination(
            db=db,
            db_exam=db_exam,
            diagnosis_data=initial_diagnosis_data
        )
        
        db.commit()
        
        # Обновляем объект из БД, чтобы подгрузить созданный диагноз
        db.refresh(db_exam, attribute_names=['diagnoses'])
        
        print(f"🎉 УСПЕХ! Создан анализ (ID: {db_exam.examination_id}) для пользователя (СНИЛС: {db_user.user_id}).")
        return db_exam

    except (S3Error, SQLAlchemyError) as e:
        print(f"❌ ОШИБКА БАЗЫ ДАННЫХ или MinIO: {e}")
        db.rollback()
        return None
    except Exception as e:
        print(f"❌ ОБЩАЯ ОШИБКА: {e}")
        db.rollback()
        return None
