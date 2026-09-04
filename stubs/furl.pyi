import sys
from typing import type_check_only

if sys.version_info >= (3, 11):
    from typing import Self

else:
    from typing import Any

    Self = Any  # type: ignore

@type_check_only
class furl:
    url: str | None = None
    path: str | None = None
    scheme: str | None = None
    host: str | None = None
    port: str | int | None = None

    def __init__(
        self,
        url: str | None = None,
        path: str | None = None,
        scheme: str | None = None,
        host: str | None = None,
        port: str | int | None = None,
    ) -> None: ...
    def add(
        self,
        path: list[str] | str | None = None,
        framgment_path: list[str] | str | None = None,
        fragment_args: dict | None = None,
        query_params: dict | None = None,
    ) -> Self: ...
