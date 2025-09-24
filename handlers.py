from __future__ import annotations

from aiogram import types, F, Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command, BaseFilter

from storage import Storage
import re


router = Router()
storage = Storage()


@router.message(Command("start"))
async def start_handler(msg: Message):
    await msg.answer("Привет! Я помогу вам записывать все траты")


@router.message(Command("help"))
async def help_handler(msg: Message):
    await msg.answer("Привет! Я помогу вам записывать все траты. Вот мои команды:\n" +
                     "/create \"group_name\" - создать новую платежную группу в этом чате \n" +
                     "/show - вывести список всех групп в этом чате \n" +
                     "/show \"group_name\" - вывести балансы участников группы \n" +
                     "/add \"GroupName\" \"@UserName\" - добавить участника чата в группу \n" +
                     "/payment \"GroupName\" \"@UserName\" \"Value\" - занести трату")


@router.message(Command("create"))
async def create_handler(msg: Message):
    command_string = msg.text.replace("/create", "")
    if command_string == "":
        await msg.answer("Введите название группы: /create [group_name]")
        return

    arg_list = re.findall(r"\[(.*?)\]", command_string)
    arg_list = list(filter(lambda a: a != "" and a != " ", arg_list))
    storage.insert_group(msg.chat.id, arg_list[0])
    await msg.answer("Группа " + arg_list[0] + " успешно создана")


@router.message(Command("show"))
async def create_handler(msg: Message):
    command_string = msg.text.replace("/show", "")
    if command_string == "":
        result = storage.select_group_from_chat_id(msg.chat.id)
        if len(result) == 0:
            await msg.answer("Групп не найдено")
            return

        result_string = f"\n".join(result)
        await msg.answer("Список групп: \n" + result_string, parse_mode=ParseMode.MARKDOWN)
        return

    arg_list = re.findall(r"\[(.*?)\]", command_string)
    arg_list = list(filter(lambda a: a != "" and a != " ", arg_list))
    balances = storage.get_balances_group(arg_list[0])
    balances.sort(key=lambda x:x[0])
    balances_string = '\n'.join(map(str, balances))
    await msg.answer("Балансы " + arg_list[0] + ":\n" + balances_string)


@router.message(Command("add"))
async def add_handler(msg: Message):
    command_string = msg.text.replace("/add", "")
    if command_string == "":
        await msg.answer("Формат комманды: /add \"GroupName\" \"@UserName\"")
        return

    arg_list = re.findall(r"\[(.*?)\]", command_string)
    arg_list = list(filter(lambda a: a != "" and a != " ", arg_list))
    storage.insert_user_in_group(msg.chat.id, arg_list[0], arg_list[1])

    await msg.answer("Юзер успешно добавлен в группу")


@router.message(Command("payment"))
async def payment_handler(msg: Message):
    command_string = msg.text.replace("/payment", "")
    if command_string == "":
        await msg.answer("Формат команды - /payment \"GroupName\" \"@UserName\" \"Value\"")
        return
    arg_list = re.findall(r"\[(.*?)\]", command_string)
    arg_list = list(filter(lambda a: a != "" and a != " ", arg_list))

    storage.change_balance(arg_list[0], arg_list[1], arg_list[2], arg_list[3])
    await msg.answer("Баланс успешно изменен")


@router.message(Command("start"))
async def message_handler(msg: Message):
    await msg.answer(f"Твой ID: {msg.from_user.id}")

