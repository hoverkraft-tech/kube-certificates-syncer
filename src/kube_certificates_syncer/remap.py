"""Map certificate data keys to configured output filenames."""

import logging

from kubernetes.client import V1Secret


def key(source_key: str, remap_key: str, remap_value: str, secret: V1Secret) -> str:
    """Replace a matching key and interpolate the Secret name."""
    if secret.metadata is None or secret.metadata.name is None:
        raise ValueError("secret metadata.name is required for remapping")
    logger = logging.getLogger(__name__)
    logger.debug("remapping key: secret=%s key=%s", secret.metadata.name, source_key)
    if source_key != remap_key:
        return source_key
    return remap_value.replace("{{secretName}}", secret.metadata.name)
