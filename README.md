# kube-certificates-syncer

A Kubernetes daemon that watches Secrets in its namespace and writes matching
certificate data to files, with optional filename remapping.

Use it to copy cert-manager certificates into `/certs` for HAProxy hot reloads.

## Usage

- Adapt the [example manifests](tests/manifests) to your namespace, image and storage.
- Apply the namespace before its namespaced resources.
- Create Secrets with the annotations configured in `config.yaml`.
- Read the resulting files from the shared `/certs` volume.

The example Secrets contain synthetic data, not usable certificates. Replace them
with your own certificates when deploying. The container runs as UID/GID 10001;
its certificate volume must be writable by that user. The sample pod sets `fsGroup`
to grant access to supported Kubernetes volumes and makes the root filesystem read-only.

See the [development guide](docs/development/README.md) for local setup and checks.

See [Contributing](CONTRIBUTING.md) to develop or propose changes.
