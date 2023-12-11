import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import psycopg2
from datetime import datetime, timedelta

from config import host, port, db_name, user, password, api_token

logging.basicConfig(level=logging.INFO)

bot = Bot(token=api_token)
dp = Dispatcher(bot)

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


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer("Привет! Я бот. Добро пожаловать!")

    user_id = message.chat.id

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

    except psycopg2.Error:
        await message.answer("Что-то пошло не так")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)