docker-build:
	docker build -t streams-bot:docker .

docker-run:
	docker run --name=streams-botkeeper.service --rm -it streams-bot:docker

docker-bash:
	docker exec -it streams-botkeeper.service /bin/bash
