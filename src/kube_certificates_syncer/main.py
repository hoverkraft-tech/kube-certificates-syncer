"""Watch annotated Kubernetes Secrets and synchronize their certificate files."""

import logging
import os
import sys
from base64 import b64decode
from binascii import Error as Base64Error
from collections.abc import Mapping

import yaml
from kubernetes import client
from kubernetes.config.config_exception import ConfigException
from kubernetes.config.incluster_config import load_incluster_config
from kubernetes.config.kube_config import list_kube_config_contexts, load_kube_config
from kubernetes.watch import Watch

from kube_certificates_syncer import remap


def main() -> None:
    """Configure the Kubernetes client and process Secret events."""
    logger = configure_logging()
    logger.info("starting kube-certificates-syncer")

    # Load the configuration from the config.yaml file
    logger.info("loading config file")
    with open("config.yaml", encoding="utf-8") as stream:
        try:
            config_data = yaml.safe_load(stream)
        except yaml.YAMLError:
            logger.exception("invalid config file")
            raise
    logger.info("config file loaded")

    # Get the annotation filter from the configuration file
    annotation_filter = config_data.get("filter").get("annotations")
    logger.info("annotations filter: %s", annotation_filter)

    # Get the remap config from the configuration file
    remap_config = config_data.get("remap")
    logger.info("remap config: %s", remap_config)

    # Get the sync directory from the environment variable
    sync_dir = os.getenv("SYNCDIR")
    if sync_dir is None:
        sync_dir = "/certs"
    logger.info("syncdir: %s", sync_dir)

    # Load the kube config
    logger.info("loading kubernetes client configuration from environment")
    try:
        load_kube_config()
    except ConfigException:
        load_incluster_config()
    logger.info("kubernetes client config loaded")

    # Get the current namespace from kubeconfig or from env
    namespace = os.getenv("NAMESPACE")
    if not namespace:
        try:
            namespace = list_kube_config_contexts()[1]["context"]["namespace"]
        except (ConfigException, KeyError, TypeError):
            namespace = "default"
    logger.info("kubernetes current namespace: %s", namespace)

    # Create a client for the Kubernetes API
    v1 = client.CoreV1Api()

    # Watch for changes in Secrets objects in the current namespace
    logger.info("watching secrets events")
    w = Watch()

    # main events loop
    try:
        for event in w.stream(v1.list_namespaced_secret, namespace):
            secret: client.V1Secret = event["object"]

            # Check the type of event
            if event["type"] not in ["ADDED", "MODIFIED", "DELETED"]:
                logger.debug("got an event of type %s, skipping", event["type"])
                continue

            if secret.metadata is None or secret.metadata.name is None:
                logger.warning("secret event is missing metadata or name, skipping")
                continue

            logger.info(
                "got secret event: secret=%s type=%s",
                secret.metadata.name,
                event["type"],
            )

            sync_secret(
                event["type"], secret, annotation_filter, remap_config, sync_dir
            )

    except KeyboardInterrupt:
        logger.info("Finished")
        sys.exit(0)


def configure_logging() -> logging.Logger:
    """Apply the configured log level and timestamp format."""
    logger = logging.getLogger()
    loglevel = os.environ.get("LOGLEVEL", "INFO").upper()
    logger.setLevel(loglevel)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger = logging.getLogger("kube-certificate-syncer.remap")
    return logger


def sync_secret(
    event_type: str,
    secret: client.V1Secret,
    annotation_filter: Mapping[str, str],
    remap_config: list[dict[str, str]] | None,
    sync_dir: str,
) -> None:
    """Filter a Secret and synchronize each of its optionally remapped keys."""
    if secret.metadata is None or secret.metadata.name is None:
        return
    logger = logging.getLogger(__name__)
    annotations = secret.metadata.annotations or {}
    if not all(
        annotations.get(name) == value for name, value in annotation_filter.items()
    ):
        logger.info(
            "secret %s does not match the filters, skipping",
            secret.metadata.name,
        )
        return

    for key, value in (secret.data or {}).items():
        # Remap the fields of the secrets if specified in the configuration
        if remap_config:
            logger.info(
                "remapping secret key names for secret %s", secret.metadata.name
            )
            for item in remap_config:
                _kname = item["name"]
                _kvalue = item["value"]
                key = remap.key(key, _kname, _kvalue, secret)
                logger.debug("remapped key=%s", key)

        sync_file(event_type, secret.metadata.name, key, value, sync_dir)


def sync_file(
    event_type: str, secret_name: str, key: str, value: str, sync_dir: str
) -> None:
    """Apply a single Secret key while keeping decode and filesystem failures local."""
    logger = logging.getLogger(__name__)
    # persist secrets
    filename = os.path.join(sync_dir, key)

    # handle the simple case of delete
    if event_type == "DELETED":
        try:
            os.remove(filename)
            logger.info("deleted secret %s at %s", secret_name, filename)
        except OSError:
            logger.exception(
                "cannot delete secret %s at %s",
                secret_name,
                filename,
            )
        return

    # decode the certificate
    try:
        decoded = b64decode(value, validate=True).decode("utf-8")
        logger.info(
            "secret=%s key=%s written to %s",
            secret_name,
            key,
            filename,
        )
    except (UnicodeDecodeError, Base64Error):
        logger.warning(
            "secret=%s key=%s can't be decoded as base64",
            secret_name,
            key,
        )
        logger.warning("skipping secret=%s key=%s", secret_name, key)
        return

    # Write the secret data to a file in the sync directory
    try:
        with open(filename, "w", encoding="utf-8") as output:
            output.write(decoded)
        logger.info(
            "secret=%s key=%s written to %s",
            secret_name,
            key,
            filename,
        )
    except OSError:
        logger.exception("secret=%s key=%s cannot be synced", secret_name, key)


if __name__ == "__main__":
    main()
