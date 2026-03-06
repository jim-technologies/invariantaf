.PHONY: generate descriptor lint fmt build serve-mcp serve-cli test clean

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

build:
	go build -o unsplash-mcp .

serve-mcp:
	go run .

serve-cli:
	go run . --cli

test:
	go test -v -count=1 ./...

clean:
	rm -f unsplash-mcp descriptor.binpb
