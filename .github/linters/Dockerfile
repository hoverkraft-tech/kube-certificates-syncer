FROM ghcr.io/hoverkraft-tech/docker-base-images/super-linter:2.0.2@sha256:12dedee667b43856a9cc792628fecc4723fc0868bf8090d268981407a7402b2c

ARG UID=1000
ARG GID=1000
USER ${UID}:${GID}
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s --retries=3 CMD ["/bin/sh", "-c", "test -d /github/home"]

# Application lint uses the project-owned Go or Python tools through make lint-code.
ENV VALIDATE_JAVASCRIPT_TOOLCHAIN="" \
    VALIDATE_PYTHON_TOOLCHAIN="" \
    LOG_LEVEL=INFO \
    IGNORE_GITIGNORED_FILES=true \
    VALIDATE_BASH=true \
    VALIDATE_BASH_EXEC=true \
    VALIDATE_BIOME_FORMAT=true \
    VALIDATE_BIOME_LINT=true \
    VALIDATE_CHECKOV=true \
    VALIDATE_DOCKERFILE_HADOLINT=true \
    VALIDATE_GITHUB_ACTIONS=true \
    VALIDATE_GITHUB_ACTIONS_ZIZMOR=true \
    VALIDATE_GIT_COMMITLINT=true \
    VALIDATE_MARKDOWN=true \
    VALIDATE_MARKDOWN_PRETTIER=true \
    VALIDATE_NATURAL_LANGUAGE=true \
    VALIDATE_SHELL_SHFMT=true \
    VALIDATE_TRIVY=true \
    VALIDATE_YAML=true \
    VALIDATE_YAML_PRETTIER=true
