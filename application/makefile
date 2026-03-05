.PHONY: build push release

build:
	# make sure we build an amd64 image (Cloud Run requires linux/amd64)
	# `docker build` on arm hosts produces an index that may lack amd64,
	# so explicitly set the platform or use buildx.
	docker build --platform linux/amd64 -t $(REGISTRY):$(COMMIT_TAG) -f Dockerfile .

push:
	docker push $(REGISTRY):$(COMMIT_TAG);

release:
	$(eval DIGEST = $(shell gcloud container images list-tags $(SNAPSHOT_REGISTRY) --filter=$(COMMIT_TAG) --format='get(digest)'))
	gcloud container images add-tag --quiet \
		$(SNAPSHOT_REGISTRY)@$(DIGEST) \
		$(RELEASE_REGISTRY):$(COMMIT_TAG) \
		$(RELEASE_REGISTRY):$(RELEASE_TAG)

default: build
