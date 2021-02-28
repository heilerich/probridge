FROM ubuntu:focal AS common
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update && apt-get -y upgrade && apt-get -y install pass 

FROM common AS build-env
RUN apt-get install -y libsecret-1-dev build-essential
ADD https://golang.org/dl/go${GO_VERSION}.linux-amd64.tar.gz /usr/local/
RUN tar -C /usr/local/ -xzf /usr/local/go${GO_VERSION}.linux-amd64.tar.gz && rm /usr/local/go${GO_VERSION}.linux-amd64.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"
RUN  set -ex; \
     \
     curl -o /usr/local/bin/su-exec.c https://raw.githubusercontent.com/ncopa/su-exec/master/su-exec.c; \
     \
     fetch_deps='gcc libc-dev'; \
     apt-get update; \
     apt-get install -y --no-install-recommends $fetch_deps; \
     rm -rf /var/lib/apt/lists/*; \
     gcc -Wall \
         /usr/local/bin/su-exec.c -o/usr/local/bin/su-exec; \
     chown root:root /usr/local/bin/su-exec; \
     chmod 0755 /usr/local/bin/su-exec
WORKDIR /work
CMD ["/bin/bash"]

FROM build-env AS builder
COPY . .
RUN make build-nogui

FROM common
RUN apt-get -y update && apt-get install -y libsecret-1-0
COPY --from=build-env /usr/local/bin/su-exec /usr/local/bin/su-exec
VOLUME /home/bridge
WORKDIR /app
COPY --from=builder /work/proton-bridge /bin/proton-bridge
COPY ./seed /app
ENTRYPOINT ["/app/entrypoint.sh"] 
CMD ["--noninteractive", "--log-level", "info"]
