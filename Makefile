# Makefile for building amd64 docker images locally using buildx
# Usage:
#   make build            # build both app and worker images for amd64 and load into local docker
#   make build-app        # build app image
#   make build-worker     # build worker image
#   make clean-images     # remove local images built by this Makefile

IMAGE_PREFIX ?= docker.io/hedw
VERSION ?= 1.4.5
PLATFORM ?= linux/amd64

# Nexus registry prefix for push
NEXUS_REGISTRY ?= nexus-camc.sybs.online/ots-group/library/docker.io/hedw

.PHONY: build build-app build-worker clean-images

build: build-app build-worker

build-app:
	@echo "构建 app 镜像: $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION) for $(PLATFORM)"
	# 使用 buildx，--load 会将镜像加载到本地 docker（需要 buildx driver 支持）
	# 确保使用最新代码而不是缓存
	docker buildx build --platform $(PLATFORM) --load -t $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION) \
		-f Dockerfile --target app .

build-worker:
	@echo "构建 worker 镜像: $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION)-worker for $(PLATFORM)"
	# 确保使用最新代码而不是缓存
	docker buildx build --platform $(PLATFORM) --load -t $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION)-worker \
		-f Dockerfile --target worker .

clean-images:
	@echo "删除本地构建的镜像"
	-docker rmi $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION) || true
	-docker rmi $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION)-worker || true

# 推送镜像到注册表
.PHONY: push push-app push-worker

push-app:
	@echo "推送 app 镜像: $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION)"
	docker push $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION)

push-worker:
	@echo "推送 worker 镜像: $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION)-worker"
	docker push $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION)-worker

push: push-app push-worker

# 直接使用 buildx 构建并推送（可选，替代上面的单独构建再 push 工作流）
.PHONY: buildx-push-app buildx-push-worker buildx-push

buildx-push-app:
	@echo "使用 buildx 构建并推送 app 镜像 ($(PLATFORM))"
	docker buildx build --platform $(PLATFORM) --push -t $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION) \
		-f Dockerfile --target app .

buildx-push-worker:
	@echo "使用 buildx 构建并推送 worker 镜像 ($(PLATFORM))"
	docker buildx build --platform $(PLATFORM) --push -t $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION)-worker \
		-f Dockerfile --target worker .

buildx-push: buildx-push-app buildx-push-worker

# =============== Nexus push targets ===============
.PHONY: push-nexus push-nexus-app push-nexus-worker

push-nexus-app:
	@echo "给 app 镜像打 tag 并推送到 Nexus: $(NEXUS_REGISTRY)/ai-codereview-gitlab:$(VERSION)"
	@docker tag $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION) $(NEXUS_REGISTRY)/ai-codereview-gitlab:$(VERSION)
	@docker push $(NEXUS_REGISTRY)/ai-codereview-gitlab:$(VERSION)

push-nexus-worker:
	@echo "给 worker 镜像打 tag 并推送到 Nexus: $(NEXUS_REGISTRY)/ai-codereview-gitlab:$(VERSION)-worker"
	@docker tag $(IMAGE_PREFIX)/ai-codereview-gitlab:$(VERSION)-worker $(NEXUS_REGISTRY)/ai-codereview-gitlab:$(VERSION)-worker
	@docker push $(NEXUS_REGISTRY)/ai-codereview-gitlab:$(VERSION)-worker

push-nexus: push-nexus-app push-nexus-worker
