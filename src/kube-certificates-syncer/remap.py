import sys
import os
import re
import string
import logging

def key(key: string, remapKey: string, remapValue: string, secret: object):
  logger = logging.getLogger(__name__)
  logger.debug('remapping keys: secret=%s key=%s remapKey=%s remapValue=%s', secret.metadata.name, key, remapKey, remapValue)

  if key != remapKey:
    return key
  else:
    _value = re.sub(r"{{secretName}}", secret.metadata.name, remapValue)

  # return the new value
  return _value
