export SNAPSHOT_REGISTRY ?= us-docker.pkg.dev/fleetrouting-app-ops/fleetrouting-app/snapshot
export RELEASE_REGISTRY ?= us-docker.pkg.dev/fleetrouting-app-ops/fleetrouting-app/release
export REGISTRY=europe-west1-docker.pkg.dev/beefast-exp-routing/beefast-exp-main-docker/routing-app
export COMMIT_TAG ?= 1.2.2
export RELEASE_TAG  ?= 0.0.0

application := application

.PHONY: build push release

build:
	$(MAKE) -C application build

push:
	$(MAKE) -C application push

release:
	$(MAKE) -C application release
