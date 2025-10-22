# Makefile для разработки Telegram бота

.PHONY: help install test run dev clean test-db test-commands cleanup

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip3 install -r requirements.txt
	pip3 install psycopg2-binary

test: ## Запустить все тесты
	@echo "🧪 Запуск тестов команд..."
	python3 test_commands.py

test-db: ## Тестировать только базу данных
	@echo "🧪 Тестирование базы данных..."
	python3 test_commands.py

test-commands: ## Тестировать только команды
	python3 test_commands.py

run: ## Запустить бота в продакшн режиме
	python3 main.py

clean: ## Очистить тестовые данные
	python3 cleanup_test_data.py

cleanup: clean ## Алиас для clean

logs: ## Показать логи разработки
	tail -f bot_dev.log

stop: ## Остановить все процессы бота
	pkill -f "python3.*main.py" || true

restart: stop dev ## Перезапустить бота в режиме разработки


status: ## Показать статус процессов
	@echo "Процессы бота:"
	@ps aux | grep -E "main\.py" | grep -v grep || echo "Бот не запущен"

