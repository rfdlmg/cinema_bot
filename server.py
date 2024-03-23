import logging

from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext

import psycopg2
from datetime import datetime, timedelta

from config import host, port, db_name, user, password, api_token
from scrape_movie_link import scrape_movie_link

logging.basicConfig(level=logging.INFO)

bot = Bot(token=api_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

logging.basicConfig(level=logging.INFO)
dp.middleware.setup(LoggingMiddleware())

conn = psycopg2.connect(
    host=host,
    port=port,
    dbname=db_name,
    user=user,
    password=password
)
cursor = conn.cursor()

with open('create_users_table.sql', 'r') as sql_config:
    create_table_query = sql_config.read()

cursor.execute(create_table_query)

conn.commit()


# Меню для взаимодействия с ботом
def call_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    search_film = types.InlineKeyboardButton("Найти фильм 🎥", callback_data="search_film")
    subscribe = types.InlineKeyboardButton("Оформить подписку 💳", callback_data="subscribe")
    trial_subscription = types.InlineKeyboardButton("Активировать пробную подписку 🎁", callback_data="trial_subscription")
    subscribe_info = types.InlineKeyboardButton("Моя подписка ❓", callback_data="subscribe_info")
    markup.add(search_film, subscribe, trial_subscription, subscribe_info)
    return markup


def check_type_of_video_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    film_button = types.InlineKeyboardButton("Фильм 🍿", callback_data="film")
    soap_opera_button = types.InlineKeyboardButton("Сериал 🎬", callback_data="soap_opera")
    markup.add(film_button, soap_opera_button)
    return markup


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message, state: FSMContext):
    keyboard = call_menu()
    await message.reply("Доброго времени суток!🍿 Вы попали в онлайн-кинотеатр, работающий через телеграм-бота 🎥 \n"
                        "Выберите нужную функцию: ", reply_markup=keyboard)

    user_id = message.chat.id

    # Запись текущего шага пользователя во временное хранилище
    async with state.proxy() as data:
        data['current_step'] = 1

    with open("insert_user_query.sql", "r") as file:
        insert_query = file.read()

    try:
        cursor.execute(insert_query, (user_id,))
        conn.commit()

    except psycopg2.Error:
        conn.rollback()
        await message.answer("Что-то пошло не так")


@dp.message_handler(commands=['subscribe'])
async def subscribe_command(message: types.Message):
    user_id = message.chat.id
    expiration_date = datetime.now() + timedelta(days=30)

    try:
        cursor.execute('SELECT is_attempt_spent FROM users WHERE user_id = %s;', (user_id,))
        is_attempt_spent = cursor.fetchone()[0]

        if not is_attempt_spent:
            await message.answer(f"Вы активировали пробную подписку. Дата истечения: {expiration_date}")

            with open("update_subscribe_query.sql", "r") as file:
                update_query = file.read()

            try:
                cursor.execute(update_query, (user_id,))
                conn.commit()

            except psycopg2.Error:
                conn.rollback()
                await message.answer("Что-то пошло не так")
        else:
            await message.answer(f"Вы уже пользовались бесплатной подпиской")

    except psycopg2.Error:
        await message.answer("Что-то пошло не так")


# Функция для вызова функционала кнопок меню
@dp.callback_query_handler(lambda callback_query: True)
async def callback(call, state: FSMContext):
    user_id = call.message.chat.id

    # Удаление предыдущего сообщения от бота
    await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)

    # Проверка данных нажатой кнопки в меню и реализация её функционала
    if call.data == "search_film":
        cursor.execute('SELECT subscribe FROM users WHERE user_id = %s;', (user_id,))
        subscribe_date = cursor.fetchone()[0]

        # Проверка на актуальность подписки
        if subscribe_date:
            current_date = datetime.now()
            difference = current_date - subscribe_date

            if difference.days > 30:
                await bot.send_message(call.message.chat.id, "Срок Вашей подписки истёк. Оформить новую: /subscribe")
            else:
                await bot.send_message(call.message.chat.id, "Введите название фильма/сериала: ")

                # Запись текущего шага пользователя во временное хранилище
                async with state.proxy() as data:
                    data['current_step'] = 2
        else:
            await bot.send_message(call.message.chat.id, "Активируйте пробную подписку на 30 дней: /subscribe")

    elif call.data == "film":
        await bot.send_message(call.message.chat.id, "Бот ищет фильм...🤖")

        async with state.proxy() as data:
            data['current_step'] = 1
            film_name = str(data["film_name"])
            movie_link = scrape_movie_link(f"https://vk.com/video?q={film_name}&ysclid=lt39nq9jf8631020539")

            await bot.send_message(call.message.chat.id, movie_link)

    elif call.data == "soap_opera":
        await bot.send_message(call.message.chat.id, "Введите номер сезона:")

        async with state.proxy() as data:
            data['current_step'] = 3

    elif call.data == "subscribe":
        await bot.send_message(call.message.chat.id, "Функция в разработке")

    elif call.data == "trial_subscription":
        user_id = call.message.chat.id

        try:
            cursor.execute('SELECT is_attempt_spent FROM users WHERE user_id = %s;', (user_id,))
            is_attempt_spent = cursor.fetchone()[0]

            if not is_attempt_spent:
                expiration_date = datetime.now() + timedelta(days=30)

                # Форматирование даты expiration_date в формат дд.мм.гггг
                formatted_date = expiration_date.strftime('%d.%m.%Y')

                await call.message.answer(f"Вы активировали пробную подписку. Дата истечения: {formatted_date}")

                with open("update_subscribe_query.sql", "r") as file:
                    update_query = file.read()

                try:
                    cursor.execute(update_query, (user_id,))
                    conn.commit()

                except psycopg2.Error:
                    conn.rollback()
                    await call.message.answer("Что-то пошло не так")
            else:
                await call.message.answer(f"Вы уже пользовались бесплатной подпиской")

        except psycopg2.Error:
            await call.message.answer("Что-то пошло не так")
    elif call.data == "subscribe_info":
        cursor.execute('SELECT subscribe FROM users WHERE user_id = %s;', (user_id,))
        subscribe_date = cursor.fetchone()[0]

        # Проверка на актуальность подписки
        if subscribe_date:
            current_date = datetime.now()
            difference = current_date - subscribe_date

            if difference.days > 30:
                await bot.send_message(call.message.chat.id, "Срок Вашей подписки истёк. Оформить новую: /subscribe")
            else:
                expiration_date = subscribe_date + timedelta(days=30)

                # Форматирование даты expiration_date в формат дд.мм.гггг
                formatted_date = expiration_date.strftime('%d.%m.%Y')

                await bot.send_message(call.message.chat.id, f"Ваша подписка действительна до: {formatted_date}")

        else:
            await bot.send_message(call.message.chat.id, "Активируйте пробную подписку на 30 дней: /subscribe")


# Функция для обработки введённого текста
@dp.message_handler(lambda message: message.text)
async def handle_text(message: types.Message, state: FSMContext):
    user_id = message.chat.id

    input_data = message.text

    # Достаём данные из временного хранилища
    async with state.proxy() as data:
        if data['current_step'] == 2:
            data['film_name'] = input_data

            keyboard = check_type_of_video_menu()
            await message.reply("Это фильм или сериал?", reply_markup=keyboard)

        elif data['current_step'] == 3:
            try:
                float(input_data)

                data['season'] = input_data
                data['current_step'] = 4

                await message.reply("Введите номер серии: ")

            except ValueError:
                await message.reply("Введите номер серии в числовом формате")

        elif data['current_step'] == 4:
            try:
                float(input_data)

                data['series'] = input_data
                data['current_step'] = 1

                await message.reply("Бот ищет серию... 🤖")

                film_name = str(data["film_name"])
                season = str(data["season"])
                series = str(data["series"])
                movie_link = scrape_movie_link(f"https://vk.com/video?q={film_name}%20{season}%20сезон%20{series}%20серия&ysclid=lt39nq9jf8631020539")

                await bot.send_message(message.chat.id, movie_link)

            except ValueError:
                await message.reply("Введите номер серии в числовом формате")
        else:
            await message.reply("Сначала выберите функцию в меню бота")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)