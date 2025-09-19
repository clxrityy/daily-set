# syntax=docker/dockerfile:1.7-labs
FROM golang:tip-alpine3.22 AS build
WORKDIR /app
COPY go.mod ./
RUN --mount=type=cache,target=/go/pkg/mod apt-get update && apt-get upgrade -y && go mod download
COPY . .
RUN --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 \
    GOOS=linux \
    GOARCH=amd64 \
    go build -o /out/realtime ./...

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /
COPY --from=build /out/realtime /realtime
USER nonroot:nonroot
ENV REALTIME_ADDR=":8081"
EXPOSE 8081
ENTRYPOINT ["/realtime"]
