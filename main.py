import os
import telebot
from telebot import apihelper
import logging
import requests

from weather import process_weather_request
from news import parse_html, clean_article_html

telegram_api_token = os.getenv("TOKEN")

proxy_ip = os.getenv("PROXY_IP")
proxy_port = os.getenv("PROXY_PORT")
proxy_username = os.getenv("PROXY_USERNAME")
proxy_password = os.getenv("PROXY_PASSWORD")

if proxy_ip and proxy_port:
    if proxy_username and proxy_password:
        proxy_url = f"http://{proxy_username}:{proxy_password}@{proxy_ip}:{proxy_port}"
    else:
        proxy_url = f"http://{proxy_ip}:{proxy_port}"
    apihelper.proxy = {'https': proxy_url}

bot = telebot.TeleBot(telegram_api_token)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@bot.message_handler(commands=['start'])
def handle_start(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button_weather = telebot.types.KeyboardButton('Получить погоду 🌤️')
    button_currency = telebot.types.KeyboardButton('Получить курс валют 💱')
    button_news = telebot.types.KeyboardButton('Новости дня 📰')
    button_order_bot = telebot.types.KeyboardButton('Заказать бот 🤖')

    keyboard.add(button_weather, button_currency, button_news, button_order_bot)
    bot.send_message(message.chat.id, "Добро пожаловать! Выберите действие:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "Получить погоду 🌤️")
def handle_weather_request(message):
    bot.send_message(message.chat.id, "Введите название города:")
    bot.register_next_step_handler(message, lambda m: process_weather_request(bot, m))

@bot.message_handler(func=lambda message: message.text == "Получить курс валют 💱")
def handle_currency_request(message):
    bot.send_message(message.chat.id, "Введите код валюты (например, USD, EUR):")
    bot.register_next_step_handler(message, process_currency_request)

def process_currency_request(message):
    currency_code = message.text.upper()
    bot.send_message(message.chat.id, f"Курс {currency_code}: ...")

@bot.message_handler(func=lambda message: message.text == "Новости дня 📰")
def handle_news_request(message):
    links_titles_images = get_news()
    if links_titles_images:
        send_news_batch(message, links_titles_images, 0)
    else:
        bot.send_message(message.chat.id, "Извините, новости не найдены.")

def get_news():
    url = 'https://charter97.org/ru/news/p/1/'
    response = requests.get(url, proxies=apihelper.proxy)
    if response.status_code == 200:
        return parse_html(response.text)
    else:
        logger.error(f"Failed to retrieve news: {response.status_code}")
        return []

def send_news_batch(message, links_titles_images, start_index):
    news_batch = links_titles_images[start_index:start_index + 10]
    for i, (title, link, img_src) in enumerate(news_batch, start=1):
        bot.send_message(message.chat.id, f"{start_index + i}. <a href='{link}'>{title}</a>", parse_mode='HTML')
        if img_src:
            bot.send_photo(message.chat.id, img_src)

    if start_index + 10 < len(links_titles_images):
        keyboard = telebot.types.InlineKeyboardMarkup()
        next_button = telebot.types.InlineKeyboardButton("Следующие 10 новостей", callback_data=f"next_{start_index + 10}")
        keyboard.add(next_button)
        bot.send_message(message.chat.id, "Нажмите, чтобы увидеть следующие новости:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("next"))
def handle_next_batch(call):
    start_index = int(call.data.split("_")[1])
    links_titles_images = get_news()
    if links_titles_images:
        send_news_batch(call.message, links_titles_images, start_index)

@bot.callback_query_handler(func=lambda call: call.data.startswith("link_"))
def handle_article_request(call):
    link = call.data.split("_", 1)[1]
    response = requests.get(link, proxies=apihelper.proxy)
    if response.status_code == 200:
        cleaned_article = clean_article_html(response.text)
        bot.send_message(call.message.chat.id, cleaned_article)
    else:
        bot.send_message(call.message.chat.id, "Не удалось загрузить статью.")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    bot.send_message(message.chat.id, "Я не понимаю вашу команду. Пожалуйста, используйте кнопки меню.")

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callback_queries(call):
    bot.send_message(call.message.chat.id, "Неизвестный запрос. Пожалуйста, используйте кнопки меню.")

if __name__ == "__main__":
    bot.polling(none_stop=True)
