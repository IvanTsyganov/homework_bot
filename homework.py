# standard
import sys
import time
import os
import logging
from http import HTTPStatus
# local
import telegram
import requests
from dotenv import load_dotenv


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка валидности токенов."""
    return all((TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID))


class SendingMessageError(Exception):
    """Специальная ошибка отправки сообщения."""

    pass


def send_message(bot, message):
    """Отправка соощения в чат telegram."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка отправки сообщения {error}')
        raise SendingMessageError(f'Ошибка отправки сообщения {error}')
    else:
        logging.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Делает запрос к API Практикум Домашка."""
    if timestamp is None:
        timestamp = int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, params=params, headers=HEADERS)
        logging.debug('Отправка запроса к эндпоинту API-сервиса')
        if response.status_code != HTTPStatus.OK:
            logging.error('Статус запроса не 200')
            raise requests.exceptions.HTTPError('Статус запроса не 200')
        else:
            logging.info('Запрос к API. Статус 200')
            return response.json()
    except requests.exceptions.RequestException as error:
        message = 'Ошибка при запросе к основному API'
        logging.error(message)
        raise Exception(error)


def check_response(response):
    """Проверка содержания запроса API."""
    try:
        homeworks = response['homeworks']
    except KeyError as error:
        logging.error(f'Ошибка доступа по ключу homeworks: {error}')
    if not isinstance(homeworks, list):
        logging.error('Ответ в некорректном формате (homeworks не список)')
        raise TypeError('Ответ API в некорректном формате')
    elif not isinstance(response, dict):
        logging.error('Ответ API в некорректном формате (не словарь)')
        raise TypeError('Ответ API в некорректном формате')
    return homeworks


def parse_status(homework):
    """Получение статуса домашки."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе отсутствует информация о домашке')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise NameError('Неизвестный статус работы {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}".{verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует обязательная переменная окружения.')
        sys.exit(1)
    else:
        logging.info('Старт')
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        timestamp = int(time.time())
        while True:
            try:
                all_homeworks = get_api_answer(timestamp)
                logging.info('Получен ответ от API')
                homeworks = check_response(all_homeworks)
                if len(homeworks) > 0:
                    homework_status = parse_status(homeworks[0])
                    send_message(bot, homework_status)
                    logging.info('Сообщение отправлено')
                else:
                    logging.debug('Пока ничего')
                time.sleep(RETRY_PERIOD)
            except Exception as error:
                logging.error(f'Сбой в работе программы: {error}')
            finally:
                time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,
        filename='program.log',
        filemode='w',
    )
    main()
