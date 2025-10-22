#!/usr/bin/env python3
"""
Скрипт для очистки тестовых данных из базы данных
"""

from storage import Storage

def cleanup_test_data():
    """Очистка тестовых данных"""
    try:
        storage = Storage()
        
        # Сначала удаляем балансы (зависимые данные)
        print("🧹 Очистка тестовых балансов...")
        
        query = storage.BalanceUserToUser.delete().where(
            storage.BalanceUserToUser.columns.FirstUserName.like("%test%") |
            storage.BalanceUserToUser.columns.SecondUserName.like("%test%")
        )
        result = storage.conn.execute(query)
        storage.conn.commit()
        
        print(f"✅ Удалено тестовых балансов: {result.rowcount}")
        
        # Затем удаляем пользователей групп
        print("🧹 Очистка тестовых пользователей...")
        
        query = storage.GroupUser.delete().where(storage.GroupUser.columns.UserId.like("%test%"))
        result = storage.conn.execute(query)
        storage.conn.commit()
        
        print(f"✅ Удалено тестовых пользователей: {result.rowcount}")
        
        # В конце удаляем группы
        print("🧹 Очистка тестовых групп...")
        
        query = storage.Group.delete().where(storage.Group.columns.ChatId == "12345")
        result = storage.conn.execute(query)
        storage.conn.commit()
        
        print(f"✅ Удалено тестовых групп: {result.rowcount}")
        
        print("🎉 Очистка тестовых данных завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке данных: {e}")

if __name__ == "__main__":
    cleanup_test_data()
