docker-build:
	docker build -t streams-bot:docker .

docker-run:
	docker run --name=streams-bot.service --rm -it streams-bot:docker

docker-bash:
	docker exec -it streams-bot.service /bin/bash
