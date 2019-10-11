FROM python:3.6.9

ENV PYTHONUNBUFFERED 1

ENV APP_DIR "/home/user/app"
ENV PYTHONPATH "$APP_DIR"

ENV GOOGLE_APPLICATION_CREDENTIALS "/home/user/app/resources/gcp_key.json"

# Version of used terraform binary
ENV TFVER "0.12.10"

# Url of terraform binaries repo
ENV TFURL "https://releases.hashicorp.com/terraform/"

# Format url to compressed terraform binary for linux amd64
ENV TFURL "$TFURL$TFVER/terraform_${TFVER}_linux_amd64.zip"

RUN pip install pipenv

RUN groupadd -r user && \
    useradd -r -g user user

COPY . /home/user/app

RUN chown -R user:user /home/user

WORKDIR /home/user/app

USER user

# Install all dependencies
RUN pipenv install --dev

# Download and decompress terraform to working directory
RUN wget $TFURL -O terraform_bin.zip
RUN unzip terraform_bin.zip -d ${APP_DIR}

# Copy your gcp service account key
COPY ./resources/gcp_key.json /home/user/app/resources/

ENTRYPOINT pipenv shell
