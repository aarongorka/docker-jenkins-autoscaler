# this directive will make $(BUILD_VERSION) accessible as a normal env var
export

SEMVER = 1.0.0

##################
# PUBLIC TARGETS #
##################
dockerBuild:
	docker-compose build jenkins-autoscaler

shell: .env
	@docker-compose down -v
	docker-compose run --rm jenkins-autoscaler sh

gitTag:
	git tag $(SEMVER)
	git push origin $(SEMVER)

###########
# ENVFILE #
###########
.env:
	@echo "Create .env with .env.template"
# due to https://github.com/docker/compose/issues/6206 .env must exist before running anything with docker-compose
# we also ignore errors with '-' because "permission denied" probably means the file already exists, and disable output with '@'
	-@echo "" >> .env
# we must run cp in docker because Windows does not have cp
	@docker-compose down -v
	docker-compose run --rm jenkins-autoscaler cp .env.template .env

cleanEnv:
	-@echo "" >> .env
	@docker-compose down -v
	docker-compose run --rm jenkins-autoscaler rm -f .env
