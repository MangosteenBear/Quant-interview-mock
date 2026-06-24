"""
统一日志模块
结构化 JSON 日志，方便长期迭代排查
"""
import json
import logging
import sys
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """JSON 格式化器，输出结构化日志"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        # 附加自定义字段
        for key in ("source_file", "page", "question_id", "stage"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(name: str = "pipeline", level: int = logging.INFO) -> logging.Logger:
    """配置并返回 logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger


# 全局 logger
logger = setup_logger()
