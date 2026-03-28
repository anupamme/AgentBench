#!/bin/bash
set -e
docker build -t agentbench/python:latest -f docker/python.Dockerfile docker/
docker build -t agentbench/node:latest -f docker/node.Dockerfile docker/
docker build -t agentbench/multi:latest -f docker/multi.Dockerfile docker/
