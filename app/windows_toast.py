"""Qt desktop notifications, delivered to the GUI thread through the mediator."""
from enum import Enum
from app import mediator
from module.logger import log

class TemplateToast(Enum):
    NoneTemplate=0
    TestTemplate=1
    NormalTemplate=2

def send_toast(title, msg, **kwargs):
    message = '\n'.join(msg) if isinstance(msg,list) else str(msg)
    log.info(f'{title}: {message}')
    mediator.desktop_notification.emit(title, message)
    return True
