from bs4 import BeautifulSoup
from loguru import logger
import requests
import os
import time

class ProxyHandler:
    def get_proxy(self):
        proxy_ip = os.getenv("PROXY_IP")
        proxy_port = os.getenv("PROXY_PORT")
        proxy_username = os.getenv("PROXY_USERNAME")
        proxy_password = os.getenv("PROXY_PASSWORD")

        if proxy_ip and proxy_port:
            if proxy_username and proxy_password:
                return f"http://{proxy_username}:{proxy_password}@{proxy_ip}:{proxy_port}"
            else:
                return f"http://{proxy_ip}:{proxy_port}"
        else:
            return None

class ProxyRequest:
    def __init__(self):
        self.proxy_handler = ProxyHandler()

    def make_request(self, url):
        proxy_url = self.proxy_handler.get_proxy()
        if proxy_url:
            try:
                response = requests.get(url, proxies={"http": proxy_url, "https": proxy_url}, timeout=10)
                response.raise_for_status()  # Raise an exception for bad status codes
                return response.text
            except Exception as e:
                logger.error("Exception: {}", e)
                return None
        else:
            logger.error("No proxy available. Skipping request.")
            return None

def slice_filter(html, start_pattern, end_pattern):
    """
    Filter out content between the start_pattern and end_pattern using slices.
    """
    start_idx = html.find(start_pattern)
    end_idx = html.find(end_pattern, start_idx)
    if start_idx != -1 and end_idx != -1:
        return html[:start_idx] + html[end_idx + len(end_pattern):]
    return html

def clean_article_html(html):
    # Use slicing to remove unwanted sections before parsing with BeautifulSoup
    html = slice_filter(html, '<div id="donate-article">', '</div>')
    html = slice_filter(html, '<div id="article-comment-btns">', '</div>')
    html = slice_filter(html, '<div class="article-subscription">', '</div>')

    soup = BeautifulSoup(html, 'html.parser')


    selectors_to_remove = [
        "div.social", "div.subscribe", "div.comments", "div.account",
        "a[href*='facebook.com']", "a[href*='youtube.com']", "a[href*='x.com']",
        "a[href*='vk.com']", "a[href*='ok.ru']", "a[href*='instagram.com']",
        "a[href*='rss']", "a[href*='t.me']", "footer"
    ]

    for selector in selectors_to_remove:
        elements = soup.select(selector)
        for element in elements:
            element.decompose()


    unwanted_texts = [
        "PATREON Поддержите сайт  «Хартия-97»", "Написать комментарий",
        "Также следите за аккаунтами Charter97.org в социальных сетях",
        "Facebook", "YouTube", "X.com", "vkontakte", "ok.ru", "Instagram",
        "RSS", "Telegram"
    ]

    for text in unwanted_texts:
        elements = soup.find_all(string=lambda t: text in t)
        for element in elements:
            element.extract()

    # Remove time elements
    for time_tag in soup.find_all('time'):
        time_tag.decompose()

    # Replace domain name occurrences
    for element in soup.find_all(string=True):
        if "charter97.org" in element:
            element.replace_with(element.replace("charter97.org", "news"))


    article_content = ""
    for paragraph in soup.find_all('p'):
        if ':' not in paragraph.get_text():
            article_content += paragraph.get_text() + "\n"

    return article_content.strip()

def parse_html(html):
    base_url = "https://charter97.org"
    soup = BeautifulSoup(html, 'html.parser')

    news_items = soup.find_all(class_='news news_latest')

    links_titles_images = []

    for item in news_items:
        li_elements = item.find_all('li')
        for li in li_elements:
            if 'google_ad' in li.get('class', []):
                continue

            a_tag = li.find('a')
            img_tag = li.find('img', class_='news__pic')

            if img_tag:
                li['class'] = li.get('class', []) + ['news__pic']

            img_src = img_tag['src'] if img_tag else None

            time_tag = li.find('span', class_='news__time')
            if time_tag:
                time_tag.decompose()

            if a_tag:
                full_link = base_url + a_tag['href']
                title = a_tag.get_text(strip=True)

                # Remove time from title
                if title.endswith('00:00'):
                    title = title[:-6].strip()

                links_titles_images.append((title, full_link, img_src))

    return links_titles_images

def format_telegram_link(title, link):
    return f"<a href='{link}'>{title}</a>"

@logger.catch
def main():
    url = 'https://charter97.org/ru/news/p/1/'
    proxy_request = ProxyRequest()

    while True:
        response = proxy_request.make_request(url)
        if response:
            links_titles_images = parse_html(response)
            if links_titles_images:
                for i in range(0, len(links_titles_images), 10):
                    for j, (title, link, img_src) in enumerate(links_titles_images[i:i+10], 1):
                        telegram_link = format_telegram_link(title, link)
                        print(f"{i+j}. {telegram_link}")
                        if img_src:
                            print(f"Image: {img_src}\n")

                    choice = input("Enter the number of the news you want to read (or 'q' to quit): ")
                    if choice.lower() == 'q':
                        break
                    try:
                        choice_index = int(choice) - 1
                        if 0 <= choice_index < len(links_titles_images):
                            selected_title, selected_link, _ = links_titles_images[choice_index]
                            article_html = proxy_request.make_request(selected_link)
                            if article_html:
                                cleaned_article = clean_article_html(article_html)
                                print(f"Title: {selected_title}\nCleaned Article:\n{cleaned_article}\n")
                    except ValueError:
                        print("Invalid input. Please enter a number.")


        time.sleep(3600)

if __name__ == "__main__":
    main()
