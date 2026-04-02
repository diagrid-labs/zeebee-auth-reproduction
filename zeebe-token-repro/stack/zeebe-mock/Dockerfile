FROM golang:1.23-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY main.go .
RUN CGO_ENABLED=0 go build -o /zeebe-mock .

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /zeebe-mock /zeebe-mock
EXPOSE 26500
USER nonroot:nonroot
ENTRYPOINT ["/zeebe-mock"]
