# kube-certificates-syncer

A kubernetes aware daemon that is listening for events on the secrets in the same namesapce and dump them as files with an optional remapping

Mainly used to discover all cert-manager generated secrets and dump them in a `/certs` dir for HAproxy with hot reload

## usage

- Deploy something similar than in `tests/manifests`
- Create some secrets
- Check what is in `/certs`
