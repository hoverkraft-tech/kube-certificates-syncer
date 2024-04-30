import os
import yaml
from kubernetes import client, config, watch

# Load the kube config from the default location
config.load_kube_config()

# Create a client for the Kubernetes API
v1 = client.CoreV1Api()

# Load the configuration from the config.yaml file
with open("config.yaml", 'r') as stream:
  try:
    config_data = yaml.safe_load(stream)
  except yaml.YAMLError as exc:
    print(exc)

# Get the sync directory from the environment variable
sync_dir = os.getenv('SYNCDIR')

# Get the annotation filter from the configuration
annotation_filter = config_data.get('secretFilter')

# Watch for changes in Secrets objects in the current namespace
w = watch.Watch()
for event in w.stream(v1.list_namespaced_secret):
  secret = event['object']

  # Check if the secret has the required annotations
  for key, value in annotation_filter.items():
    if secret.metadata.annotations.get(key) != value:
      continue

  # Download all the secrets in the sync directory
  for key, value in secret.data.items():
    # Remap the fields of the secrets if specified in the configuration
    if 'remap' in config_data and key in config_data['remap']:
      key = config_data['remap'][key]

    # Write the secret data to a file in the sync directory
    with open(os.path.join(sync_dir, key), 'w') as f:
      f.write(value)
