# CRUD/crud_ops.py

from sqlalchemy.orm import Session, selectinload
from Models import models
from Schemas import schemas

# ========== Операции с Пользователями (UserData) ==========

def get_user_by_id(db: Session, user_id: str) -> models.UserData | None:
    return db.query(models.UserData).filter(models.UserData.user_id == user_id).first()

def create_db_user(db: Session, user: schemas.UserCreate) -> models.UserData:
    db_user = models.UserData(**user.model_dump())
    db.add(db_user)
    db.flush()
    return db_user

def get_or_create_db_user(db: Session, user: schemas.UserCreate) -> models.UserData:
    db_user = get_user_by_id(db, user_id=user.user_id)
    if db_user:
        return db_user
    return create_db_user(db, user)

# ========== Операции с Изображениями (Image) ==========

def get_image_by_id(db: Session, image_id: int) -> models.Image | None:
    return db.query(models.Image).filter(models.Image.image_id == image_id).first()

def create_db_image(db: Session, object_name: str) -> models.Image:
    db_image = models.Image(image_link=object_name)
    db.add(db_image)
    db.flush()
    return db_image

# ========== Операции с Обследованиями и Диагнозами ==========

def get_examination_by_id(db: Session, exam_id: int) -> models.ExaminationResult | None:
    """
    Получает полное обследование по его ID, включая все связанные диагнозы.
    """
    return db.query(models.ExaminationResult).options(
        selectinload(models.ExaminationResult.diagnoses) # Эффективно загружаем диагнозы
    ).filter(models.ExaminationResult.examination_id == exam_id).first()

def get_examinations_by_user_id(db: Session, user_id: str) -> list[models.ExaminationResult]:
    """
    Возвращает список обследований пользователя, включая все связанные диагнозы.
    """
    return db.query(models.ExaminationResult).options(
        selectinload(models.ExaminationResult.diagnoses)
    ).filter(
        models.ExaminationResult.user_id == user_id
    ).order_by(models.ExaminationResult.examination_date.desc()).all()

def create_db_examination(db: Session, exam_data: schemas.ExaminationCreate, image_id: int, user_id: str) -> models.ExaminationResult:
    """Создает запись об обследовании в БД."""
    db_exam = models.ExaminationResult(
        **exam_data.model_dump(),
        examination_image_id=image_id,
        user_id=user_id
    )
    db.add(db_exam)
    db.flush()
    return db_exam

# ИЗМЕНЕНИЕ: update_examination_diagnosis УДАЛЕНА

def add_diagnosis_to_examination(db: Session, db_exam: models.ExaminationResult, diagnosis_data: schemas.DiagnosisCreate) -> models.Diagnosis:
    """
    НОВАЯ ФУНКЦИЯ: Создает новую запись диагноза и привязывает ее к существующему обследованию.
    """
    db_diagnosis = models.Diagnosis(
        **diagnosis_data.model_dump(),
        examination_id=db_exam.examination_id
    )
    db.add(db_diagnosis)
    db.flush()
    return db_diagnosis
