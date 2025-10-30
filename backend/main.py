import uvicorn
from fastapi import FastAPI
from Database.Base import Base
from Database.Session import engine
from Api import router as api_router
from fastapi.middleware.cors import CORSMiddleware


def create_db_tables():
    """
    Создает все таблицы в БД, которые наследуются от Base.
    """
    print("--- Попытка создания таблиц в БД ---")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Таблицы успешно проверены/созданы.")
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")


app = FastAPI(
    title="Medical Analysis API",
    description="API для хранения и получения результатов медицинских анализов.",
    version="1.0.0"
)
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],    
)

@app.on_event("startup")
def on_startup():
    create_db_tables()


app.include_router(api_router.router, prefix="/api", tags=["Analysis"])


@app.get("/")
def read_root():
    return {"message": "Добро пожаловать в Medical Analysis API!", "docs_url": "/docs"}


if __name__ == "__main__":
    print("Запуск FastAPI приложения через uvicorn...")
    uvicorn.run(
        "main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
    )
