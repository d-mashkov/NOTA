"""Память диалога — хранит историю сообщений по chat_id."""

MAX_MESSAGES = 20

_histories: dict = {}


def get_history(chat_id: int) -> list:
    return _histories.get(chat_id, [])


def add_message(chat_id: int, role: str, content: str):
    if chat_id not in _histories:
        _histories[chat_id] = []
    _histories[chat_id].append({"role": role, "content": content})
    # Оставляем только последние MAX_MESSAGES
    if len(_histories[chat_id]) > MAX_MESSAGES:
        _histories[chat_id] = _histories[chat_id][-MAX_MESSAGES:]


def clear_history(chat_id: int):
    _histories[chat_id] = []
