#!/bin/bash

DOCKER_IMAGE="docker-registry.brightpowerinc.com/rancher-openvpn"
DOCKER_TAG="$1"

if [ "$DOCKER_TAG" = "" ]
then
	echo "Usage : $0 tag"
	exit 1
fi

[ ! -e "Dockerfile" ] && echo "Missing Dockerfile" && exit 2

docker build -t $DOCKER_IMAGE:$DOCKER_TAG .

if [ "$?" = "0" ]
then
	echo "Build done for tag $DOCKER_IMAGE:$DOCKER_TAG"
else
	echo "Build failed for tag $DOCKER_IMAGE:$DOCKER_TAG"
fi
