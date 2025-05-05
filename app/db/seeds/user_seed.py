from app.db.database import AsyncSessionFactory
from app.db.repositories.user_repository import UserRepository

async def seed_initial_user():
    if AsyncSessionFactory is None:
        print("Фабрика сессий не инициализирована, пропуск сидинга.")
        return
    

    print("Проверка/создание начального пользователя...")


    try:
        async with AsyncSessionFactory() as session:
            # Создаем репозиторий с передачей сессии 
            user_repository = UserRepository(session)
            # Вызываем метод без параметра db
            await user_repository.get_or_create_user(user_id=1, username="testuser1")
            
    except Exception as e:
        print(f"Ошибка при создании начального пользователя: {e}")
    
    print("Проверка/создание начального пользователя завершено.")