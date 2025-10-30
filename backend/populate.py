import os
import random
import decimal
from faker import Faker


from Database.Session import SessionLocal, engine
from Models.models import Base
from Schemas import schemas
from CRUD.analysis_service import create_full_analysis_workflow
from config import settings


fake = Faker('ru_RU')


def get_random_image_data() -> tuple[bytes, str, str] | None:
    """Выбирает случайный файл и читает его байты."""
    folder = settings.IMAGES_FOLDER
    if not os.path.isdir(folder):
        print(f"Ошибка: Папка '{folder}' не найдена."); return None
    image_files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    if not image_files:
        print(f"В папке '{folder}' нет файлов."); return None
    random_filename = random.choice(image_files)
    file_path = os.path.join(folder, random_filename)
    content_type = 'image/jpeg' if random_filename.lower().endswith(('.jpg', '.jpeg')) else 'image/png'
    with open(file_path, 'rb') as f:
        image_bytes = f.read()
    unique_filename = f"{os.path.splitext(random_filename)[0]}_{fake.uuid4()}{os.path.splitext(random_filename)[1]}"
    return image_bytes, unique_filename, content_type

def generate_random_data():
    """Генерирует Pydantic-схемы со случайными данными."""
    user_gender = random.choice([True, False])
    user_data = schemas.UserCreate(
        user_name=fake.first_name_male() if user_gender else fake.first_name_female(),
        user_second_name=fake.last_name_male() if user_gender else fake.last_name_female(),
        user_patronomyc=fake.middle_name_male() if user_gender else fake.middle_name_female(),
        user_gender=user_gender,
        user_age=random.randint(18, 90)
    )
    exam_data = schemas.ExaminationCreate(
        examination_result_model=random.choice(['B', 'M']),
        examination_result_human=random.choice(['B', 'M', 'U']), 
        examination_location=random.choice(['AR', 'LE', 'BA', 'CH']),
        examination_date=fake.date_between(start_date='-2y', end_date='today'),
        examination_doctor=f"Др. {fake.last_name()}",
        model_confidence=decimal.Decimal(random.uniform(0.5, 0.999))
    )
    image_tuple = get_random_image_data()
    if not image_tuple:
        return None, None, None    
    image_bytes, image_filename, content_type = image_tuple
    return user_data, exam_data, image_bytes, image_filename, content_type


def main():
    print("--- Запуск скрипта заполнения БД ---")
    Base.metadata.create_all(bind=engine)
    print("--- Таблицы БД проверены/созданы ---")
    db = SessionLocal()
    user_data, exam_data, img_bytes, img_name, img_type = generate_random_data()
    if not user_data:
        print("Не удалось сгенерировать данные.")
        db.close()
        return
    print(f"Попытка создать запись для: {user_data.user_second_name} с файлом {img_name}...")
    try:
        create_full_analysis_workflow(
            db=db,
            user_data=user_data,
            exam_data=exam_data,
            image_bytes=img_bytes,
            image_filename=img_name,
            image_content_type=img_type
        )
    except Exception as e:
        print(f"Непредвиденная ошибка в главном скрипте: {e}")
    finally:
        db.close()
        print("--- Скрипт завершен, сессия БД закрыта ---")

if __name__ == "__main__":
    main()
