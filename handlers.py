from __future__ import annotations

from aiogram import types, F, Router
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from storage import Storage
import re
from config import SUPPORTED_CURRENCIES, DEFAULT_CURRENCY


router = Router()
storage = Storage()


# FSM состояния для интерактивного ввода
class GroupStates(StatesGroup):
    waiting_for_group_name = State()
    waiting_for_member_username = State()
    waiting_for_payment_amount = State()
    waiting_for_remove_member_username = State()
    waiting_for_currency_selection = State()
    waiting_for_payment_distribution = State()
    waiting_for_amount_distribution = State()
    waiting_for_parts_distribution = State()


@router.message(Command("start"))
async def start_handler(msg: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
        [InlineKeyboardButton(text="➕ Создать группу", callback_data="create_group")],
        [InlineKeyboardButton(text="👥 Добавить участника", callback_data="add_member")],
        [InlineKeyboardButton(text="❌ Удалить участника", callback_data="remove_member")],
        [InlineKeyboardButton(text="💰 Записать трату", callback_data="add_payment")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])
    
    await msg.answer(
        "👋 <b>Привет! Я помогу вам записывать все траты</b>\n\n"
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.message(Command("help"))
async def help_handler(msg: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
        [InlineKeyboardButton(text="➕ Создать группу", callback_data="create_group")]
    ])
    
    await msg.answer(
        "📖 <b>Справка по боту</b>\n\n"
        "Я помогу вам записывать и разделять траты между участниками.\n\n"
        "<b>Основные функции:</b>\n"
        "• Создание групп для разделения расходов\n"
        "• Добавление участников в группы\n"
        "• Запись трат и расчет балансов\n"
        "• Просмотр истории платежей\n\n"
        "Используйте кнопки ниже для навигации:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.message(Command("create"))
async def create_handler(msg: Message):
    command_string = msg.text.replace("/create", "")
    if command_string == "":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await msg.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Введите название группы: <code>/create [group_name]</code>\n\n"
            "Например: <code>/create [Поездка в отпуск]</code>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return

    arg_list = re.findall(r"\[(.*?)\]", command_string)
    arg_list = list(filter(lambda a: a != "" and a != " ", arg_list))
    storage.insert_group(msg.chat.id, arg_list[0], DEFAULT_CURRENCY)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
        [InlineKeyboardButton(text="👥 Добавить участника", callback_data="add_member")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await msg.answer(
        f"✅ <b>Группа создана!</b>\n\n"
        f"Группа <b>{arg_list[0]}</b> успешно создана.\n"
        f"Теперь вы можете добавить участников и записывать траты.",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.message(Command("show"))
async def show_handler(msg: Message):
    command_string = msg.text.replace("/show", "")
    if command_string == "":
        result = storage.select_group_from_chat_id(msg.chat.id)
        if len(result) == 0:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать группу", callback_data="create_group")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            await msg.answer(
                "📋 <b>Мои группы</b>\n\n"
                "У вас пока нет групп.\n"
                "Создайте первую группу для начала работы!",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            return

        keyboard_buttons = []
        for group in result:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"📊 {group}", 
                callback_data=f"group_balances_{group}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        groups_text = "\n".join([f"• {group}" for group in result])
        await msg.answer(
            f"📋 <b>Мои группы</b>\n\n"
            f"{groups_text}\n\n"
            f"Нажмите на группу, чтобы посмотреть балансы:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return

    arg_list = re.findall(r"\[(.*?)\]", command_string)
    arg_list = list(filter(lambda a: a != "" and a != " ", arg_list))
    balances = storage.get_balances_group(arg_list[0])
    balances.sort(key=lambda x:x[0])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Все группы", callback_data="show_groups")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    if not balances:
        await msg.answer(
            f"📊 <b>Балансы группы: {arg_list[0]}</b>\n\n"
            "В группе пока нет участников или платежей.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        # Группируем балансы по валютам
        balances_by_currency = {}
        for balance in balances:
            currency = balance[3] if len(balance) > 3 else 'RUB'
            if currency not in balances_by_currency:
                balances_by_currency[currency] = []
            balances_by_currency[currency].append(balance)
        
        # Формируем текст с балансами по валютам
        balances_lines = []
        for currency, currency_balances in balances_by_currency.items():
            currency_info = SUPPORTED_CURRENCIES.get(currency, {'symbol': currency})
            currency_lines = [f"• {balance[0]} → {balance[1]}: {balance[2]} {currency_info['symbol']}" for balance in currency_balances]
            balances_lines.extend(currency_lines)
        
        balances_text = "\n".join(balances_lines)
        await msg.answer(
            f"📊 <b>Балансы группы: {arg_list[0]}</b>\n\n"
            f"{balances_text}",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )


@router.message(Command("add"))
async def add_handler(msg: Message):
    command_string = msg.text.replace("/add", "")
    if command_string == "":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await msg.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Формат команды: <code>/add [GroupName] [@UserName]</code>\n\n"
            "Например: <code>/add [Поездка в отпуск] [@username]</code>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return

    arg_list = re.findall(r"\[(.*?)\]", command_string)
    arg_list = list(filter(lambda a: a != "" and a != " ", arg_list))
    storage.insert_user_in_group(msg.chat.id, arg_list[0], arg_list[1])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
        [InlineKeyboardButton(text="💰 Записать трату", callback_data="add_payment")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await msg.answer(
        f"✅ <b>Участник добавлен!</b>\n\n"
        f"Пользователь <b>{arg_list[1]}</b> добавлен в группу <b>{arg_list[0]}</b>.\n"
        f"Теперь можно записывать траты!",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


@router.message(Command("payment"))
async def payment_handler(msg: Message):
    command_string = msg.text.replace("/payment", "")
    if command_string == "":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await msg.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Формат команды: <code>/payment [GroupName] [@UserName] [Value]</code>\n\n"
            "Например: <code>/payment [Поездка в отпуск] [@username] [1000]</code>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return
    
    arg_list = re.findall(r"\[(.*?)\]", command_string)
    arg_list = list(filter(lambda a: a != "" and a != " ", arg_list))

    # Записываем трату - плательщик платит за всех участников группы
    group_name = arg_list[0]
    payer = arg_list[1]
    amount = float(arg_list[2])
    
    # Получаем всех участников группы
    group_id = storage.select_groupid_by_chatid_groupname(msg.chat.id, group_name)
    all_users = storage.select_users_from_group(group_id)
    
    # Распределяем трату между всеми участниками (включая плательщика)
    amount_per_person = amount / len(all_users)
    
    for user in all_users:
        if user != f"@{payer}":
            # Остальные участники должны плательщику
            storage.change_balance(group_name, user, f"@{payer}", str(amount_per_person))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Посмотреть балансы", callback_data=f"group_balances_{arg_list[0]}")],
        [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await msg.answer(
        f"✅ <b>Трата записана!</b>\n\n"
        f"В группе <b>{arg_list[0]}</b> записана трата:\n"
        f"• Кто платил: <b>{arg_list[1]}</b>\n"
        f"• Сумма: <b>{arg_list[2]} руб.</b>\n\n"
        f"Балансы обновлены!",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )




# Обработчики callback-запросов для кнопок
@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
        [InlineKeyboardButton(text="➕ Создать группу", callback_data="create_group")],
        [InlineKeyboardButton(text="👥 Добавить участника", callback_data="add_member")],
        [InlineKeyboardButton(text="❌ Удалить участника", callback_data="remove_member")],
        [InlineKeyboardButton(text="💰 Записать трату", callback_data="add_payment")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])
    
    await callback.message.edit_text(
        "👋 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "show_groups")
async def show_groups_callback(callback: CallbackQuery):
    groups = storage.select_group_from_chat_id(callback.message.chat.id)
    
    if not groups:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать группу", callback_data="create_group")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            "📋 <b>Мои группы</b>\n\n"
            "У вас пока нет групп.\n"
            "Создайте первую группу для начала работы!",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        keyboard_buttons = []
        for group in groups:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"📊 {group}", 
                callback_data=f"group_balances_{group}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        groups_text = "\n".join([f"• {group}" for group in groups])
        await callback.message.edit_text(
            f"📋 <b>Мои группы</b>\n\n"
            f"{groups_text}\n\n"
            f"Нажмите на группу, чтобы посмотреть балансы:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()


@router.callback_query(F.data == "create_group")
async def create_group_callback(callback: CallbackQuery, state: FSMContext):
    # Создаем кнопки для выбора валюты
    keyboard_buttons = []
    currencies = list(SUPPORTED_CURRENCIES.items())
    
    # Размещаем валюты по 2 в ряд
    for i in range(0, len(currencies), 2):
        row = []
        for j in range(2):
            if i + j < len(currencies):
                currency_code, currency_info = currencies[i + j]
                row.append(InlineKeyboardButton(
                    text=f"{currency_info['symbol']} {currency_code}",
                    callback_data=f"select_currency_{currency_code}"
                ))
        keyboard_buttons.append(row)
    
    keyboard_buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        "➕ <b>Создание группы</b>\n\n"
        "Выберите валюту для группы:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


# Обработчик выбора валюты
@router.callback_query(F.data.startswith("select_currency_"))
async def select_currency_callback(callback: CallbackQuery, state: FSMContext):
    currency_code = callback.data.replace("select_currency_", "")
    currency_info = SUPPORTED_CURRENCIES.get(currency_code)
    
    if not currency_info:
        await callback.answer("❌ Неверная валюта")
        return
    
    # Сохраняем выбранную валюту в состоянии
    await state.update_data(selected_currency=currency_code)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        f"➕ <b>Создание группы</b>\n\n"
        f"Выбрана валюта: <b>{currency_info['symbol']} {currency_code}</b>\n\n"
        f"Введите название группы:\n"
        f"Например: <i>Поездка в отпуск</i>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    # Устанавливаем состояние ожидания названия группы
    await state.set_state(GroupStates.waiting_for_group_name)
    await callback.answer()


# Обработчик ввода названия группы
@router.message(GroupStates.waiting_for_group_name)
async def process_group_name(msg: Message, state: FSMContext):
    group_name = msg.text.strip()
    
    # Проверяем, что название не пустое
    if not group_name:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
        ])
        await msg.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Название группы не может быть пустым.\n"
            "Попробуйте еще раз:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Создаем группу
    try:
        # Получаем выбранную валюту из состояния
        data = await state.get_data()
        currency = data.get('selected_currency', DEFAULT_CURRENCY)
        storage.insert_group(msg.chat.id, group_name, currency)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 Добавить участника", callback_data="add_member")],
            [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        currency_info = SUPPORTED_CURRENCIES.get(currency, SUPPORTED_CURRENCIES[DEFAULT_CURRENCY])
        await msg.answer(
            f"✅ <b>Группа создана!</b>\n\n"
            f"Группа <b>«{group_name}»</b> успешно создана.\n"
            f"Валюта: <b>{currency_info['symbol']} {currency}</b>\n\n"
            f"Теперь вы можете добавить участников и записывать траты.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Сбрасываем состояние
        await state.clear()
        
    except Exception as e:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="create_group")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await msg.answer(
            f"❌ <b>Ошибка при создании группы</b>\n\n"
            f"Не удалось создать группу. Возможно, группа с таким названием уже существует.\n"
            f"Попробуйте другое название.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Сбрасываем состояние
        await state.clear()


@router.callback_query(F.data == "add_member")
async def add_member_callback(callback: CallbackQuery, state: FSMContext):
    # Сначала показываем список групп для выбора
    groups = storage.select_group_from_chat_id(callback.message.chat.id)
    
    if not groups:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать группу", callback_data="create_group")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            "👥 <b>Добавление участника</b>\n\n"
            "У вас пока нет групп.\n"
            "Сначала создайте группу!",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    
    # Показываем список групп для выбора
    keyboard_buttons = []
    for group in groups:
        keyboard_buttons.append([InlineKeyboardButton(
            text=f"👥 Добавить в «{group}»", 
            callback_data=f"add_to_group_{group}"
        )])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    groups_text = "\n".join([f"• {group}" for group in groups])
    await callback.message.edit_text(
        f"👥 <b>Добавление участника</b>\n\n"
        f"Выберите группу:\n\n"
        f"{groups_text}",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


# Обработчик выбора группы для добавления участника
@router.callback_query(F.data.startswith("add_to_group_"))
async def select_group_for_member_callback(callback: CallbackQuery, state: FSMContext):
    group_name = callback.data.replace("add_to_group_", "")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="add_member")]
    ])
    
    await callback.message.edit_text(
        f"👥 <b>Добавление участника в группу «{group_name}»</b>\n\n"
        f"Введите username участника (с @ или без):\n"
        f"Например: <i>@username</i> или <i>username</i>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    # Сохраняем название группы в состоянии
    await state.update_data(selected_group=group_name)
    await state.set_state(GroupStates.waiting_for_member_username)
    await callback.answer()


# Обработчик ввода username участника
@router.message(GroupStates.waiting_for_member_username)
async def process_member_username(msg: Message, state: FSMContext):
    username = msg.text.strip()
    data = await state.get_data()
    group_name = data.get('selected_group')
    
    # Очищаем username от @ если есть
    if username.startswith('@'):
        username = username[1:]
    
    # Проверяем, что username не пустой
    if not username:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="add_member")]
        ])
        await msg.answer(
            "❌ <b>Ошибка</b>\n\n"
            "Username не может быть пустым.\n"
            "Попробуйте еще раз:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Добавляем участника
    try:
        storage.insert_user_in_group(msg.chat.id, group_name, f"@{username}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Записать трату", callback_data="add_payment")],
            [InlineKeyboardButton(text="👥 Добавить еще участника", callback_data="add_member")],
            [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await msg.answer(
            f"✅ <b>Участник добавлен!</b>\n\n"
            f"Пользователь <b>@{username}</b> добавлен в группу <b>«{group_name}»</b>.\n"
            f"Теперь можно записывать траты!",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Сбрасываем состояние
        await state.clear()
        
    except Exception as e:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=f"add_to_group_{group_name}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await msg.answer(
            f"❌ <b>Ошибка при добавлении участника</b>\n\n"
            f"Не удалось добавить участника. Возможно, пользователь уже в группе.\n"
            f"Попробуйте другого участника.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Сбрасываем состояние
        await state.clear()


@router.callback_query(F.data == "add_payment")
async def add_payment_callback(callback: CallbackQuery, state: FSMContext):
    # Сначала показываем список групп для выбора
    groups = storage.select_group_from_chat_id(callback.message.chat.id)
    
    if not groups:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать группу", callback_data="create_group")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            "💰 <b>Запись траты</b>\n\n"
            "У вас пока нет групп.\n"
            "Сначала создайте группу!",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    
    # Показываем список групп для выбора
    keyboard_buttons = []
    for group in groups:
        keyboard_buttons.append([InlineKeyboardButton(
            text=f"💰 Записать трату в «{group}»", 
            callback_data=f"payment_to_group_{group}"
        )])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    groups_text = "\n".join([f"• {group}" for group in groups])
    await callback.message.edit_text(
        f"💰 <b>Запись траты</b>\n\n"
        f"Выберите группу:\n\n"
        f"{groups_text}",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


# Обработчик выбора группы для записи траты
@router.callback_query(F.data.startswith("payment_to_group_"))
async def select_group_for_payment_callback(callback: CallbackQuery, state: FSMContext):
    group_name = callback.data.replace("payment_to_group_", "")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="add_payment")]
    ])
    
    # Получаем валюту группы
    group_currency = storage.get_group_currency(group_name)
    currency_info = SUPPORTED_CURRENCIES.get(group_currency, SUPPORTED_CURRENCIES[DEFAULT_CURRENCY])
    
    await callback.message.edit_text(
        f"💰 <b>Запись траты в группу «{group_name}»</b>\n\n"
        f"Валюта группы: <b>{currency_info['symbol']} {group_currency}</b>\n\n"
        f"Введите участников и суммы:\n"
        f"<i>username сумма username сумма ... [валюта]</i>\n\n"
        f"Примеры:\n"
        f"• <i>alice 1000</i> или <i>@alice 1000</i>\n"
        f"• <i>alice 100 USD</i> (с валютой)\n"
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    # Сохраняем название группы в состоянии
    await state.update_data(selected_group=group_name)
    await state.set_state(GroupStates.waiting_for_payment_amount)
    await callback.answer()


# Обработчик ввода данных траты
@router.message(GroupStates.waiting_for_payment_amount)
async def process_payment_data(msg: Message, state: FSMContext):
    payment_data = msg.text.strip()
    data = await state.get_data()
    group_name = data.get('selected_group')
    
    # Парсим ввод с несколькими участниками
    try:
        # Ищем паттерн username amount (с @ или без) и опциональную валюту
        import re
        pattern = r'@?(\w+)\s+(\d+(?:\.\d+)?)'
        matches = re.findall(pattern, payment_data)
        
        if not matches:
            raise ValueError("Неверный формат. Используйте: username amount username amount ...")
        
        # Проверяем, что все участники есть в группе
        group_id = storage.select_groupid_by_chatid_groupname(msg.chat.id, group_name)
        all_users = storage.select_users_from_group(group_id)
        all_usernames = [user[1:] for user in all_users]  # убираем @
        
        payments = []
        total_amount = 0
        
        for username, amount_str in matches:
            if username not in all_usernames:
                raise ValueError(f"Участник @{username} не найден в группе")
            
            try:
                amount_float = float(amount_str)
                if amount_float <= 0:
                    raise ValueError("Сумма должна быть положительной")
            except ValueError:
                raise ValueError(f"Неверная сумма для @{username}")
            
            payments.append((username, amount_float))
            total_amount += amount_float
        
        if not payments:
            raise ValueError("Не найдено ни одного участника")
        
        # Парсим валюту из ввода (если указана)
        currency = None
        payment_data_upper = payment_data.upper()
        for curr_code in SUPPORTED_CURRENCIES.keys():
            if curr_code in payment_data_upper:
                currency = curr_code
                break
        
        # Если валюта не указана, используем валюту группы
        if not currency:
            currency = storage.get_group_currency(group_name)
        
        # Сохраняем данные траты в FSM контексте
        await state.update_data(
            group_name=group_name,
            payments=payments,
            total_amount=total_amount,
            currency=currency,
            all_users=all_users
        )
        
        # Получаем информацию о валюте
        currency_info = SUPPORTED_CURRENCIES.get(currency, SUPPORTED_CURRENCIES[DEFAULT_CURRENCY])
        total_amount_text = f"{total_amount} {currency_info['symbol']}"
        
        # Формируем список участников и их сумм
        payments_text = "\n".join([f"• @{username}: {amount} {currency_info['symbol']}" for username, amount in payments])
        
        # Показываем кнопки выбора типа распределения
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚖️ Поровну", callback_data=f"distribute_equal_{group_name}")],
            [InlineKeyboardButton(text="💰 По суммам", callback_data=f"distribute_amounts_{group_name}")],
            [InlineKeyboardButton(text="🔢 Частями", callback_data=f"distribute_parts_{group_name}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="add_payment")]
        ])
        
        await msg.answer(
            f"💳 <b>Общая сумма: {total_amount_text}</b>\n"
            f"👥 Группа: <b>«{group_name}»</b>\n\n"
            f"<b>Участники и суммы:</b>\n{payments_text}\n\n"
            f"Выберите способ распределения траты:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Устанавливаем состояние ожидания выбора типа распределения
        await state.set_state(GroupStates.waiting_for_payment_distribution)
        
    except ValueError as e:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=f"payment_to_group_{group_name}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        error_message = "Неверный формат данных"
        if "Пустые данные" in str(e):
            error_message = "Все поля должны быть заполнены"
        elif "Сумма должна быть положительной" in str(e):
            error_message = "Сумма должна быть положительным числом"
        elif "Неверная сумма" in str(e):
            error_message = "Сумма должна быть числом"
        elif "Неподдерживаемая валюта" in str(e):
            error_message = "Неподдерживаемая валюта. Доступные валюты: " + ", ".join(SUPPORTED_CURRENCIES.keys())
        elif "Участник не в группе" in str(e):
            error_message = f"Участник <b>@{payer}</b> не состоит в группе <b>«{group_name}»</b>"
        elif "не найден в группе" in str(e):
            error_message = str(e)
            # Добавляем кнопку для добавления участника
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👥 Добавить участника", callback_data="add_member")],
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=f"payment_to_group_{group_name}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
        
        await msg.answer(
            f"❌ <b>Ошибка при записи траты</b>\n\n"
            f"{error_message}.\n"
            f"Попробуйте еще раз в формате: <i>username сумма username сумма ... [валюта]</i>\n"
            f"Например: <i>alice 1000 bob 2000</i> или <i>alice 100 bob 200 USD</i>\n"
            f"Доступные валюты: {', '.join(SUPPORTED_CURRENCIES.keys())}",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Сбрасываем состояние
        await state.clear()
    
    except Exception as e:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=f"payment_to_group_{group_name}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await msg.answer(
            f"❌ <b>Ошибка при записи траты</b>\n\n"
            f"Не удалось записать трату. Возможно, пользователь не в группе.\n"
            f"Попробуйте другого участника.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Сбрасываем состояние
        await state.clear()


@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
        [InlineKeyboardButton(text="➕ Создать группу", callback_data="create_group")]
    ])
    
    await callback.message.edit_text(
        "📖 <b>Справка по боту</b>\n\n"
        "Я помогу вам записывать и разделять траты между участниками.\n\n"
        "<b>Основные функции:</b>\n"
        "• Создание групп для разделения расходов\n"
        "• Добавление участников в группы\n"
        "• Запись трат и расчет балансов\n"
        "• Просмотр истории платежей\n\n"
        "Используйте кнопки ниже для навигации:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("group_balances_"))
async def group_balances_callback(callback: CallbackQuery):
    group_name = callback.data.replace("group_balances_", "")
    
    # Получаем ID группы
    group_id = storage.select_groupid_by_chatid_groupname(callback.message.chat.id, group_name)
    if group_id == -1:
        await callback.answer("❌ Группа не найдена", show_alert=True)
        return
    
    # Получаем участников группы
    users = storage.select_users_from_group(group_id)
    balances = storage.get_balances_group(group_name)
    
    # Отладочная информация
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Все группы", callback_data="show_groups")],
        [InlineKeyboardButton(text="🗑️ Удалить группу", callback_data=f"delete_group_{group_name}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    # Формируем текст с участниками и балансами
    if not users:
        await callback.message.edit_text(
            f"📊 <b>Группа: {group_name}</b>\n\n"
            "❌ В группе нет участников.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        # Показываем участников
        users_text = "\n".join([f"• {user}" for user in users])
    
        if not balances or all(abs(balance[2]) < 0.01 for balance in balances):
            await callback.message.edit_text(
                f"📊 <b>Группа: {group_name}</b>\n\n"
                f"👥 <b>Участники ({len(users)}):</b>\n{users_text}\n\n"
                "💰 <b>Балансы:</b>\n✅ Все долги равны нулю - в группе нет задолженностей!",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        else:
            # Показываем все ненулевые балансы (и положительные, и отрицательные)
            non_zero_balances = [b for b in balances if abs(b[2]) > 0.01]
            if non_zero_balances:
                # Группируем балансы по участникам и валютам
                user_balances = {}
                for balance in non_zero_balances:
                    user = balance[0]
                    amount = balance[2]
                    currency = balance[3] if len(balance) > 3 else 'RUB'
                    
                    if user not in user_balances:
                        user_balances[user] = {}
                    if currency not in user_balances[user]:
                        user_balances[user][currency] = 0
                    user_balances[user][currency] += amount
                
                # Формируем текст с балансами по валютам
                balances_lines = []
                for user, currencies in user_balances.items():
                    user_balance_lines = []
                    for currency, amount in currencies.items():
                        if abs(amount) > 0.01:  # Показываем только ненулевые балансы
                            currency_info = SUPPORTED_CURRENCIES.get(currency, {'symbol': currency})
                            user_balance_lines.append(f"{amount:.2f} {currency_info['symbol']}")
                    
                    if user_balance_lines:
                        # Правильно соединяем валюты с учетом знаков
                        balance_text = ""
                        for i, balance_part in enumerate(user_balance_lines):
                            if i == 0:
                                balance_text = balance_part
                            else:
                                # Если следующий элемент отрицательный, добавляем пробел
                                # Если положительный, добавляем " + "
                                if balance_part.startswith('-'):
                                    balance_text += f" {balance_part}"
                                else:
                                    balance_text += f" + {balance_part}"
                        
                        balances_lines.append(f"• {user} => {balance_text}")
                
                balances_text = "\n".join(balances_lines)
                
                await callback.message.edit_text(
                    f"📊 <b>Группа: {group_name}</b>\n\n"
                    f"👥 <b>Участники ({len(users)}):</b>\n{users_text}\n\n"
                    f"💰 <b>Балансы:</b>\n{balances_text}",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await callback.message.edit_text(
                    f"📊 <b>Группа: {group_name}</b>\n\n"
                    f"👥 <b>Участники ({len(users)}):</b>\n{users_text}\n\n"
                    "💰 <b>Балансы:</b>\n✅ Все долги равны нулю - в группе нет задолженностей!",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
    
    await callback.answer()

@router.callback_query(F.data == "remove_member")
async def remove_member_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Удалить участника'"""
    groups = storage.select_group_from_chat_id(callback.from_user.id)
    
    if not groups:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать группу", callback_data="create_group")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            "❌ <b>Удаление участника</b>\n\n"
            "У вас пока нет групп. Сначала создайте группу.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        # Создаем кнопки для выбора группы
        keyboard_buttons = []
        for group in groups:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"📁 {group}", 
                callback_data=f"remove_from_group_{group}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            "❌ <b>Удаление участника</b>\n\n"
            "Выберите группу, из которой хотите удалить участника:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("remove_from_group_"))
async def remove_from_group_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора группы для удаления участника"""
    group_name = callback.data.replace("remove_from_group_", "")
    
    # Получаем ID группы по названию
    group_id = storage.select_groupid_by_chatid_groupname(callback.from_user.id, group_name)
    if not group_id:
        await callback.answer("❌ Группа не найдена", show_alert=True)
        return
    
    # Получаем список участников группы
    users = storage.select_users_from_group(group_id)
    
    if not users:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 Добавить участника", callback_data="add_member")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            f"❌ <b>Удаление участника из группы: {group_name}</b>\n\n"
            "В группе нет участников для удаления.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        # Создаем кнопки для выбора участника
        keyboard_buttons = []
        for user in users:
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"👤 {user}", 
                callback_data=f"remove_user_{group_name}_{user}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        users_list = "\n".join([f"• {user}" for user in users])
        await callback.message.edit_text(
            f"❌ <b>Удаление участника из группы: {group_name}</b>\n\n"
            f"<b>Участники группы:</b>\n{users_list}\n\n"
            "Выберите участника для удаления:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("remove_user_"))
async def remove_user_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик удаления конкретного пользователя - показываем подтверждение"""
    data_parts = callback.data.replace("remove_user_", "").split("_", 1)
    group_name = data_parts[0]
    user_name = data_parts[1]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить участника", callback_data=f"confirm_remove_user_{group_name}_{user_name}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"remove_from_group_{group_name}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы действительно хотите удалить участника <b>{user_name}</b> из группы <b>«{group_name}»</b>?\n\n"
        f"❗ <b>Внимание:</b> Это действие нельзя отменить!\n"
        f"Все связанные с участником балансы и долги будут удалены навсегда.",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_remove_user_"))
async def confirm_remove_user_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик подтверждения удаления участника"""
    data_parts = callback.data.replace("confirm_remove_user_", "").split("_", 1)
    group_name = data_parts[0]
    user_name = data_parts[1]
    
    # Удаляем пользователя из группы
    success = storage.remove_user_from_group(group_name, user_name)
    
    if success:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Посмотреть балансы", callback_data=f"group_balances_{group_name}")],
            [InlineKeyboardButton(text="❌ Удалить еще участника", callback_data="remove_member")],
            [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            f"✅ <b>Участник удален!</b>\n\n"
            f"Пользователь <b>{user_name}</b> удален из группы <b>«{group_name}»</b>.\n"
            f"Все связанные с ним балансы также удалены.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="remove_member")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при удалении</b>\n\n"
            f"Не удалось удалить пользователя <b>{user_name}</b> из группы <b>«{group_name}»</b>.\n"
            f"Возможно, пользователь не был найден в группе.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()




@router.callback_query(F.data.startswith("delete_group_"))
async def delete_group_callback(callback: CallbackQuery):
    """Обработчик удаления группы - показываем подтверждение"""
    group_name = callback.data.replace("delete_group_", "")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить группу", callback_data=f"confirm_delete_group_{group_name}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"group_balances_{group_name}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы действительно хотите удалить группу <b>«{group_name}»</b>?\n\n"
        f"❗ <b>Внимание:</b> Это действие нельзя отменить!\n"
        f"Все данные группы (участники, траты, балансы) будут удалены навсегда.",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_group_"))
async def confirm_delete_group_callback(callback: CallbackQuery):
    """Обработчик подтверждения удаления группы"""
    success = False
    group_name = ""
    
    try:
        group_name = callback.data.replace("confirm_delete_group_", "")
        # Получаем ID группы
        group_id = storage.select_groupid_by_chatid_groupname(callback.from_user.id, group_name)
        
        if group_id == -1 or not group_id:
            await callback.answer("❌ Группа не найдена", show_alert=True)
            return
        
        # Удаляем группу (это должно удалить все связанные записи)
        success = storage.delete_group(group_id)
        
    except Exception as e:
        await callback.answer("❌ Произошла ошибка при удалении группы", show_alert=True)
        return
    
    if success:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
            [InlineKeyboardButton(text="➕ Создать группу", callback_data="create_group")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            f"✅ <b>Группа удалена!</b>\n\n"
            f"Группа <b>«{group_name}»</b> и все связанные с ней данные удалены.\n"
            f"Все участники, балансы и платежи также удалены.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при удалении</b>\n\n"
            f"Не удалось удалить группу <b>«{group_name}»</b>.\n"
            f"Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()


# Обработчик выбора распределения поровну
@router.callback_query(lambda c: c.data.startswith("distribute_equal_"))
async def distribute_equal_callback(callback: CallbackQuery, state: FSMContext):
    group_name = callback.data.replace("distribute_equal_", "")
    
    # Получаем данные из FSM контекста
    data = await state.get_data()
    payments = data.get('payments', [])
    total_amount = data.get('total_amount', 0)
    currency = data.get('currency')
    all_users = data.get('all_users', [])
    
    # Распределяем поровну между всеми участниками группы
    amount_per_person = total_amount / len(all_users)
    
    # Записываем балансы: каждый участник должен плательщикам
    for user in all_users:
        for payer_username, payer_amount in payments:
            payer_user = f"@{payer_username}"
            if user != payer_user:
                # Участник должен плательщику пропорциональную часть
                user_share = amount_per_person
                storage.change_balance(group_name, user, payer_user, str(user_share), currency)
    
    # Получаем информацию о валюте
    currency_info = SUPPORTED_CURRENCIES.get(currency, SUPPORTED_CURRENCIES[DEFAULT_CURRENCY])
    total_amount_text = f"{total_amount} {currency_info['symbol']}"
    
    # Формируем список плательщиков
    payers_text = ", ".join([f"@{username}" for username, _ in payments])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Посмотреть балансы", callback_data=f"group_balances_{group_name}")],
        [InlineKeyboardButton(text="💰 Записать еще трату", callback_data="add_payment")],
        [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        f"✅ <b>Трата записана!</b>\n\n"
        f"В группе <b>«{group_name}»</b> записана трата:\n"
        f"• Плательщики: <b>{payers_text}</b>\n"
        f"• Общая сумма: <b>{total_amount_text}</b>\n"
        f"• Распределение: <b>Поровну</b>\n\n"
        f"Балансы обновлены!",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    # Сбрасываем состояние
    await state.clear()
    await callback.answer()


# Обработчик выбора распределения по суммам
@router.callback_query(lambda c: c.data.startswith("distribute_amounts_"))
async def distribute_amounts_callback(callback: CallbackQuery, state: FSMContext):
    group_name = callback.data.replace("distribute_amounts_", "")
    
    # Получаем данные из FSM контекста
    data = await state.get_data()
    all_users = data.get('all_users')
    
    # Формируем список участников
    users_list = "\n".join([f"• {user}" for user in all_users])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="add_payment")]
    ])
    
    await callback.message.edit_text(
        f"💰 <b>Распределение по суммам</b>\n\n"
        f"👥 <b>Участники группы:</b>\n{users_list}\n\n"
        f"📝 <b>Введите суммы для каждого участника:</b>\n"
        f"<code>имя сумма имя сумма ...</code>\n\n"
        f"<b>Пример:</b>\n"
        f"<code>@alice 100 @bob 200 @charlie 50</code>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    # Устанавливаем состояние ожидания ввода сумм
    await state.set_state(GroupStates.waiting_for_amount_distribution)
    await callback.answer()


# Обработчик выбора распределения частями
@router.callback_query(lambda c: c.data.startswith("distribute_parts_"))
async def distribute_parts_callback(callback: CallbackQuery, state: FSMContext):
    group_name = callback.data.replace("distribute_parts_", "")
    
    # Получаем данные из FSM контекста
    data = await state.get_data()
    all_users = data.get('all_users')
    
    # Формируем список участников
    users_list = "\n".join([f"• {user}" for user in all_users])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="add_payment")]
    ])
    
    await callback.message.edit_text(
        f"🔢 <b>Распределение частями</b>\n\n"
        f"👥 <b>Участники группы:</b>\n{users_list}\n\n"
        f"📝 <b>Введите количество частей для каждого участника:</b>\n"
        f"<code>имя [количество]x имя [количество]x ...</code>\n\n"
        f"<b>Пример:</b>\n"
        f"<code>@alice 2x @bob 1x @charlie 3x</code>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    # Устанавливаем состояние ожидания ввода частей
    await state.set_state(GroupStates.waiting_for_parts_distribution)
    await callback.answer()


# Обработчик ввода сумм для распределения
@router.message(GroupStates.waiting_for_amount_distribution)
async def process_amount_distribution(msg: Message, state: FSMContext):
    try:
        # Получаем данные из FSM контекста
        data = await state.get_data()
        group_name = data.get('group_name')
        payments = data.get('payments', [])  # Список плательщиков
        amount = data.get('total_amount')  # Используем total_amount вместо amount
        currency = data.get('currency')
        all_users = data.get('all_users')
        
        # Получаем список плательщиков
        payers = [f"@{username}" for username, _ in payments]
        
        # Парсим введенные суммы
        distribution_text = msg.text.strip()
        distributions = {}
        total_distributed = 0
        
        # Парсим ввод с помощью регулярного выражения
        import re
        pattern = r'@?(\w+)\s+(\d+(?:\.\d+)?)'
        matches = re.findall(pattern, distribution_text)
        
        if not matches:
            raise ValueError("Неверный формат. Используйте: имя сумма имя сумма ...")
        
        for username, amount_str in matches:
            name = f"@{username}"
            try:
                amount_value = float(amount_str)
                if amount_value <= 0:
                    raise ValueError("Сумма должна быть положительной")
            except ValueError:
                raise ValueError(f"Неверная сумма для {name}")
            
            # Проверяем, что участник есть в группе
            if name not in all_users:
                raise ValueError(f"Участник {name} не найден в группе")
            
            distributions[name] = amount_value
            total_distributed += amount_value
        
        # Проверяем, что сумма совпадает
        if abs(total_distributed - amount) > 0.01:
            raise ValueError(f"Сумма распределения ({total_distributed}) не совпадает с суммой траты ({amount})")
        
        # Записываем траты (исключаем плательщиков)
        for user, user_amount in distributions.items():
            if user not in payers:  # Исключаем всех плательщиков
                # Каждый плательщик получает долю от этого пользователя
                for payer_username, _ in payments:
                    storage.change_balance(group_name, user, f"@{payer_username}", str(user_amount), currency)
        
        # Получаем информацию о валюте
        currency_info = SUPPORTED_CURRENCIES.get(currency, SUPPORTED_CURRENCIES[DEFAULT_CURRENCY])
        amount_text = f"{amount} {currency_info['symbol']}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Посмотреть балансы", callback_data=f"group_balances_{group_name}")],
            [InlineKeyboardButton(text="💰 Записать еще трату", callback_data="add_payment")],
            [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        # Формируем список плательщиков
        payers_text = ", ".join([f"@{username}" for username, _ in payments])
        
        # Формируем список распределения
        distribution_list = "\n".join([f"• {user}: {amount} {currency_info['symbol']}" for user, amount in distributions.items()])
        
        await msg.answer(
            f"✅ <b>Трата записана!</b>\n\n"
            f"В группе <b>«{group_name}»</b> записана трата:\n"
            f"• Плательщики: <b>{payers_text}</b>\n"
            f"• Общая сумма: <b>{amount_text}</b>\n"
            f"• Распределение: <b>По суммам</b>\n\n"
            f"<b>Детали:</b>\n{distribution_list}\n\n"
            f"Балансы обновлены!",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Сбрасываем состояние
        await state.clear()
        
    except ValueError as e:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=f"distribute_amounts_{group_name}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="add_payment")]
        ])
        
        await msg.answer(
            f"❌ <b>Ошибка ввода</b>\n\n"
            f"<b>Причина:</b> {str(e)}\n\n"
            f"<b>Правильный формат:</b>\n"
            f"<code>имя сумма имя сумма ...</code>\n\n"
            f"<b>Пример:</b>\n"
            f"<code>@alice 100 @bob 200 @charlie 50</code>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )


# Обработчик ввода частей для распределения
@router.message(GroupStates.waiting_for_parts_distribution)
async def process_parts_distribution(msg: Message, state: FSMContext):
    try:
        # Получаем данные из FSM контекста
        data = await state.get_data()
        group_name = data.get('group_name')
        payments = data.get('payments', [])  # Список плательщиков
        amount = data.get('total_amount')  # Используем total_amount вместо amount
        currency = data.get('currency')
        all_users = data.get('all_users')
        
        # Получаем список плательщиков
        payers = [f"@{username}" for username, _ in payments]
        
        # Парсим введенные части
        distribution_text = msg.text.strip()
        parts_distribution = {}
        total_parts = 0
        
        # Парсим ввод с помощью регулярного выражения
        import re
        pattern = r'@?(\w+)\s+(\d+)x'
        matches = re.findall(pattern, distribution_text)
        
        if not matches:
            raise ValueError("Неверный формат. Используйте: имя [количество]x имя [количество]x ...")
        
        for username, parts_str in matches:
            name = f"@{username}"
            try:
                parts_value = int(parts_str)
                if parts_value <= 0:
                    raise ValueError("Количество частей должно быть положительным")
            except ValueError:
                raise ValueError(f"Неверное количество частей для {name}")
            
            # Проверяем, что участник есть в группе
            if name not in all_users:
                raise ValueError(f"Участник {name} не найден в группе")
            
            parts_distribution[name] = parts_value
            total_parts += parts_value
        
        if total_parts == 0:
            raise ValueError("Общее количество частей не может быть равно нулю")
        
        # Вычисляем сумму за одну часть
        amount_per_part = amount / total_parts
        
        # Записываем траты (исключаем плательщиков)
        for user, user_parts in parts_distribution.items():
            user_amount = amount_per_part * user_parts
            if user not in payers:  # Исключаем всех плательщиков
                # Каждый плательщик получает долю от этого пользователя
                for payer_username, _ in payments:
                    storage.change_balance(group_name, user, f"@{payer_username}", str(user_amount), currency)
        
        # Получаем информацию о валюте
        currency_info = SUPPORTED_CURRENCIES.get(currency, SUPPORTED_CURRENCIES[DEFAULT_CURRENCY])
        amount_text = f"{amount} {currency_info['symbol']}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Посмотреть балансы", callback_data=f"group_balances_{group_name}")],
            [InlineKeyboardButton(text="💰 Записать еще трату", callback_data="add_payment")],
            [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        # Формируем список плательщиков
        payers_text = ", ".join([f"@{username}" for username, _ in payments])
        
        # Формируем список распределения
        distribution_list = "\n".join([f"• {user}: {parts}x = {amount_per_part * parts:.2f} {currency_info['symbol']}" for user, parts in parts_distribution.items()])
        
        await msg.answer(
            f"✅ <b>Трата записана!</b>\n\n"
            f"В группе <b>«{group_name}»</b> записана трата:\n"
            f"• Плательщики: <b>{payers_text}</b>\n"
            f"• Общая сумма: <b>{amount_text}</b>\n"
            f"• Распределение: <b>Частями</b>\n"
            f"• Всего частей: <b>{total_parts}</b>\n"
            f"• За часть: <b>{amount_per_part:.2f} {currency_info['symbol']}</b>\n\n"
            f"<b>Детали:</b>\n{distribution_list}\n\n"
            f"Балансы обновлены!",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Сбрасываем состояние
        await state.clear()
        
    except ValueError as e:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=f"distribute_parts_{group_name}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="add_payment")]
        ])
        
        await msg.answer(
            f"❌ <b>Ошибка ввода</b>\n\n"
            f"<b>Причина:</b> {str(e)}\n\n"
            f"<b>Правильный формат:</b>\n"
            f"<code>имя [количество]x имя [количество]x ...</code>\n\n"
            f"<b>Пример:</b>\n"
            f"<code>@alice 2x @bob 1x @charlie 3x</code>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
