import re
import string
import logging

def remap_key(key: string, remapKey: string, remapValue: string, secret: object):
  logger = logging.getLogger('k8s-cert-sync')
  logger.info('remapping key %s with %s: %s', key, remapKey, remapValue)

  if key != remapKey:
    return key
  else:
    _value = re.sub(r"{{secretName}}", secret.metadata.name, remapValue)

  # return the new value
  return _value
