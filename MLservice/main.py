import os
import random
import io
from minio import Minio
from minio.error import S3Error
from PIL import Image

# --- Настройки MinIO ---
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin123"
MINIO_SECURE = False
BUCKET_NAME = "images"

# --- Настройки папки ---
IMAGES_FOLDER = "skin_cancer_images"

def handle_image_workflow():
    """
    Выполняет полный цикл: 
    1. Выбирает случайное изображение и загружает его в MinIO.
    2. Получает загруженное изображение из MinIO.
    3. Отображает его в отдельном окне.
    """
    
    # ------------------------------------
    # I. Инициализация и выбор файла для загрузки
    # ------------------------------------
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
    except Exception as e:
        print(f"Ошибка при инициализации клиента MinIO: {e}"); return

    if not os.path.isdir(IMAGES_FOLDER):
        print(f"Ошибка: Папка '{IMAGES_FOLDER}' не найдена."); return

    all_files = os.listdir(IMAGES_FOLDER)
    image_files = [f for f in all_files if os.path.isfile(os.path.join(IMAGES_FOLDER, f))]

    if not image_files:
        print(f"В папке '{IMAGES_FOLDER}' нет файлов."); return

    random_filename = random.choice(image_files)
    file_path = os.path.join(IMAGES_FOLDER, random_filename)
    # Ключ объекта в MinIO, который мы будем использовать для получения
    object_name = random_filename

    print(f"Выбран файл для загрузки: {file_path}")

    # ------------------------------------
    # II. Загрузка в MinIO
    # ------------------------------------
    try:
        # Создаем бакет, если он не существует
        if not client.bucket_exists(BUCKET_NAME):
            client.make_bucket(BUCKET_NAME)
            print(f"Бакет '{BUCKET_NAME}' создан.")

        # Определяем Content-Type
        content_type = 'image/jpeg' if random_filename.lower().endswith(('.jpg', '.jpeg')) else 'image/png' if random_filename.lower().endswith('.png') else 'application/octet-stream'

        # Загружаем файл
        client.fput_object(
            BUCKET_NAME,
            object_name,
            file_path,
            content_type=content_type
        )

        print("-" * 30)
        print(f"✅ Успешно загружено: '{object_name}' в бакет '{BUCKET_NAME}'")
        print("-" * 30)

    except S3Error as err:
        print(f"Ошибка MinIO при загрузке: {err}"); return
    except Exception as e:
        print(f"Произошла непредвиденная ошибка при загрузке: {e}"); return

    # ------------------------------------
    # III. Получение и отображение
    # ------------------------------------
    print(f"--- Получение объекта '{object_name}' из MinIO ---")
    
    response = None
    try:
        # 1. Скачивание объекта из MinIO
        response = client.get_object(BUCKET_NAME, object_name)
        
        # Чтение байтов изображения
        image_bytes = response.read()

        # 2. Отображение изображения с помощью Pillow
        image = Image.open(io.BytesIO(image_bytes))
        print(f"Размер изображения: {image.size}")
        # Отображение в отдельном окне
        image.show(title=f"Изображение из MinIO: {object_name}")
        
    except S3Error as err:
        print(f"Ошибка MinIO при получении объекта: {err}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка при отображении: {e}")
    finally:
        # Важно закрыть поток, если он был открыт
        if response:
            response.close()
            response.release_conn()


if __name__ == "__main__":
    handle_image_workflow()