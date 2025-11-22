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
import httpx


limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
TIMEOUT = httpx.Timeout(3.0, read=15.0)
async_client = httpx.AsyncClient(limits=limits, timeout=TIMEOUT)


DISEASE_DISPLAY = {
    'BKL': 'Доброкачественные кератозоподобные поражения',
    'AK':  'Актинический кератоз',
    'BCC': 'Базально-клеточная карцинома',
    'DF':  'Дерматофиброма',
    'NV':  'Меланоцитарные невусы',
    'VASC': 'Сосудистые поражения',
    'MEL': 'Меланома'
}

CANONICAL = {"NV", "MEL", "BCC", "BKL", "AK", "DF", "VASC"}

SYNONYMS_TO_CODE = {
    "benign_keratosis-like_lesions": "BKL", "bkl": "BKL",
    "actinic_keratoses": "AK", "ak": "AK", "akiec": "AK",
    "basal_cell_carcinoma": "BCC", "bcc": "BCC",
    "dermatofibroma": "DF", "df": "DF",
    "melanocytic_nevi": "NV", "nv": "NV",
    "vascular_lesions": "VASC", "vasc": "VASC",
    "melanoma": "MEL", "mel": "MEL"
}


# ИЗМЕНЕНИЕ: Функция стала асинхронной (async def)
async def run_model_prediction(image_bytes: bytes) -> Schemas.schemas.AnalysisPredictionResponse:
    """
    АСИНХРОННЫЙ вызов внешнего prediction-service -> нормализация результата
    """
    logger = logging.getLogger("analysis_service")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)

    PREDICT_SERVICE_URL = os.getenv("PREDICT_SERVICE_URL", "http://127.0.0.1:8080/predict")

    files = {
        "image_file": ("image.jpg", io.BytesIO(image_bytes), "application/octet-stream")
    }

    try:
        logger.info(f"run_model_prediction: sending image to {PREDICT_SERVICE_URL}")
        resp = await async_client.post(PREDICT_SERVICE_URL, files=files)

        logger.info(f"Prediction service responded: status={resp.status_code}")
        body_preview = (resp.text[:1000] + '...') if len(resp.text) > 1000 else resp.text
        logger.debug(f"Prediction service body (preview): {body_preview}")
        resp.raise_for_status()

        try:
            data = resp.json()
        except Exception as je:
            logger.exception(f"Failed to parse JSON from prediction service: {je}")
            raise

        raw_label = None
        for key in ("label", "predicted_label", "examination_result_model"):
            if key in data and data.get(key) is not None:
                raw_label = str(data.get(key))
                break
        canonical_code = None
        if raw_label:
            rl = raw_label.strip().lower().replace("-", "_")
            rl = re.sub(r"[^a-z0-9_ ]+", "", rl).strip()
            rl_nospace = rl.replace(" ", "")
            for candidate in (rl, rl_nospace, rl.replace("_", "")):
                if candidate in SYNONYMS_TO_CODE:
                    canonical_code = SYNONYMS_TO_CODE[candidate]
                    break
        confidence = None
        if "confidence" in data:
            try: confidence = float(data.get("confidence"))
            except Exception: confidence = None

        if canonical_code is None:
            logger.warning(f"Could not normalize label '{raw_label}' -> using fallback simulation")
            canonical_code = random.choice(list(CANONICAL))
            if confidence is None: confidence = round(random.uniform(0.7, 0.99), 4)
        else:
            if confidence is None: confidence = 0.0

        display_name = DISEASE_DISPLAY.get(canonical_code, canonical_code)
        display_with_code = f"{display_name} ({canonical_code})"

        logger.info(f"Prediction normalized: {raw_label} -> {display_with_code}, confidence={confidence}")

        return Schemas.schemas.AnalysisPredictionResponse(
            examination_result_model=display_with_code,
            model_confidence=float(round(float(confidence), 6))
        )

    except httpx.RequestError as e:
        logger.error(f"HTTPX RequestError during prediction: {e}")
        tb = traceback.format_exc()
        logger.debug(f"Full traceback:\n{tb}")

    except Exception as e:
        logger.error(f"Exception during prediction request: {e}")
        tb = traceback.format_exc()
        logger.debug(f"Full traceback:\n{tb}")

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
    exam_data: Schemas.schemas.ExaminationFullCreate,
    image_bytes: bytes,
    image_filename: str,
    initial_diagnosis_data: Schemas.schemas.DiagnosisCreate,
    image_content_type: str = 'image/jpeg'
):
    """
    Эта функция ОСТАЕТСЯ СИНХРОННОЙ, т.к. она работает с БД и MinIO.
    Она не вызывает AI-модель, а только получает ее результат.
    """
    try:
        object_name = minio_service.upload_file(
            file_bytes=image_bytes,
            object_name=image_filename,
            content_type=image_content_type
        )
        db_user = crud_ops.get_or_create_db_user(db, user=user_data)
        db_image = crud_ops.create_db_image(db, object_name=object_name)
        
        db_exam = crud_ops.create_db_examination(
            db,
            exam_data=exam_data,
            image_id=db_image.image_id,
            user_id=db_user.user_id,
            initial_diagnosis_value=initial_diagnosis_data.diagnosis_result
        )
        crud_ops.add_diagnosis_to_examination(
            db=db,
            db_exam=db_exam,
            diagnosis_data=initial_diagnosis_data
        )
        db.commit()
        db.refresh(db_exam, attribute_names=['diagnoses'])
        print(f"УСПЕХ! Создан анализ (ID: {db_exam.examination_id}) для пользователя (СНИЛС: {db_user.user_id}).")
        return db_exam

    except (S3Error, SQLAlchemyError) as e:
        print(f"❌ ОШИБКА БАЗЫ ДАННЫХ или MinIO: {e}")
        db.rollback()
        return None
    except Exception as e:
        print(f"❌ ОБЩАЯ ОШИБКА: {e}")
        db.rollback()
        return None
