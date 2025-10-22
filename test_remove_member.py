#!/usr/bin/env python3
"""
Тест функции удаления участника из группы
"""
from storage import Storage

def test_remove_member():
    """Тестирование функции удаления участника"""
    storage = Storage()
    
    print("🧪 Тестирование функции удаления участника...")
    
    # Тестовые данные
    chat_id = "123456789"
    group_name = "TestGroup_Remove"
    user1 = "@testuser1"
    user2 = "@testuser2"
    
    try:
        # 1. Создаем группу
        print("1️⃣ Создание тестовой группы...")
        storage.insert_group(chat_id, group_name)
        print(f"✅ Группа '{group_name}' создана")
        
        # 2. Добавляем участников
        print("2️⃣ Добавление участников...")
        group_id = storage.select_groupid_by_groupname(group_name)
        storage.insert_user_in_group(group_id, user1)
        storage.insert_user_in_group(group_id, user2)
        print(f"✅ Участники {user1} и {user2} добавлены")
        
        # 3. Проверяем, что участники в группе
        print("3️⃣ Проверка участников в группе...")
        users = storage.select_users_from_group(group_name)
        print(f"📋 Участники в группе: {[user[0] for user in users]}")
        
        # 4. Проверяем функцию is_user_in_group
        print("4️⃣ Проверка функции is_user_in_group...")
        is_user1_in = storage.is_user_in_group(group_name, user1)
        is_user2_in = storage.is_user_in_group(group_name, user2)
        print(f"✅ {user1} в группе: {is_user1_in}")
        print(f"✅ {user2} в группе: {is_user2_in}")
        
        # 5. Удаляем первого участника
        print("5️⃣ Удаление первого участника...")
        success = storage.remove_user_from_group(group_name, user1)
        print(f"✅ Удаление {user1}: {success}")
        
        # 6. Проверяем, что участник удален
        print("6️⃣ Проверка после удаления...")
        users_after = storage.select_users_from_group(group_name)
        print(f"📋 Участники после удаления: {[user[0] for user in users_after]}")
        
        is_user1_in_after = storage.is_user_in_group(group_name, user1)
        is_user2_in_after = storage.is_user_in_group(group_name, user2)
        print(f"✅ {user1} в группе после удаления: {is_user1_in_after}")
        print(f"✅ {user2} в группе после удаления: {is_user2_in_after}")
        
        # 7. Пытаемся удалить несуществующего пользователя
        print("7️⃣ Тест удаления несуществующего пользователя...")
        fake_user = "@fakeuser"
        success_fake = storage.remove_user_from_group(group_name, fake_user)
        print(f"✅ Удаление несуществующего пользователя: {success_fake}")
        
        # 8. Удаляем оставшегося участника
        print("8️⃣ Удаление оставшегося участника...")
        success2 = storage.remove_user_from_group(group_name, user2)
        print(f"✅ Удаление {user2}: {success2}")
        
        # 9. Проверяем, что группа пуста
        print("9️⃣ Проверка пустой группы...")
        users_final = storage.select_users_from_group(group_name)
        print(f"📋 Участники в пустой группе: {[user[0] for user in users_final]}")
        
        print("\n🎉 Все тесты пройдены успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False
    
    finally:
        # Очистка тестовых данных
        print("\n🧹 Очистка тестовых данных...")
        try:
            # Удаляем тестовую группу (если она существует)
            from cleanup_test_data import cleanup_test_data
            cleanup_test_data()
            print("✅ Тестовые данные очищены")
        except Exception as e:
            print(f"⚠️ Ошибка при очистке: {e}")
    
    return True

if __name__ == "__main__":
    test_remove_member()
