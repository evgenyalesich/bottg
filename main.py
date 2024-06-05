import os
import telebot
import requests
from telebot import apihelper
import logging
from news import get_news, clean_article_html

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
    buttons = [
        telebot.types.KeyboardButton('Получить погоду 🌤️'),
        telebot.types.KeyboardButton('Получить курс валют 💱'),
        telebot.types.KeyboardButton('Новости дня 📰'),
        telebot.types.KeyboardButton('Заказать бот 🤖')
    ]
    keyboard.add(*buttons)
    bot.send_message(message.chat.id, "Добро пожаловать! Выберите действие:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "Новости дня 📰")
def handle_news_request(message):
    links_titles_images = get_news()
    if links_titles_images:
        send_news_batch(message, links_titles_images, 0)
    else:
        bot.send_message(message.chat.id, "Извините, новости не найдены.")

def send_news_batch(message, links_titles_images, start_index):
    news_batch = links_titles_images[start_index:start_index + 10]
    for i, (title, link, img_src) in enumerate(news_batch, start=1):
        markup = telebot.types.InlineKeyboardMarkup()
        read_button = telebot.types.InlineKeyboardButton("Читать статью", callback_data=f"link_{link}")
        markup.add(read_button)

        if img_src:
            bot.send_photo(message.chat.id, img_src, caption=f"*{start_index + i}. {title}*", parse_mode='Markdown',
                           reply_markup=markup)
        else:
            bot.send_message(message.chat.id, f"*{start_index + i}. {title}*", parse_mode='Markdown',
                             reply_markup=markup)

    if start_index + 10 < len(links_titles_images):
        keyboard = telebot.types.InlineKeyboardMarkup()
        next_button = telebot.types.InlineKeyboardButton("Следующие 10 новостей",
                                                         callback_data=f"next_{start_index + 10}")
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
    proxy_url = apihelper.proxy.get('https') or apihelper.proxy.get('http')
    response = requests.get(link, proxies={"http": proxy_url, "https": proxy_url})
    if response.status_code == 200:
        article_text, media_urls = clean_article_html(response.text)

        max_message_length = 4096
        for i in range(0, len(article_text), max_message_length):
            bot.send_message(call.message.chat.id, article_text[i:i + max_message_length], parse_mode='Markdown')

        logger.debug("Sending media URLs: {}", media_urls)
        for media_type, media_url in media_urls:
            if media_type == 'photo':
                bot.send_photo(call.message.chat.id, media_url)
            elif media_type == 'video':
                bot.send_message(call.message.chat.id, f"Смотреть видео: {media_url}")
    else:
        bot.send_message(call.message.chat.id, "Не удалось загрузить статью.")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    bot.send_message(message.chat.id, "Я не понимаю вашу команду. Пожалуйста, используйте кнопки меню.")

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callback_queries(call):
    bot.send_message(call.message.chat.id, "Неизвестный запрос.")

if __name__ == "__main__":
    bot.polling(none_stop=True)
