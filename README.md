# streams-bot
Discord Bot for syncing streams to discord channel

## Environment Setup

```
# Copy example config file to local file.
# This file should not be checked in and is part of the .gitignore
cp streams-bot-config.json.example streams-bot-config.json

# Build the container
make docker-build

# Run the bot
make docker-run
```
