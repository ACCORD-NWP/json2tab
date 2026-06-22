.PHONY: list install install/minimal install/geojson install/euromap_generation install/plotting install/devtools install/full static_data web_data prep euromap tab_type_databases knmi_type_database fortran_type_database

# List all possbile make commands
list:
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$@$$'


# Example to run json2tab to generate tab files based on config-file CONFIG_FILE and overwrite OUTPUT_FOLDER and SITUATION_DATE
CONFIG_FILE=config.yaml
OUTPUT_FOLDER=output_2026
SITUATION_DATE=1-1-2026
example:
	rm -rf $(OUTPUT_FOLDER)
	mkdir -p $(OUTPUT_FOLDER)
	@echo "*" > $(OUTPUT_FOLDER)/.gitignore
	json2tab --config-file=$(CONFIG_FILE) --output-dir $(OUTPUT_FOLDER) --situation-date $(SITUATION_DATE)


# Different flavors of installation methods
install: install/standard

# Standard setup includes geojson support and plotting to add simple visualization of the generated turbines
install/standard:
	poetry install --with geojson,plotting

install/minimal:
	poetry install

# Additional packages needed for master database generation
install/euromap_generation:
	poetry install --with geojson,osmrequest,converters

# Additional packages needed for development
install/devtools:
	poetry install --with linting,test

install/full: install/euromap_generation, install/plotting, install/devtools


# Collect/build static data folder
static_data: tab_type_databases
	cd static_data && make

# Collect/build web data folder
web_data: install/euromap_generation
	cd web_data && make

# Generate master turbine database euromap
euromap: static_data web_data
	cd euromap && make



tab_type_databases: knmi_type_database fortran_type_database

# Auxillary task to covert old-style (or output-style) wind_turbine_xxx.tab files to input-style turbine_database.json
knmi_type_database: static_data/turbine_database+knmi.json
static_data/turbine_database+knmi.json:
	json2tab --inverse knmi_turbines/wind_turbine_*.tab --output static_data/turbine_database+knmi.json
  

# Auxillary task to covert Austrian fortran turbine types to input-style turbine_database.json
fortran_type_database: static_data/turbine_database+wf101.json
static_data/turbine_database+wf101.json:
	json2tab --inverse wf101_turbines/wind_turbine_*.tab --output static_data/turbine_database+wf101.json
