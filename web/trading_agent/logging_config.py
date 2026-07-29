"""Central logging setup, including a hard-to-miss banner for live trading."""

import logging
import sys

LIVE_TRADING_BANNER = """
################################################################
#  WARNING: LIVE TRADING MODE ACTIVE - REAL MONEY IS AT RISK  #
#  Orders placed by this agent will be sent to a real broker/  #
#  exchange account and may result in real financial losses.   #
################################################################
"""


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def warn_live_trading(logger: logging.Logger) -> None:
    for line in LIVE_TRADING_BANNER.strip("\n").splitlines():
        logger.warning(line)
