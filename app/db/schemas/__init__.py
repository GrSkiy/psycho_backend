# Реэкспорт классов из отдельных файлов для обратной совместимости

# Импорт и реэкспорт классов чата
from .chat import (
    ChatBase, 
    ChatCreate, 
    Chat,
    ChatInfo,
    MessageBase,
    MessageCreate,
    Message
)

# Импорт и реэкспорт классов пользователя
from .user import (
    UserBase,
    UserCreate,
    User
)

# В будущем здесь могут быть импорты из diary.py, astro.py, tarot.py и т.д. 