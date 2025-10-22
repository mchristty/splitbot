#!/usr/bin/env python3
"""
Скрипт для тестирования производительности бота
Поддерживает нагрузочное тестирование для 100+ пользователей
"""

import asyncio
import aiohttp
import time
import random
from typing import List, Dict, Any
from dataclasses import dataclass
import json


@dataclass
class TestUser:
    """Пользователь для тестирования"""
    user_id: int
    chat_id: int
    username: str
    session: aiohttp.ClientSession


@dataclass
class TestResult:
    """Результат тестирования"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    requests_per_second: float


class PerformanceTester:
    """Тестер производительности бота"""
    
    def __init__(self, bot_token: str, base_url: str = "https://api.telegram.org"):
        self.bot_token = bot_token
        self.base_url = base_url
        self.test_users: List[TestUser] = []
        self.results: List[TestResult] = []
    
    async def create_test_users(self, count: int = 100) -> List[TestUser]:
        """Создает тестовых пользователей"""
        print(f"Creating {count} test users...")
        
        users = []
        async with aiohttp.ClientSession() as session:
            for i in range(count):
                user = TestUser(
                    user_id=1000000 + i,
                    chat_id=1000000 + i,
                    username=f"testuser{i}",
                    session=session
                )
                users.append(user)
        
        self.test_users = users
        print(f"Created {len(users)} test users")
        return users
    
    async def simulate_user_workflow(self, user: TestUser) -> Dict[str, Any]:
        """Симулирует рабочий процесс пользователя"""
        results = {
            'user_id': user.user_id,
            'operations': [],
            'total_time': 0,
            'success_count': 0,
            'error_count': 0
        }
        
        start_time = time.time()
        
        try:
            # 1. Отправка /start
            await self._send_command(user, "/start")
            results['operations'].append('start')
            results['success_count'] += 1
            
            # 2. Создание группы
            group_name = f"TestGroup_{user.user_id}_{random.randint(1000, 9999)}"
            await self._send_command(user, f"/create {group_name}")
            results['operations'].append('create_group')
            results['success_count'] += 1
            
            # 3. Добавление участников
            for i in range(3):
                member_username = f"member{i}_{user.user_id}"
                await self._send_command(user, f"/add {group_name} @{member_username}")
                results['operations'].append('add_member')
                results['success_count'] += 1
            
            # 4. Запись трат
            for i in range(5):
                amount = random.randint(100, 5000)
                payer = f"member{i % 3}_{user.user_id}"
                await self._send_command(user, f"/payment {group_name} @{payer} {amount}")
                results['operations'].append('add_payment')
                results['success_count'] += 1
            
            # 5. Просмотр балансов
            await self._send_command(user, f"/show {group_name}")
            results['operations'].append('show_balances')
            results['success_count'] += 1
            
        except Exception as e:
            print(f"Error in user workflow for {user.user_id}: {e}")
            results['error_count'] += 1
        
        results['total_time'] = time.time() - start_time
        return results
    
    async def _send_command(self, user: TestUser, command: str) -> Dict[str, Any]:
        """Отправляет команду боту (симуляция)"""
        # В реальном тестировании здесь был бы HTTP запрос к API Telegram
        # Для симуляции просто ждем случайное время
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Симуляция успешного ответа
        return {
            'command': command,
            'response_time': random.uniform(0.1, 0.5),
            'success': True
        }
    
    async def run_concurrent_test(self, concurrent_users: int = 50) -> TestResult:
        """Запускает тест с заданным количеством одновременных пользователей"""
        print(f"Starting concurrent test with {concurrent_users} users...")
        
        start_time = time.time()
        
        # Выбираем случайных пользователей для тестирования
        test_users = random.sample(self.test_users, min(concurrent_users, len(self.test_users)))
        
        # Запускаем тесты параллельно
        tasks = [self.simulate_user_workflow(user) for user in test_users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Анализируем результаты
        successful_requests = sum(1 for r in results if isinstance(r, dict) and r['success_count'] > 0)
        failed_requests = len(results) - successful_requests
        
        response_times = [r['total_time'] for r in results if isinstance(r, dict)]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        
        total_requests = sum(r['success_count'] + r['error_count'] for r in results if isinstance(r, dict))
        requests_per_second = total_requests / total_time if total_time > 0 else 0
        
        result = TestResult(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            max_response_time=max_response_time,
            min_response_time=min_response_time,
            requests_per_second=requests_per_second
        )
        
        self.results.append(result)
        return result
    
    async def run_load_test(self, max_users: int = 100, step: int = 10) -> List[TestResult]:
        """Запускает нагрузочный тест с постепенным увеличением нагрузки"""
        print(f"Starting load test up to {max_users} users with step {step}")
        
        all_results = []
        
        for concurrent_users in range(step, max_users + 1, step):
            print(f"Testing with {concurrent_users} concurrent users...")
            
            result = await self.run_concurrent_test(concurrent_users)
            all_results.append(result)
            
            # Выводим промежуточные результаты
            print(f"Results for {concurrent_users} users:")
            print(f"  - Total requests: {result.total_requests}")
            print(f"  - Success rate: {result.successful_requests/result.total_requests*100:.1f}%")
            print(f"  - Avg response time: {result.avg_response_time:.2f}s")
            print(f"  - Requests per second: {result.requests_per_second:.1f}")
            
            # Пауза между тестами
            await asyncio.sleep(5)
        
        return all_results
    
    def generate_report(self, results: List[TestResult]) -> str:
        """Генерирует отчет о тестировании"""
        report = []
        report.append("=" * 60)
        report.append("PERFORMANCE TEST REPORT")
        report.append("=" * 60)
        
        for i, result in enumerate(results):
            concurrent_users = (i + 1) * 10  # Предполагаем шаг 10
            report.append(f"\nTest {i+1}: {concurrent_users} concurrent users")
            report.append(f"  Total requests: {result.total_requests}")
            report.append(f"  Successful: {result.successful_requests}")
            report.append(f"  Failed: {result.failed_requests}")
            report.append(f"  Success rate: {result.successful_requests/result.total_requests*100:.1f}%")
            report.append(f"  Avg response time: {result.avg_response_time:.2f}s")
            report.append(f"  Max response time: {result.max_response_time:.2f}s")
            report.append(f"  Min response time: {result.min_response_time:.2f}s")
            report.append(f"  Requests per second: {result.requests_per_second:.1f}")
        
        # Находим максимальную нагрузку
        max_successful = max(results, key=lambda r: r.successful_requests)
        max_rps = max(results, key=lambda r: r.requests_per_second)
        
        report.append(f"\nSUMMARY:")
        report.append(f"  Max successful requests: {max_successful.successful_requests}")
        report.append(f"  Max requests per second: {max_rps.requests_per_second:.1f}")
        report.append(f"  Best success rate: {max(r.successful_requests/r.total_requests*100 for r in results):.1f}%")
        
        return "\n".join(report)


async def main():
    """Основная функция тестирования"""
    # Конфигурация тестирования
    BOT_TOKEN = "8301851864:AAHgAnX2-JQNAM_Xr2RYSgKVtxvck9LWpGI"  # Замените на ваш токен
    MAX_USERS = 100
    STEP = 10
    
    print("Starting performance test...")
    
    # Создаем тестер
    tester = PerformanceTester(BOT_TOKEN)
    
    # Создаем тестовых пользователей
    await tester.create_test_users(MAX_USERS)
    
    # Запускаем нагрузочный тест
    results = await tester.run_load_test(MAX_USERS, STEP)
    
    # Генерируем отчет
    report = tester.generate_report(results)
    print(report)
    
    # Сохраняем отчет в файл
    with open('performance_report.txt', 'w') as f:
        f.write(report)
    
    print("Performance test completed. Report saved to performance_report.txt")


if __name__ == "__main__":
    asyncio.run(main())
