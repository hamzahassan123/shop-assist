import logging
import os
from contextvars import ContextVar


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | "
    "conversation_id=%(conversation_id)s | %(message)s"
)
conversation_id_context: ContextVar[str] = ContextVar(
    "conversation_id",
    default="-",
)


class ConversationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.conversation_id = conversation_id_context.get()
        return True


def configure_logging():
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
    )

    root_logger = logging.getLogger()
    if not any(isinstance(item, ConversationIdFilter) for item in root_logger.filters):
        root_logger.addFilter(ConversationIdFilter())
    for handler in root_logger.handlers:
        if not any(isinstance(item, ConversationIdFilter) for item in handler.filters):
            handler.addFilter(ConversationIdFilter())
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
