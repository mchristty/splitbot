#!/usr/bin/env python3
"""
Скрипт для тестирования бота через API
"""
import asyncio
import aiohttp
import json
from test_config import TEST_BOT_TOKEN

async def test_bot():
    """Тестирование бота через Telegram API"""
    base_url = f"https://api.telegram.org/bot{TEST_BOT_TOKEN}"
    
    async with aiohttp.ClientSession() as session:
        # 1. Проверяем информацию о боте
        print("🤖 Проверяем информацию о боте...")
        async with session.get(f"{base_url}/getMe") as response:
            if response.status == 200:
                bot_info = await response.json()
                if bot_info.get("ok"):
                    print(f"✅ Бот: @{bot_info['result']['username']} ({bot_info['result']['first_name']})")
                else:
                    print(f"❌ Ошибка: {bot_info}")
                    return
            else:
                print(f"❌ HTTP ошибка: {response.status}")
                return
        
        # 2. Получаем обновления
        print("\n📨 Проверяем обновления...")
        async with session.get(f"{base_url}/getUpdates") as response:
            if response.status == 200:
                updates = await response.json()
                if updates.get("ok"):
                    print(f"✅ Получено {len(updates['result'])} обновлений")
                    if updates['result']:
                        print("📋 Последние обновления:")
                        for update in updates['result'][-3:]:  # Показываем последние 3
                            if 'message' in update:
                                msg = update['message']
                                print(f"  - Сообщение от {msg['from']['first_name']}: {msg.get('text', 'Нет текста')}")
                            elif 'callback_query' in update:
                                cb = update['callback_query']
                                print(f"  - Callback от {cb['from']['first_name']}: {cb['data']}")
                else:
                    print(f"❌ Ошибка получения обновлений: {updates}")
            else:
                print(f"❌ HTTP ошибка при получении обновлений: {response.status}")

if __name__ == "__main__":
    print("🚀 Тестирование бота...")
    asyncio.run(test_bot())
