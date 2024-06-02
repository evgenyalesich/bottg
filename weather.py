import os
import requests
import logging
import telebot

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class WeatherForecast:
    def __init__(self):
        self.api_key = os.getenv('WEATHER_API')
        self.proxy_ip = os.getenv('PROXY_IP')
        self.proxy_port = os.getenv('PROXY_PORT')
        self.proxy_username = os.getenv('PROXY_USERNAME')
        self.proxy_password = os.getenv('PROXY_PASSWORD')

    def get_weather(self, city):
        if not self.api_key:
            logger.error("Отсутствует API ключ OpenWeatherMap. Установите переменную окружения WEATHER_API.")
            return 'Отсутствует API ключ OpenWeatherMap. Установите переменную окружения WEATHER_API.', None

        url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric'
        proxies = {
            'http': f'http://{self.proxy_username}:{self.proxy_password}@{self.proxy_ip}:{self.proxy_port}',
            'https': f'http://{self.proxy_username}:{self.proxy_password}@{self.proxy_ip}:{self.proxy_port}'
        }

        try:
            response = requests.get(url, proxies=proxies)
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Response Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Response Data: {data}")

                weather_description = data['weather'][0]['description']
                icon = data['weather'][0]['icon']
                temperature = data['main']['temp']
                humidity = data['main']['humidity']
                wind_speed = data.get("wind", {}).get("speed", "Нет данных")

                icon_url = f"http://openweathermap.org/img/wn/{icon}.png"
                icon_data = requests.get(icon_url, proxies=proxies).content

                output = (
                    f"Погода в городе {city}:\n"
                    f"Описание: {weather_description}\n"
                    f"Температура: {temperature} °C\n"
                    f"Влажность: {humidity}%\n"
                    f"Скорость ветра: {wind_speed} м/с"
                )
                return output, icon_data
            else:
                logger.error(f"Failed to get weather data: {response.text}")
                return 'Не удалось получить данные о погоде.', None
        except Exception as e:
            logger.error(f"An error occurred while fetching weather data: {str(e)}")
            return 'Произошла ошибка при получении данных о погоде.', None


def process_weather_request(bot, message):
    city = message.text
    weather_forecast = WeatherForecast()
    weather_data, icon_data = weather_forecast.get_weather(city)

    if weather_data:
        bot.send_message(message.chat.id, weather_data)
    else:
        bot.send_message(message.chat.id, "Не удалось получить данные о погоде.")

    if icon_data:
        try:
            bot.send_photo(message.chat.id, icon_data)
        except telebot.apihelper.ApiTelegramException as e:
            logger.error(f"Error sending photo: {e}")
            bot.send_message(message.chat.id, "Произошла ошибка при отправке изображения.")

