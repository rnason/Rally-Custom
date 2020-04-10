# Container image that runs your code
FROM alpine:3.11.5

LABEL authors="Rich Nason"

# Copies your code file from your action repository to the filesystem path `/` of the container
RUN mkdir /github
COPY templates /github/templates
COPY requirements.txt /github/requirements.txt
COPY github_pr_report.py /github/github_pr_report.py
WORKDIR /github

# Install Required pkgs
# RUN apk add --no-cache python3 go git bash
RUN apk add --no-cache python3
RUN pip3 install pip --upgrade
RUN pip3 install PyGithub progress cloudmage-jinjautils atlassian-python-api
# RUN pip3 install -r /github/requirements.txt

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["python3", "github_pr_report.py"]