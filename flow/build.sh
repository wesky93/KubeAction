#!/bin/bash
tag=spaceone/kubeaction-job:$1
docker build -t $tag .  && docker push $tag

# . ./build.sh <version> -> . ./build.sh 0.0.13