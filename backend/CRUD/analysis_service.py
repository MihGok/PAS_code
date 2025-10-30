# CRUD/analysis_service.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from Database.image_storage import minio_service
from CRUD import crud_ops
from minio.error import S3Error
import Schemas.schemas
import random # Новый импорт для имитации модели


# --- НОВАЯ ФУНКЦИЯ: Имитация работы модели (Требование 1) ---
def run_model_prediction(image_bytes: bytes) -> Schemas.schemas.AnalysisPredictionResponse:
    """Имитирует запуск ML-модели и возвращает результат."""
    # В реальном приложении здесь будет логика вызова ML-модели, 
    # использующая image_bytes
    
    disease_codes = ['NV', 'MEL', 'BCC', 'BKL', 'VASC', 'DF', 'AKIEC']
    result = random.choice(disease_codes)
    # Уверенность должна быть float для схемы AnalysisPredictionResponse
    confidence = round(random.uniform(0.7, 0.99), 4) 

    return Schemas.schemas.AnalysisPredictionResponse(
        examination_result_model=result,
        model_confidence=confidence
    )
# --- Конец НОВОЙ ФУНКЦИИ ---


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
