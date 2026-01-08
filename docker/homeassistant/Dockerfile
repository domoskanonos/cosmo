FROM ghcr.io/home-assistant/home-assistant:stable

# Install unzip/wget if needed (HA image usually has them or curl)
RUN apk add --no-cache unzip wget

# Download and install Extended OpenAI Conversation
WORKDIR /tmp
# Using a fixed version or latest. Here accessing github api for latest release or hardcoding a stable one.
# For stability, let's hardcode a recent version or use specific download chain.
# Downloading v1.0.5 (example) - User can update later or we can fetch latest.
# Let's fetch the latest release zip from jkemail/extended_openai_conversation
RUN wget https://github.com/jekalmin/extended_openai_conversation/archive/refs/heads/main.zip -O extended_openai.zip && \
    unzip extended_openai.zip && \
    mkdir -p /tmp/custom_components/extended_openai_conversation && \
    cp -r extended_openai_conversation-main/custom_components/extended_openai_conversation/* /tmp/custom_components/extended_openai_conversation/ && \
    rm -rf extended_openai_conversation-main extended_openai.zip

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
