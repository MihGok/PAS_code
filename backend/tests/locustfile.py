# locustfile.py
import random
from locust import HttpUser, task, between
from faker import Faker
from datetime import date
import os

# --- Настройка ---
IMAGE_PATH = "test_image.jpg" # Положите тестовое изображение рядом с этим файлом
# ------------------

fake = Faker('ru_RU')
DIAGNOSES = ['NV', 'MEL', 'BCC', 'BKL', 'AK', 'DF', 'VASC']


class MedicalApiUser(HttpUser):
    """
    Расширенная модель поведения пользователя:
    - 50% времени создает новые анализы (тяжелая задача)
    - 30% времени "бродит" по истории (легкая задача)
    - 10% смотрит картинки
    - 10% добавляет "второе мнение"
    """
    
    wait_time = between(1.0, 3.0)
    
    def on_start(self):
        """Выполняется один раз при 'рождении' пользователя."""
        try:
            with open(IMAGE_PATH, 'rb') as f:
                self.image_bytes = f.read()
            self.image_file_tuple = ('image.jpg', self.image_bytes, 'image/jpeg')
            print("Тестовое изображение загружено в память.")
            self.created_data = [] 
            
        except FileNotFoundError:
            print(f"ОШИБКА: Тестовое изображение не найдено по пути: {IMAGE_PATH}")
            self.stop(True)

    def _get_random_data(self):
        """Вспомогательная функция для генерации данных."""
        gender = random.choice([True, False])
        doctor_name = fake.name()
        user_id = fake.snils()
        
        user_data = {
            "user_id": user_id,
            "user_name": fake.first_name_male() if gender else fake.first_name_female(),
            "user_second_name": fake.last_name_male() if gender else fake.last_name_female(),
            "user_patronomyc": fake.middle_name_male() if gender else fake.middle_name_female(),
            "user_gender": gender,
            "user_age": random.randint(20, 80),
        }
        exam_data = {
            "examination_location": random.choice(["CH", "AB", "BK", "HD"]),
            "examination_date": date.today().isoformat(),
            "examination_doctor": doctor_name,
        }
        initial_diagnosis_data = {
            "diagnosis_result": random.choice(DIAGNOSES),
            "doctor_name": doctor_name,
        }
        return user_id, user_data, exam_data, initial_diagnosis_data

    @task(10) # <-- Это самая частая задача
    def full_analysis_workflow(self):
        """
        ПОЛНЫЙ ЦИКЛ СОЗДАНИЯ (2 запроса: /analyze/ и /analysis/)
        """
        user_id, user_data, exam_data, initial_diagnosis_data = self._get_random_data()
        model_result = None
        model_confidence = None
        
        # --- 1. Шаг А: Вызов /api/analyze/ ---
        with self.client.post(
            "/api/analyze/",
            files={'image_file': self.image_file_tuple},
            name="/api/analyze/", 
            catch_response=True 
        ) as response_analyze:
            
            if response_analyze.status_code == 200:
                try:
                    prediction_data = response_analyze.json()
                    model_result = prediction_data['examination_result_model']
                    model_confidence = prediction_data['model_confidence']
                    response_analyze.success()
                except Exception as e:
                    response_analyze.failure(f"Failed to parse JSON: {e}")
            else:
                response_analyze.failure(f"Status code {response_analyze.status_code}")
                return 

        # --- 2. Шаг Б: Вызов /api/analysis/ (Создание) ---
        form_data = {
            **user_data, **exam_data, **initial_diagnosis_data,
            "examination_result_model": model_result,
            "model_confidence": model_confidence,
        }

        with self.client.post(
            "/api/analysis/",
            data=form_data,
            files={'image_file': self.image_file_tuple},
            name="/api/analysis/",
            catch_response=True
        ) as response_create:
            
            if response_create.status_code == 200:
                response_create.success()
                try:
                    # ЗАПОМИНАЕМ ID для других тестов
                    created_exam = response_create.json()
                    exam_id = created_exam['examination_id']
                    image_id = created_exam['image']['image_id']
                    self.created_data.append((user_id, exam_id, image_id))
                    
                    # Ограничиваем "память" пользователя
                    if len(self.created_data) > 50:
                        self.created_data.pop(0)
                        
                except Exception:
                    pass # Не страшно, если не удалось сохранить ID
            else:
                response_create.failure(f"Status code {response_create.status_code}")

    @task(5) # <-- "Просмотр" (чтение)
    def browse_history_and_analysis(self):
        """
        ЗАДАЧА НА ЧТЕНИЕ: посмотреть историю пациента и один анализ
        """
        if not self.created_data:
            return # Еще ничего не создали

        user_id, exam_id, _ = random.choice(self.created_data)

        # 1. Запрос истории
        self.client.get(
            f"/api/user/{user_id}/examinations/",
            name="/api/user/{user_id}/examinations/"
        )
        
        # 2. Запрос одного анализа
        self.client.get(
            f"/api/analysis/{exam_id}/",
            name="/api/analysis/{analysis_id}/"
        )

    @task(2) # <-- "Второе мнение" (запись)
    def add_second_opinion(self):
        """
        ЗАДАЧА НА ЗАПИСЬ: Добавить второй диагноз
        """
        if not self.created_data:
            return

        _, exam_id, _ = random.choice(self.created_data)
        
        second_diagnosis_data = {
            "diagnosis_result": random.choice(DIAGNOSES), # "Второе мнение"
            "doctor_name": fake.name()
        }
        
        self.client.post(
            f"/api/analysis/{exam_id}/diagnoses/",
            json=second_diagnosis_data,
            name="/api/analysis/{analysis_id}/diagnoses/"
        )
