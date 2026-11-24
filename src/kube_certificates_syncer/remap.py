import logging

from kubernetes.client import V1Secret


def key(key: str, remap_key: str, remap_value: str, secret: V1Secret) -> str:
    if secret.metadata is None or secret.metadata.name is None:
        raise ValueError("secret metadata.name is required for remapping")
    logger = logging.getLogger(__name__)
    logger.debug("remapping key: secret=%s key=%s", secret.metadata.name, key)
    if key != remap_key:
        return key
    return remap_value.replace("{{secretName}}", secret.metadata.name)
