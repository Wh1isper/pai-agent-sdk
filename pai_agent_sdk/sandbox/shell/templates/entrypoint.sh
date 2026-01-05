#!/bin/bash

# Default expire time if not set (5 minutes). If set to 0 or negative, do not auto-expire.
EXPIRE_SECONDS=${EXPIRE_SECONDS:-300}

echo "Sandbox container started"
if [ "$EXPIRE_SECONDS" -le 0 ]; then
  echo "Container will not auto-expire (EXPIRE_SECONDS=$EXPIRE_SECONDS)"
  echo "Ready for external bash commands"
  # Sleep in a loop to keep container alive; tini will handle signals properly
  while true; do
    sleep 86400
  done
else
  echo "Container will expire in ${EXPIRE_SECONDS} seconds"
  echo "Ready for external bash commands"
  # Simple sleep - tini will handle signals properly
  sleep ${EXPIRE_SECONDS}
  echo "Container expired after ${EXPIRE_SECONDS} seconds"
fi
exit 0
