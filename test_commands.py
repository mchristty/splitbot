#!/usr/bin/env python3
"""
Скрипт для тестирования команд бота
"""

import asyncio
from unittest.mock import Mock, AsyncMock
from aiogram.types import Message, User, Chat
from handlers import router

def create_mock_message(text: str, chat_id: int = 12345, user_id: int = 67890):
    """Создание мок-объекта сообщения для тестирования"""
    mock_user = Mock(spec=User)
    mock_user.id = user_id
    mock_user.username = "testuser"
    mock_user.first_name = "Test"
    
    mock_chat = Mock(spec=Chat)
    mock_chat.id = chat_id
    
    mock_message = Mock(spec=Message)
    mock_message.text = text
    mock_message.from_user = mock_user
    mock_message.chat = mock_chat
    mock_message.answer = AsyncMock()
    
    return mock_message

async def test_start_command():
    """Тестирование команды /start"""
    print("🧪 Тестирование команды /start...")
    
    message = create_mock_message("/start")
    
    # Находим обработчик команды start
    for handler in router.sub_routers:
        if hasattr(handler, 'filters') and any(hasattr(f, '__class__') and 'Command' in str(f.__class__) for f in handler.filters):
            try:
                await handler.callback(message)
                print("✅ Команда /start обработана")
                return True
            except Exception as e:
                print(f"❌ Ошибка в команде /start: {e}")
                return False
    
    print("⚠️ Обработчик команды /start не найден")
    return False

async def test_help_command():
    """Тестирование команды /help"""
    print("🧪 Тестирование команды /help...")
    
    message = create_mock_message("/help")
    
    # Аналогично для /help
    for handler in router.sub_routers:
        if hasattr(handler, 'filters'):
            try:
                await handler.callback(message)
                print("✅ Команда /help обработана")
                return True
            except Exception as e:
                print(f"❌ Ошибка в команде /help: {e}")
                return False
    
    print("⚠️ Обработчик команды /help не найден")
    return False

async def test_create_command():
    """Тестирование команды /create"""
    print("🧪 Тестирование команды /create...")
    
    message = create_mock_message('/create "TestGroup"')
    
    try:
        # Имитируем обработку команды create
        from handlers import create_handler
        await create_handler(message)
        print("✅ Команда /create обработана")
        return True
    except Exception as e:
        print(f"❌ Ошибка в команде /create: {e}")
        return False

async def main():
    """Основная функция тестирования команд"""
    print("🚀 Начинаем тестирование команд бота...")
    
    tests = [
        test_start_command,
        test_help_command,
        test_create_command
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"❌ Ошибка в тесте {test.__name__}: {e}")
    
    print(f"📊 Результаты тестирования: {passed}/{total} тестов прошли")
    
    if passed == total:
        print("🎉 Все тесты команд прошли успешно!")
    else:
        print(f"⚠️ {total - passed} тестов не прошли")

if __name__ == "__main__":
    asyncio.run(main())
