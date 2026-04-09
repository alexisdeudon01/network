ARG BUILD_FROM
FROM ${BUILD_FROM}

SHELL ["/bin/ash", "-o", "pipefail", "-c"]

RUN apk add --no-cache \
    bash \
    ca-certificates \
    coreutils \
    curl \
    jq \
    python3 \
    py3-pip \
    py3-requests \
    py3-jinja2 \
    py3-flask

COPY run.sh /run.sh
RUN chmod a+x /run.sh

COPY rootfs /
RUN chmod -R a+x /etc/services.d

WORKDIR /opt/fritzbox-agent

CMD [ "/run.sh" ]
