FROM node:22-bookworm-slim

ENV PAI_SANDBOX=True

# Disable core dumps
RUN echo "* soft core 0" >> /etc/security/limits.conf && \
    echo "* hard core 0" >> /etc/security/limits.conf

# Install minimal tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tini \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create working directories
RUN mkdir -p /workspace /skills
WORKDIR /workspace

# Copy and setup entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set default expire time (can be overridden by environment variable)
ENV EXPIRE_SECONDS=300

# Use tini as entrypoint for proper signal handling
ENTRYPOINT ["tini", "--", "/entrypoint.sh"]
