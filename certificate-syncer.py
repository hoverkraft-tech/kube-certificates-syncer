import os
import yaml
import logging
import sys
import base64
import re
from kubernetes import client, config, watch

# setup logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.INFO)
logger.info('starting kube-certificates-syncer')

# Load the kube config
logger.info('Loading kubernetes client configuration from environment')
try:
  config.load_kube_config()
except Exception as e:
  config.load_incluster_config()

# get the current namespace
try:
  namespace = config.list_kube_config_contexts()[1]['context']['namespace']
except:
  namespace = "default"

logger.info('Kubernetes config loaded')
logger.info('Kubernetes current namespace: %s', namespace)

# Create a client for the Kubernetes API
v1 = client.CoreV1Api()

# Load the configuration from the config.yaml file
logger.info('Loading config file')
with open("config.yaml", 'r') as stream:
  try:
    config_data = yaml.safe_load(stream)
  except yaml.YAMLError as exc:
    print(exc)
logger.info('Config file loaded')

# Get the sync directory from the environment variable
sync_dir = os.getenv('SYNCDIR')
if sync_dir == None:
  sync_dir = "/certs"
logger.info('Will sync to target dir %s', sync_dir)

# Get the annotation filter from the configuration
annotation_filter = config_data.get('secretFilter')
logger.info('Annotations filter: %s', annotation_filter)

# Watch for changes in Secrets objects in the current namespace
logger.info('Watching secrets events')
w = watch.Watch()
for event in w.stream(v1.list_namespaced_secret, namespace='default'):
  secret = event['object']
  logger.info('Considering secret %s', secret.metadata.name)

  # Check if the secret has the required annotations
  for key, value in annotation_filter.items():
    if secret.metadata.annotations.get(key) != value:
      logger.info('Annotations filter does not match for secret %s, skipping it.', secret.metadata.name)
      continue
  logger.info('Annotations filter does match for secret %s, syncing it.', secret.metadata.name)

  # Download all the secrets in the sync directory
  for key, value in secret.data.items():
    # Remap the fields of the secrets if specified in the configuration
    if 'remap' in config_data and key in config_data['remap']:
      logger.info('remapping fields for %s', secret.metadata.name)
      key = config_data['remap'][key]

    # Write the secret data to a file in the sync directory
    filename = re.sub(r"^tls\.", secret.metadata.name + '.', key)
    with open(os.path.join(sync_dir, filename), 'w') as f:
      f.write(value)
      logger.info('%s secret written to %s/%s', secret.metadata.name, sync_dir, filename)

logger.info('Finished')
