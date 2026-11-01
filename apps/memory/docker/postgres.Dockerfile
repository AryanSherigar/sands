# syntax=docker/dockerfile:1
FROM postgres:18.6-bookworm

# PGDG apt package, pinned. postgres:18-bookworm already has the PGDG repo
# configured and postgresql-18 installed from it, so this satisfies the
# package's own dependency on postgresql-18 without extra repo setup.
ARG PGVECTOR_VERSION=0.8.6-1.pgdg12+2

# Timescale's BM25 extension (https://github.com/timescale/pg_textsearch).
# No PGDG apt package exists for it; installed from the project's prebuilt
# release .deb (wrapped in a .zip), pinned by version + checksum per arch.
ARG PG_TEXTSEARCH_VERSION=1.4.0
ARG PG_TEXTSEARCH_SHA256_AMD64=c2ce0585a7f09ec7fc441f1fba11888d6ad3ab51b1851d4f24a7457905d0519f
ARG PG_TEXTSEARCH_SHA256_ARM64=f65bc4f46393ca66c78e4da71ae8c54d0aef9975eaf3d5b6836d0f4570c68c64
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        unzip \
        "postgresql-18-pgvector=${PGVECTOR_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) pgts_checksum="${PG_TEXTSEARCH_SHA256_AMD64}" ;; \
        arm64) pgts_checksum="${PG_TEXTSEARCH_SHA256_ARM64}" ;; \
        *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    pgts_zip="pg-textsearch-v${PG_TEXTSEARCH_VERSION}-pg18-${TARGETARCH}.zip"; \
    pgts_url="https://github.com/timescale/pg_textsearch/releases/download/v${PG_TEXTSEARCH_VERSION}/${pgts_zip}"; \
    workdir="$(mktemp -d)"; \
    curl -fsSL -o "${workdir}/${pgts_zip}" "${pgts_url}"; \
    echo "${pgts_checksum}  ${workdir}/${pgts_zip}" | sha256sum -c -; \
    unzip -q "${workdir}/${pgts_zip}" -d "${workdir}/extracted"; \
    dpkg -i "${workdir}"/extracted/*.deb; \
    rm -rf "${workdir}"

COPY initdb/ /docker-entrypoint-initdb.d/

# pg_textsearch requires loading via shared_preload_libraries (README.md,
# "Getting Started"). pgvector needs no preload.
CMD ["postgres", "-c", "shared_preload_libraries=pg_textsearch"]
