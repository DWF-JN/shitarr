FROM ghcr.io/hotio/bazarr:latest

# Overlay our custom provider (this replaces the whole custom_libs folder with our version)
COPY custom_libs /app/custom_libs
