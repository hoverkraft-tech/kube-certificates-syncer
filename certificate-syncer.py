import os
import yaml
import logging
from kubernetes import client, config, watch

# setup logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.INFO)
logger.info('starting kube-certificates-syncer')

# Load the kube config from the default location
logger.info('Loading kubernetes client configuration from environment')
config.load_kube_config()
logger.info('Kubernetes config loaded')

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
logger.info('Will sync to target dir %s', sync_dir)

# Get the annotation filter from the configuration
annotation_filter = config_data.get('secretFilter')
logger.info('Annotations filter: %s', annotation_filter)

# Watch for changes in Secrets objects in the current namespace
logger.info('Watching secrets events')
w = watch.Watch()
for event in w.stream(v1.list_namespaced_secret):
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
    with open(os.path.join(sync_dir, key), 'w') as f:
      f.write(value)
      logger.info('%s secret written', secret.metadata.name)

logger.info('Finished')
