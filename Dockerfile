FROM python:3.7-slim-buster

RUN apt-get update && \
    apt-get install --yes --no-install-recommends git curl git-crypt unzip amazon-ecr-credential-helper file && \
    rm -rf /var/lib/apt/lists/*

ENV VENV_PATH /opt/venv
ENV PATH ${VENV_PATH}:/opt/google-cloud-sdk/bin:/opt/awscli/bin:${PATH}

# Install gcloud CLI
# Force gcloud to run on python3 ugh
ENV CLOUDSDK_PYTHON python3
RUN curl -sSL https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-298.0.0-linux-x86_64.tar.gz | tar -xzf - -C /opt/

# Install aws CLI
RUN cd /tmp && \
    curl -sSL "https://d1vvhvl2y92vvt.cloudfront.net/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip -qq awscliv2.zip && \
    ./aws/install -i /opt/awscli -b /opt/awscli/bin

# Install SOPS
RUN cd /tmp && \
    curl -sSL -o sops.deb https://github.com/mozilla/sops/releases/download/v3.5.0/sops_3.5.0_amd64.deb && \
    apt-get install ./sops.deb && \
    rm sops.deb

# Download helm v2/v3 to helm/helm3. Make hubploy use a specific binary with
# HELM_EXECUTABLE environment variable.
RUN cd /tmp && mkdir helm && \
    curl -sSL https://get.helm.sh/helm-v2.16.9-linux-amd64.tar.gz | tar -xzf - -C helm && \
    mv helm/linux-amd64/helm /usr/local/bin/helm && \
    curl -sSL https://get.helm.sh/helm-v3.2.4-linux-amd64.tar.gz | tar -xzf - -C helm && \
    mv helm/linux-amd64/helm /usr/local/bin/helm3 && \
    rm -rf helm

RUN python3 -m venv ${VENV_PATH}

COPY . /srv/repo
RUN python3 -m pip install --no-cache-dir /srv/repo

ENTRYPOINT ["hubploy"]
