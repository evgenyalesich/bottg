from googlesearch import search
import requests
from bs4 import BeautifulSoup

def get_exchange_rate(currency, city):
    query = f"курс {currency} в {city}"
    search_results = search(query, num=1, stop=1, pause=2)
    if search_results:
        url = search_results[0]
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            exchange_rate = soup.find('div', class_='exchange-rate').text
            return exchange_rate
        else:
            print("Ошибка при получении данных о курсе валют")
    else:
        print("Результаты поиска не найдены")

def get_currency(message):
    try:
        city = message.text.split()[1]
        currency = 'USD'  # Вы можете изменить валюту по своему усмотрению
        exchange_rate = get_exchange_rate(currency, city)
        if exchange_rate:
            bot.send_message(message.chat.id, f"Курс {currency} в городе {city}: {exchange_rate}")
        else:
            bot.send_message(message.chat.id, f"Не удалось получить курс для {currency} в городе {city}.")
    except IndexError:
        bot.send_message(message.chat.id, "Пожалуйста, укажите город после команды /курс")
