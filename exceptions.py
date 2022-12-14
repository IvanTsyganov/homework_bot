class SendingMessageError(Exception):
    """Специальная ошибка отправки сообщения."""

    pass


class ApiRequestError(Exception):
    """Специальная ошибка запроса к API."""

    pass
