FROM alpine:3.20

RUN apk add --no-cache curl jq xz mtools sfdisk coreutils

COPY build-image.sh /usr/local/bin/build-image.sh
RUN chmod +x /usr/local/bin/build-image.sh

WORKDIR /work
ENTRYPOINT ["/usr/local/bin/build-image.sh"]
