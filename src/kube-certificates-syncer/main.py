import os
import sys
import yaml
import logging
from base64 import b64decode
from kubernetes import client, config, watch
import remap

def main():
  logger = logging.getLogger()
  loglevel = os.environ.get('LOGLEVEL', 'INFO').upper()
  logger.setLevel(loglevel)
  formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
  ch = logging.StreamHandler()
  ch.setFormatter(formatter)
  logger.addHandler(ch)

  logger = logging.getLogger('kube-certificate-syncer.remap')
  logger.info('starting kube-certificates-syncer')

  # Load the configuration from the config.yaml file
  logger.info('loading config file')
  with open("config.yaml", 'r') as stream:
    try:
      config_data = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
      print(exc)
  logger.info('config file loaded')

  # Get the annotation filter from the configuration file
  annotation_filter = config_data.get('filter').get('annotations')
  logger.info('annotations filter: %s', annotation_filter)

  # Get the remap config from the configuration file
  remap_config = config_data.get('remap')
  logger.info('remap config: %s', remap_config)

  # Get the sync directory from the environment variable
  sync_dir = os.getenv('SYNCDIR')
  if sync_dir == None:
    sync_dir = "/certs"
  logger.info('syncdir: %s', sync_dir)

  # Load the kube config
  logger.info('loading kubernetes client configuration from environment')
  try:
    config.load_kube_config()
  except config.config_exception.ConfigException:
    config.load_incluster_config()
  logger.info('kubernetes client config loaded')

  # Get the current namespace from kubeconfig or from env
  namespace = os.getenv('NAMESPACE')
  if not namespace:
    try:
      namespace = config.list_kube_config_contexts()[1]['context']['namespace']
    except:
      namespace = 'default'
  logger.info('kubernetes current namespace: %s', namespace)

  # Create a client for the Kubernetes API
  v1 = client.CoreV1Api()

  # Watch for changes in Secrets objects in the current namespace
  logger.info('watching secrets events')
  w = watch.Watch()

  # main events loop
  try:
    for event in w.stream(v1.list_namespaced_secret, namespace):
      secret = event['object']

      # Check the type of event
      if event['type'] not in ['ADDED', 'MODIFIED', 'DELETED']:
        logger.debug("got an event of type %s, skipping", event['type'])
        continue

      logger.info('got secret event: secret=%s type=%s', secret.metadata.name, event['type'])
      # logger.debug('event: %s', event)

      # loop over all the secrets events
      for key, value in secret.data.items():
        logger.debug('inspecting secret=%s / key=%s value=%s...', secret.metadata.name, key, value[0:10])

        matched = False
        for f_key, f_val in annotation_filter.items():
          f_annotations = None
          if secret.metadata.annotations:
            f_annotations = secret.metadata.annotations.get(f_key)
          if f_annotations != f_val:
              logger.debug('annotation mismatch: secret=%s, annotation=%s, value=%s, expected=%s', secret.metadata.name, f_key, f_annotations, f_val)
              break
          else:
            logger.debug('annotation match: secret=%s, annotation=%s, value=%s', secret.metadata.name, f_key, f_val)
            matched = True
            continue
        # if only one annotation does not match we should pass to the next event
        if matched == False:
          logger.info('secret %s does not match the filters, skipping', secret.metadata.name)
          break

        # Remap the fields of the secrets if specified in the configuration
        if remap_config:
          logger.info('remapping secret key names for secret %s', secret.metadata.name)
          for item in remap_config:
            _kname = item['name']
            _kvalue = item['value']
            key = remap.key(key, _kname, _kvalue, secret)
            logger.debug('new object after remaping: key=%s: value=%s...)', key, value[0:10])

        # persist secrets
        filename = os.path.join(sync_dir, key)

        # handle the simple case of delete
        if event['type'] == 'DELETED':
          try:
            os.remove(filename)
            logging.info('deleted secret %s at %s', secret.metadata.name, filename)
          except:
            logging.error('can''t delete secret %s at %s', secret.metadata.name, filename)
          finally:
            continue

        # decode the certificate
        try:
          decoded = b64decode(value).decode('utf-8')
          logger.info('secret=%s key=%s written to %s', secret.metadata.name, key, filename)
        except UnicodeDecodeError:
          logger.warning('secret=%s key=%s can\'t be decoded as base64', secret.metadata.name, key)
          logger.warning('skipping secret=%s key=%s', secret.metadata.name, key)
          continue

        # Write the secret data to a file in the sync directory
        with open(filename, 'w') as f:
          try:
            f.write(decoded)
            logger.info('secret=%s key=%s written to %s', secret.metadata.name, key, filename)
          except e as Exception:
            logger.error('secret=%s key=%s can\'t be synced: %s', secret.metadata.name, key, e)
          finally:
            continue

  except KeyboardInterrupt:
    logger.info('Finished')
    sys.exit(0)

if __name__ == '__main__':
    main()
