from sqlalchemy.orm import Session, selectinload
from Models import models
from Schemas import schemas
from collections import Counter


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


def get_image_by_id(db: Session, image_id: int) -> models.Image | None:
    return db.query(models.Image).filter(models.Image.image_id == image_id).first()


def create_db_image(db: Session, object_name: str) -> models.Image:
    db_image = models.Image(image_link=object_name)
    db.add(db_image)
    db.flush()
    return db_image


def get_examination_by_id(db: Session, exam_id: int) -> models.ExaminationResult | None:
    """
    Получает полное обследование по его ID, включая все связанные диагнозы.
    """
    return db.query(models.ExaminationResult).options(
        selectinload(models.ExaminationResult.diagnoses)  # Эффективно загружаем диагнозы
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


def create_db_examination(
    db: Session,
    exam_data: schemas.ExaminationFullCreate,
    image_id: int,
    user_id: str,
    initial_diagnosis_value: str
) -> models.ExaminationResult:
    """Создает запись об обследовании в БД."""
    db_exam = models.ExaminationResult(
        **exam_data.model_dump(),
        examination_image_id=image_id,
        user_id=user_id,
        final_diagnosis=initial_diagnosis_value
    )
    db.add(db_exam)
    db.flush()
    return db_exam


def recalculate_final_diagnosis(db: Session, exam_id: int):
    """
    Находит самый популярный диагноз (моду) среди всех диагнозов.
    """
    exam = db.query(models.ExaminationResult).filter(models.ExaminationResult.examination_id == exam_id).first()
    if not exam:
        return
    db.refresh(exam, attribute_names=['diagnoses'])

    if not exam.diagnoses:
        return
    all_results = [d.diagnosis_result for d in exam.diagnoses]
    if all_results:
        most_common = Counter(all_results).most_common(1)[0][0]
        exam.final_diagnosis = most_common
        db.add(exam)
        db.flush()


def add_diagnosis_to_examination(db: Session, db_exam: models.ExaminationResult, diagnosis_data: schemas.DiagnosisCreate) -> models.Diagnosis:
    """
    Создает новую запись диагноза, привязывает к обследованию 
    и ОБНОВЛЯЕТ итоговый диагноз.
    """
    db_diagnosis = models.Diagnosis(
        **diagnosis_data.model_dump(),
        examination_id=db_exam.examination_id
    )
    db.add(db_diagnosis)
    db.flush()
    recalculate_final_diagnosis(db, db_exam.examination_id)
    return db_diagnosis
