.PHONY: descriptor lint fmt serve-mcp serve-cli test clean

TEMPORAL_API_DIR := .temporal-api
TEMPORAL_API_REPO := https://github.com/temporalio/api.git

$(TEMPORAL_API_DIR):
	git clone --depth 1 $(TEMPORAL_API_REPO) $(TEMPORAL_API_DIR)

descriptor: $(TEMPORAL_API_DIR)
	cd $(TEMPORAL_API_DIR) && buf build -o ../descriptor.binpb

lint:
	go vet ./...

fmt:
	gofmt -w .

test:
	go test -v -count=1 ./...

serve-mcp:
	go run .

serve-cli:
	go run . --cli

clean:
	rm -rf $(TEMPORAL_API_DIR) descriptor.binpb
