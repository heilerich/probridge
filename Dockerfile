FROM ubuntu:focal AS common
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update && apt-get -y upgrade && apt-get -y install pass gosu && rm -rf /var/lib/apt/lists/*; \
    # verify that the binary works
	gosu nobody true

FROM common AS build-env
RUN apt-get install -y libsecret-1-dev build-essential
ADD https://golang.org/dl/go${GO_VERSION}.linux-amd64.tar.gz /usr/local/
RUN tar -C /usr/local/ -xzf /usr/local/go${GO_VERSION}.linux-amd64.tar.gz && rm /usr/local/go${GO_VERSION}.linux-amd64.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"
WORKDIR /work
CMD ["/bin/bash"]

FROM build-env AS builder
COPY . .
RUN make build-nogui

FROM common
RUN apt-get -y update && apt-get install -y libsecret-1-0
VOLUME /home/bridge
WORKDIR /app
COPY --from=builder /work/proton-bridge /bin/proton-bridge
COPY ./seed /app
ENTRYPOINT ["/app/entrypoint.sh"] 
CMD ["--noninteractive", "--log-level", "info"]
