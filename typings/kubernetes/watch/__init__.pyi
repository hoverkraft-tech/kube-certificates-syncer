from collections.abc import Callable, Iterator
from typing import Any

# kubernetes-stubs omits Watch; describe the public API used by this application.
class Watch:
    def stream(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Iterator[dict[str, Any]]: ...
