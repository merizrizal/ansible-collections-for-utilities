install:
	@cd merizrizal/utils; \
	ansible-galaxy collection build -f --output-path $$ROOT_DIR

	@version=`(yq '.version' merizrizal/utils/galaxy.yml)`; \
	ansible-galaxy collection install -f merizrizal-utils-$$version.tar.gz
