#/bin/bash

sudo docker login
sudo docker buildx build -t verify:latest .
sudo docker tag verify:latest landixbtw987/verify:latest
sudo docker push landixbtw987/verify:latest

