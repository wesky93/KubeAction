#!/bin/bash
tag=spaceone/kubeaction-controller:$1
latest=spaceone/kubeaction-controller:latest
docker build -t $tag .  && docker push $tag
docker build -t $latest .  && docker push $latest

# . ./build.sh <version> -> . ./build.sh 0.0.13