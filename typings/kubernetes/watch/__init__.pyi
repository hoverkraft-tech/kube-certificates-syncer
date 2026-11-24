"""Describe the public Watch API omitted by kubernetes-stubs."""

from collections.abc import Callable, Iterator
from typing import Any

# This stub exposes only the streaming method used by the application.
# pylint: disable-next=too-few-public-methods
class Watch:  # noqa: E302, RUF100 - Black uses one blank line in stubs
    """The application's sole Kubernetes watch interface."""

    def stream(  # pylint: disable=unused-argument
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Iterator[dict[str, Any]]:
        """Yield Kubernetes events from the supplied list operation."""
