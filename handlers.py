from __future__ import annotations

from aiogram import types, F, Router
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from storage import Storage
import re


router = Router()
storage = Storage()


# FSM состояния для интерактивного ввода
class GroupStates(StatesGroup):
    waiting_for_group_name = State()
    waiting_for_member_username = State()
    waiting_for_payment_amount = State()
    waiting_for_remove_member_username = State()


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
    storage.insert_group(msg.chat.id, arg_list[0])
    
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
        balances_text = "\n".join([f"• {balance[0]} → {balance[1]}: {balance[2]}" for balance in balances])
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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        "➕ <b>Создание группы</b>\n\n"
        "Введите название группы:\n"
        "Например: <i>Поездка в отпуск</i>",
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
        storage.insert_group(msg.chat.id, group_name)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 Добавить участника", callback_data="add_member")],
            [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await msg.answer(
            f"✅ <b>Группа создана!</b>\n\n"
            f"Группа <b>«{group_name}»</b> успешно создана.\n"
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
    
    await callback.message.edit_text(
        f"💰 <b>Запись траты в группу «{group_name}»</b>\n\n"
        f"Введите данные через запятую:\n"
        f"<i>кто_платил, сумма</i>\n\n"
        f"Например: <i>@alice, 1000</i> или <i>alice, 1000</i>",
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
    
    # Парсим ввод через запятую
    try:
        parts = [part.strip() for part in payment_data.split(',')]
        
        if len(parts) != 2:
            raise ValueError("Неверный формат")
        
        payer, amount = parts
        
        # Очищаем payer от @ если есть
        if payer.startswith('@'):
            payer = payer[1:]
        
        # Проверяем, что данные не пустые
        if not payer or not amount:
            raise ValueError("Пустые данные")
        
        # Парсим сумму
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                raise ValueError("Сумма должна быть положительной")
        except ValueError:
            raise ValueError("Неверная сумма")
        
        # Проверяем, что участник есть в группе
        if not storage.is_user_in_group(group_name, f"@{payer}"):
            raise ValueError("Участник не в группе")
        
        # Записываем трату - плательщик платит за всех участников группы
        # Получаем всех участников группы
        group_id = storage.select_groupid_by_chatid_groupname(msg.chat.id, group_name)
        all_users = storage.select_users_from_group(group_id)
        
        # Распределяем трату между всеми участниками (включая плательщика)
        amount_per_person = amount_float / len(all_users)
        
        for user in all_users:
            if user != f"@{payer}":
                # Остальные участники должны плательщику
                storage.change_balance(group_name, user, f"@{payer}", str(amount_per_person))
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Посмотреть балансы", callback_data=f"group_balances_{group_name}")],
            [InlineKeyboardButton(text="💰 Записать еще трату", callback_data="add_payment")],
            [InlineKeyboardButton(text="📋 Мои группы", callback_data="show_groups")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await msg.answer(
            f"✅ <b>Трата записана!</b>\n\n"
            f"В группе <b>«{group_name}»</b> записана трата:\n"
            f"• Кто платил: <b>@{payer}</b>\n"
            f"• Сумма: <b>{amount_float} руб.</b>\n\n"
            f"Балансы обновлены!",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Сбрасываем состояние
        await state.clear()
        
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
        elif "Участник не в группе" in str(e):
            error_message = f"Участник <b>@{payer}</b> не состоит в группе <b>«{group_name}»</b>"
            # Добавляем кнопку для добавления участника
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👥 Добавить участника", callback_data="add_member")],
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=f"payment_to_group_{group_name}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
        
        await msg.answer(
            f"❌ <b>Ошибка при записи траты</b>\n\n"
            f"{error_message}.\n"
            f"Попробуйте еще раз в формате: <i>кто_платил, сумма</i>\n"
            f"Например: <i>@alice, 1000</i>",
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
                # Группируем балансы по участникам
                user_balances = {}
                for balance in non_zero_balances:
                    user = balance[0]
                    amount = balance[2]
                    if user not in user_balances:
                        user_balances[user] = 0
                    user_balances[user] += amount
                
                # Формируем текст с балансами
                balances_text = "\n".join([f"• {user} => {amount:.2f} руб." for user, amount in user_balances.items()])
                
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
