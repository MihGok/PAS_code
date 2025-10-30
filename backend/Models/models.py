# Models/models.py
from sqlalchemy import (Column, Integer, String, Boolean, DECIMAL, 
                        Date, ForeignKey, DateTime)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from Database.Base import Base


class Image(Base):
    __tablename__ = "images"
    
    image_id = Column(Integer, primary_key=True, autoincrement=True)
    image_link = Column(String(255))
    
    examination = relationship("ExaminationResult", back_populates="image", uselist=False)


class UserData(Base):
    __tablename__ = "user_data"
    
    user_id = Column(String(50), primary_key=True, index=True, unique=True)
    user_name = Column(String(40), nullable=False)
    user_second_name = Column(String(40), nullable=False)
    user_patronomyc = Column(String(40))
    user_gender = Column(Boolean)
    user_age = Column(Integer)
    
    examinations = relationship("ExaminationResult", back_populates="user")


class ExaminationResult(Base):
    __tablename__ = "examination_results"
    
    examination_id = Column(Integer, primary_key=True, autoincrement=True)
    examination_result_model = Column(String(50), nullable=False)
    # ИЗМЕНЕНИЕ: examination_result_human УДАЛЕНО
    examination_location = Column(String(2))
    examination_date = Column(Date)
    examination_doctor = Column(String(50), nullable=False)
    model_confidence = Column(DECIMAL(10, 3), nullable=False)
    
    examination_image_id = Column(Integer, ForeignKey("images.image_id"), nullable=False, unique=True)
    user_id = Column(String(50), ForeignKey("user_data.user_id"), nullable=False)
    
    image = relationship("Image", back_populates="examination")
    user = relationship("UserData", back_populates="examinations")
    
    # НОВАЯ СВЯЗЬ: Один анализ имеет много диагнозов
    diagnoses = relationship("Diagnosis", back_populates="examination", cascade="all, delete-orphan")


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    
    diagnosis_id = Column(Integer, primary_key=True, autoincrement=True)
    examination_id = Column(Integer, ForeignKey("examination_results.examination_id"), nullable=False)
    diagnosis_result = Column(String(50), nullable=False) # Результат диагноза (NV, MEL и т.д.)
    doctor_name = Column(String(50), nullable=False) # Врач, поставивший этот конкретный диагноз
    diagnosis_date = Column(DateTime(timezone=True), server_default=func.now())
    
    examination = relationship("ExaminationResult", back_populates="diagnoses")
