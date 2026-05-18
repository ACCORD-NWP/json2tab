.PHONY: list install install/basic install/geojson install/euromap_generation install/plotting install/devtools install/full static_data web_data prep euromap tab_type_databases knmi_type_database fortran_type_database

example:
	json2tab --debug=1 --config-file=config.yaml


list:
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$@$$'


install/standard:
	poetry install --with geojson,plotting

install: install/standard

install/basic:
	poetry install

install/euromap_generation:
	poetry install --with geojson,osmrequest,converters

install/devtools:
	poetry install --with linting,test

install/full: install/euromap_generation, install/plotting, install/devtools


static_data: tab_type_databases
	cd static_data && make

web_data: install/euromap_generation
	cd web_data && make

euromap: static_data web_data
	cd euromap && make


tab_type_databases: knmi_type_database fortran_type_database

knmi_type_database: static_data/turbine_database+knmi.json
static_data/turbine_database+knmi.json:
	json2tab --debug=3 --inverse knmi_turbines/wind_turbine_*.tab --output static_data/turbine_database+knmi.json
  

fortran_type_database: static_data/turbine_database+wf101.json
static_data/turbine_database+wf101.json:
	json2tab --debug=3 --inverse wf101_turbines/wind_turbine_*.tab --output static_data/turbine_database+wf101.json
