# Agent instructions

Follow the [Hoverkraft organization guidance](https://github.com/hoverkraft-tech/.github/blob/main/AGENTS.md).

Read the [development guide](docs/development/README.md) before changing code or CI.
Use the commands in `Makefile`; `make ci` validates without rewriting tracked files.
Keep the application checks and the shared repository linter passing. Fix findings
instead of adding broad exclusions. Preserve the existing deployment and release contracts.
