from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

import time


def scrape_movie_link(url):

    # Устанавливаем режим "headless" для драйвера (чтобы не открывалось окно браузера)
    chrome_options = Options()
    chrome_options.add_argument("--headless")

    # Инициализация драйвера Chrome
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Открываем страницу
        driver.get(url)

        # Ждём 5 секунд, чтобы страница прогрузилась
        time.sleep(5)

        # Находим первую ссылку
        first_link = driver.find_element(By.CSS_SELECTOR, "a.VideoCard__thumbLink.video_item__thumb_link")

        # Выводим атрибут href найденного элемента
        href_value = first_link.get_attribute('href')

        return href_value

    finally:
        # Закрываем браузер после выполнения всех действий
        driver.quit()
