import logging
from time import sleep

from dakara_base.progress_bar import progress_bar

logger = logging.getLogger("examples.progress_bar")

logging.basicConfig(level=logging.INFO)

logger.info("process started")

for item in progress_bar(range(10), text="i'm gonna mikumiku you"):
    if item % 3 == 0:
        logger.warning("something happens with item %i", item)

    sleep(0.5)

for item in progress_bar(range(10), text="i'm gonna mikumiku you", term_width=70):
    if item % 3 == 0:
        logger.warning("something happens with item %i", item)

    sleep(0.5)

logger.info("process ended")
