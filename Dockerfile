# Base container
FROM python:3.10.10-slim as base

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

ENV PYROOT /pyroot
ENV PYTHONUSERBASE $PYROOT
ENV PATH "$PYROOT/bin:$PATH"

ENV PYTHONUNBUFFERED 1


# Intermidiate container for dependancies and temporary packages
FROM base as dependencies

# Version of used terraform binary
ENV TFVER "0.12.10"

# Url of terraform binaries repo
ENV TFURL "https://releases.hashicorp.com/terraform/"

ENV TFURL "$TFURL$TFVER/terraform_${TFVER}_linux_amd64.zip"

RUN apt-get update && apt-get install -y wget unzip

COPY Pipfile* ./

RUN wget $TFURL -O terraform_bin.zip

RUN unzip terraform_bin.zip

RUN pip install pipenv

RUN PIP_USER=1 PIP_IGNORE_INSTALLED=1 pipenv install --dev --system --deploy


# Final container with optimized size
FROM base as final

COPY . /home/user/app
COPY --from=dependencies $PYROOT $PYROOT
COPY --from=dependencies terraform /home/user/app/tf_bin/terraform

ENV APP_DIR "/home/user/app"
ENV PYTHONPATH "$APP_DIR"

ENV PATH $PATH:$APP_DIR/tf_bin

RUN groupadd -r user && \
    useradd -r -g user user

COPY . /home/user/app

RUN chown -R user:user /home/user

WORKDIR /home/user/app

USER user
