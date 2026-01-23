FROM golang:1.22-alpine AS build
WORKDIR /src
RUN apk add --no-cache gcc musl-dev libpcap-dev
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=1 go build -o /out/collector .

FROM alpine:3.19
WORKDIR /app
RUN apk add --no-cache libpcap
COPY --from=build /out/collector /app/collector
ENV REDIS_ADDR=redis:6379
ENV REDIS_STREAM=flows
ENV CAPTURE_MODE=live
CMD ["/app/collector"]
