# kube-certificates-syncer

<div align="center">
  <img src=".github/logo.svg" alt="Kube Certificates Syncer logo" width="200" />
</div>

---

[![Main - Continuous Integration](https://github.com/hoverkraft-tech/kube-certificates-syncer/actions/workflows/main-ci.yml/badge.svg)](https://github.com/hoverkraft-tech/kube-certificates-syncer/actions/workflows/main-ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/hoverkraft-tech/kube-certificates-syncer)](https://github.com/hoverkraft-tech/kube-certificates-syncer/releases)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## Overview

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
Adapt the sample NetworkPolicy to your Kubernetes API and DNS endpoints.

See the [development guide](docs/development/README.md) for local setup and checks.

## Contributing

Contributions are welcome. Read [Contributing](CONTRIBUTING.md) before proposing a change.
