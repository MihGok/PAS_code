# Api/router.py

import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
import decimal
from Database.Session import get_db
from Schemas import schemas
from CRUD import crud_ops, analysis_service
from Database.image_storage import minio_service

router = APIRouter()

async def get_user_data(
    user_id: str = Form(..., description="СНИЛС пациента"),
    user_name: str = Form(..., description="Имя пользователя"),
    user_second_name: str = Form(..., description="Фамилия пользователя"),
    user_patronomyc: str | None = Form(None, description="Отчество"),
    user_gender: bool = Form(..., description="Пол (True/False)"),
    user_age: int = Form(..., description="Возраст"),
) -> schemas.UserCreate:
    return schemas.UserCreate(
        user_id=user_id, user_name=user_name, user_second_name=user_second_name,
        user_patronomyc=user_patronomyc, user_gender=user_gender, user_age=user_age,
    )

async def get_exam_data(
    examination_location: str | None = Form(None, max_length=2),
    examination_date: date = Form(date.today()),
    examination_doctor: str = Form(...),
) -> schemas.ExaminationCreate:
    return schemas.ExaminationCreate(
        examination_location=examination_location, 
        examination_date=examination_date,
        examination_doctor=examination_doctor,
    )


async def get_initial_diagnosis_data(
    diagnosis_result: str = Form(..., max_length=50),
    doctor_name: str = Form(...) 
) -> schemas.DiagnosisCreate:
    return schemas.DiagnosisCreate(
        diagnosis_result=diagnosis_result,
        doctor_name=doctor_name,
    )


@router.post(
    "/analyze/",
    response_model=schemas.AnalysisPredictionResponse,
    summary="Получить предсказание и уверенность модели для загруженного изображения"
)
async def analyze_image_for_model_prediction(image_file: UploadFile = File(...)):
    """
    Принимает изображение, АСИНХРОННО запускает модель и возвращает предсказание.
    """
    try:
        image_bytes = await image_file.read()
        
        # ИЗМЕНЕНИЕ: Добавлено 'await', т.к. функция стала асинхронной
        prediction_data = await analysis_service.run_model_prediction(image_bytes=image_bytes)
        
        return prediction_data
    except Exception as e:
        # (Дополнительно) Ловим ошибки httpx, если они "прорвутся"
        if "RequestError" in str(type(e)):
            raise HTTPException(status_code=504, detail=f"Ошибка подключения к сервису модели: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при выполнении анализа: {e}")


# ----------------- ЭНДПОИНТ СОЗДАНИЯ АНАЛИЗА (БЕЗ ИЗМЕНЕНИЙ) ------------------
# Он не вызывает модель, а получает ее результат из формы,
# поэтому его логика остается СИНХРОННОЙ.
@router.post(
    "/analysis/",
    response_model=schemas.ExaminationResponse,
    summary="Полный цикл создания анализа, включая пользователя и первый диагноз"
)
async def create_full_analysis(
    user_data: schemas.UserCreate = Depends(get_user_data),
    exam_data: schemas.ExaminationCreate = Depends(get_exam_data),
    initial_diagnosis_data: schemas.DiagnosisCreate = Depends(get_initial_diagnosis_data),
    examination_result_model: str = Form(..., max_length=50),
    model_confidence: float = Form(...),
    image_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        full_exam_data = schemas.ExaminationFullCreate(
            **exam_data.model_dump(),
            examination_result_model=examination_result_model,
            model_confidence=decimal.Decimal(str(model_confidence)) 
        )
        
        image_bytes = await image_file.read()

        # Вызываем СИНХРОННУЮ функцию workflow (она работает с БД)
        db_exam = analysis_service.create_full_analysis_workflow(
            db=db,
            user_data=user_data,
            exam_data=full_exam_data, 
            image_bytes=image_bytes,
            image_filename=f"{uuid.uuid4()}_{image_file.filename}",
            initial_diagnosis_data=initial_diagnosis_data,
            image_content_type=image_file.content_type
        )
        
        if db_exam is None:
             raise HTTPException(status_code=500, detail="Не удалось завершить рабочий процесс анализа.")
             
        return db_exam
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Произошла ошибка при создании анализа: {e}"
        )


@router.get("/user/{user_id}/examinations/", response_model=list[schemas.ExaminationResponse], summary='Получить все анализы пользователя')
def get_user_examinations(user_id: str, db: Session = Depends(get_db)):
    examinations = crud_ops.get_examinations_by_user_id(db, user_id=user_id)
    return examinations


@router.get("/analysis/{analysis_id}/", response_model=schemas.ExaminationResponse, summary="Получить анализ по ID")
def get_analysis_by_id(analysis_id: int, db: Session = Depends(get_db)):
    db_exam = crud_ops.get_examination_by_id(db, exam_id=analysis_id)
    if db_exam is None:
        raise HTTPException(status_code=404, detail="Результат анализа не найден")
    return db_exam


@router.post(
    "/analysis/{analysis_id}/diagnoses/",
    response_model=schemas.DiagnosisResponse,
    summary="Добавить новый диагноз к существующему анализу"
)
def add_new_diagnosis(
    analysis_id: int,
    diagnosis_data: schemas.DiagnosisCreate, 
    db: Session = Depends(get_db)
):
    db_exam = crud_ops.get_examination_by_id(db, exam_id=analysis_id)
    if not db_exam:
        raise HTTPException(status_code=404, detail="Результат анализа не найден")
    
    try:
        new_diagnosis = crud_ops.add_diagnosis_to_examination(
            db=db,
            db_exam=db_exam,
            diagnosis_data=diagnosis_data
        )
        db.commit()
        db.refresh(new_diagnosis)
        return new_diagnosis
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Не удалось добавить диагноз: {e}"
        )

@router.get("/image/{image_id}/")
def get_image_visualization(image_id: int, db: Session = Depends(get_db)):
    db_image = crud_ops.get_image_by_id(db, image_id=image_id)
    if db_image is None:
        raise HTTPException(status_code=404, detail="Изображение не найдено")
        
    presigned_url = minio_service.get_presigned_url(db_image.image_link)
    
    if presigned_url is None:
        raise HTTPException(status_code=500, detail="Не удалось получить ссылку на изображение")
    
    return RedirectResponse(url=presigned_url)
