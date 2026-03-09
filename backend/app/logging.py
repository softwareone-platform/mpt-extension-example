from typing import ClassVar

import rich
from rich.highlighter import ReprHighlighter as _ReprHighlighter
from rich.logging import RichHandler as _RichHandler
from rich.theme import Theme


class ReprHighlighter(_ReprHighlighter):
    """Highlighter for MPT IDs."""

    accounts_prefixes = ("ACC", "BUY", "LCE", "MOD", "SEL", "USR", "AUSR", "UGR")
    catalog_prefixes = (
        "PRD",
        "ITM",
        "IGR",
        "PGR",
        "MED",
        "DOC",
        "TCS",
        "TPL",
        "WHO",
        "PRC",
        "LST",
        "AUT",
        "UNT",
    )
    commerce_prefixes = ("AGR", "ORD", "SUB", "REQ")
    aux_prefixes = ("FIL", "MSG")
    extensions_prefixes = ("EXT", "EXI")
    all_prefixes = (
        *accounts_prefixes,
        *catalog_prefixes,
        *commerce_prefixes,
        *aux_prefixes,
        *extensions_prefixes,
    )

    prefixes_pattern = "|".join(all_prefixes)
    pattern = rf"(?P<mpt_id>(?:{prefixes_pattern})(?:-\d{{4}})*)"
    highlights: ClassVar[list[str]] = [
        *_ReprHighlighter.highlights,
        pattern,
    ]


class RichHandler(_RichHandler):
    """Rich handler for logging with color support."""

    HIGHLIGHTER_CLASS = ReprHighlighter


rich.reconfigure(theme=Theme({"repr.mpt_id": "bold light_salmon3"}))



def get_logging_config(log_level: str = "INFO", logging_handler: str = "rich") -> dict:
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{asctime} {name} {levelname} (pid: {process}) {message}",
                "style": "{",
            },
            "rich": {
                "format": "{name} {message}",
                "style": "{",
            },
            "plain": {"format": "%(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "stream": "ext://sys.stderr",
            },
            "rich": {
                "class": "app.logging.RichHandler",
                "level": log_level,
                "formatter": "rich",
                "log_time_format": "%Y-%m-%d %H:%M:%S",
                "rich_tracebacks": True,
            },
        },
        "root": {
            "handlers": [logging_handler],
            "level": "WARNING",
            "propagate": False,
        },
        "loggers": {
            "app": {
                "handlers": [logging_handler],
                "level": log_level,
                "propagate": False,
            },
            "mrok": {
                "handlers": [logging_handler],
                "level": log_level,
                "propagate": False,
            }
        },
    }

    return logging_config
