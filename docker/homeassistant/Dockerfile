FROM ghcr.io/home-assistant/home-assistant:stable

# Install unzip/wget if needed (HA image usually has them or curl)
RUN apk add --no-cache unzip wget

WORKDIR /tmp

# Install HACS
RUN wget https://github.com/hacs/integration/releases/latest/download/hacs.zip -O hacs.zip && \
    mkdir -p /tmp/custom_components/hacs && \
    unzip hacs.zip -d /tmp/custom_components/hacs && \
    rm hacs.zip

# HACS will be copied to /config at runtime if missing
ENTRYPOINT ["/bin/bash", "-c", "if [ ! -d /config/custom_components/hacs ]; then mkdir -p /config/custom_components/hacs && cp -r /tmp/custom_components/hacs/* /config/custom_components/hacs/; fi && exec /init"]
