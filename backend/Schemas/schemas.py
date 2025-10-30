# Schemas/schemas.py

import decimal
import random
from datetime import date, datetime
from pydantic import BaseModel, Field
from faker import Faker

fake = Faker('ru_RU')

# --- Схемы для Диагноза ---

class DiagnosisBase(BaseModel):
    diagnosis_result: str = Field(..., max_length=50, description="Результат диагноза (NV, MEL и т.д.)")
    doctor_name: str = Field(..., description="ФИО врача, поставившего диагноз")

class DiagnosisCreate(DiagnosisBase):
    pass

class DiagnosisResponse(DiagnosisBase):
    diagnosis_id: int
    diagnosis_date: datetime

    class Config:
        from_attributes = True

# --- Схемы для Пользователя ---

class UserCreate(BaseModel):
    user_id: str = Field(..., description="СНИЛС пациента (используется как ID)")
    user_name: str
    user_second_name: str
    user_patronomyc: str | None = None
    user_gender: bool
    user_age: int

class UserResponse(UserCreate):
    class Config:
        from_attributes = True

# --- Схемы для Изображения ---\
class ImageResponse(BaseModel):
    image_id: int
    image_link: str

    class Config:
        from_attributes = True

# --- Схемы для Обследования ---

# 1. Схема для данных обследования, которые не зависят от модели (для первого шага)
class ExaminationCreate(BaseModel):
    # УДАЛЕНЫ examination_result_model и model_confidence
    examination_location: str | None = Field(default='CH', max_length=2)
    examination_date: date = Field(default_factory=date.today)
    examination_doctor: str # Врач, проводивший осмотр
    
# 2. НОВАЯ СХЕМА: Объединяет ExaminationCreate с результатами модели (для финальной записи в БД)
class ExaminationFullCreate(ExaminationCreate):
    examination_result_model: str = Field(..., max_length=50)
    model_confidence: decimal.Decimal

# 3. НОВАЯ СХЕМА: Ответ от эндпоинта анализа
class AnalysisPredictionResponse(BaseModel):
    examination_result_model: str
    model_confidence: float

# 4. Схема ответа (ExaminationResponse)
class ExaminationResponse(BaseModel):
    examination_id: int
    examination_result_model: str
    examination_location: str | None
    examination_date: date
    examination_doctor: str
    model_confidence: float
    
    user: UserResponse
    image: ImageResponse
    diagnoses: list[DiagnosisResponse] # Список диагнозов

    class Config:
        from_attributes = True