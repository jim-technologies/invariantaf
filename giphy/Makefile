.PHONY: generate descriptor build test clean lint fmt serve-mcp serve-cli

generate:
	cd proto && buf generate
	cd proto && buf build -o ../descriptor.binpb

descriptor:
	cd proto && buf build -o ../descriptor.binpb

build: generate
	go build -o giphy-mcp .

test:
	go test -v -count=1 ./...

lint:
	cd proto && buf lint
	go vet ./...

fmt:
	cd proto && buf format -w
	gofmt -w .

serve-mcp:
	go run .

serve-cli:
	go run . --cli

clean:
	rm -rf descriptor.binpb giphy-mcp giphy/v1/giphy.pb.go
