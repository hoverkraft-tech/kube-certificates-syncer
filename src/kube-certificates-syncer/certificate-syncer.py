import logging
import os
import re
import sys
import yaml
from base64 import b64decode
from jinja2 import Template
from kubernetes import client, config, watch
from remap import remap_key

# setup logger
logger = logging.getLogger('k8s-cert-sync')
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
annotation_filter = config_data.get('filter').get('annotations')
logger.info('Annotations filter: %s', annotation_filter)

# Watch for changes in Secrets objects in the current namespace
logger.info('Watching secrets events')
w = watch.Watch()

try:
  for event in w.stream(v1.list_namespaced_secret, namespace):
    secret = event['object']
    logger.info('Considering secret %s', secret.metadata.name)

    # loop over all the secrets in the namespace
    for key, value in secret.data.items():

      matched = False
      for f_key, f_val in annotation_filter.items():
        if secret.metadata.annotations.get(f_key) != f_val:
            logger.info('annotation mismatch: secret=%s, annotation=%s, value=%s, expected=%s', secret.metadata.name, f_key, secret.metadata.annotations.get(f_key), f_val)
            break
        else:
          logger.info('annotation match: secret=%s, annotation=%s, value=%s', secret.metadata.name, f_key, f_val)
          matched = True
          continue
      # if only one annotation does not match we should pass to the next event
      if matched == False:
        break

      # Remap the fields of the secrets if specified in the configuration
      if 'remap' in config_data:
        logger.info('remapping fields for %s', secret.metadata.name)
        for item in config_data['remap']:
          _kname = item['name']
          _kvalue = item['value']
          key = remap_key(key, _kname, _kvalue, secret)
          logger.info('New object after remaping: (%s: %s)', key, value[1:10])

      # Write the secret data to a file in the sync directory
      filename = os.path.join(sync_dir, key)
      with open(filename, 'w') as f:
        value = b64decode(value).decode('utf-8')
        f.write(value)
        logger.info('secret=%s key=%s written to %s', secret.metadata.name, key, filename)

except KeyboardInterrupt:
  logger.info('Finished')
  sys.exit(0)
