.PHONY: generate descriptor lint fmt serve-mcp serve-cli test clean build

build:
	go build -o quicknode-mcp .

generate:
	cd proto && buf generate
	cd proto && buf build -o ../descriptor.binpb

descriptor:
	cd proto && buf build -o ../descriptor.binpb

lint:
	cd proto && buf lint
	go vet ./...

fmt:
	cd proto && buf format -w
	gofmt -w .

test:
	go test -v -count=1 ./...

serve-mcp:
	go run .

serve-cli:
	go run . --cli

clean:
	rm -f quicknode-mcp
	rm -rf quicknode/v1/*.pb.go descriptor.binpb
