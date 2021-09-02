#!/bin/bash

git pull --rebase origin main && make docker-build && sudo systemctl restart streams-bot.service
