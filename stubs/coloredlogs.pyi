from io import TextIOWrapper
from logging import Logger
from typing import Any

def install(
    level: str | int | None = None,
    logger: Logger | None = None,
    fmt: str | None = None,
    datefmt: str | None = None,
    style: str | None = None,
    millisecond: bool = False,
    level_styles: dict | None = None,
    field_styles: dict | None = None,
    stream: TextIOWrapper | None = None,
    isatty: bool = False,
    reconfigure: bool = True,
    use_chroot: Any | None = None,
    programname: Any | None = None,
    username: Any | None = None,
    syslog: bool = True,
) -> None: ...
def set_level(level: str | int) -> None: ...
