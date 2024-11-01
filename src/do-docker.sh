#/bin/bash

docker buildx build -t verify:latest .
docker tag verify:latest landixbtw987/verify:latest
docker push landixbtw987/verify:latest

