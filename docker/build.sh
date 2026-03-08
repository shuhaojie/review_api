#!/usr/bin/env bash
DATE=$(date +%Y%m%d)
COMMIT_ID=$(git rev-parse --short HEAD)

image="crpi-ya3kylqzs706jupe.cn-beijing.personal.cr.aliyuncs.com/vs_review/review_api:${DATE}_${COMMIT_ID}"

docker build -t "${image}" -f docker/Dockerfile .
echo "docker image:${image}"
#docker push "${image}"
