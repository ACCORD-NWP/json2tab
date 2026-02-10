install_basic:
	poetry install

install_extras: install_basic
	poetry install --with plotting,osmrequest,locationmerger,linting

all: tab_type_databases
tab_type_databases: knmi_type_database fortran_type_database

json2tab:
	json2tab --debug=3 --config-file=myconfig.yaml

knmi_type_database:
	json2tab --debug=3 --inverse knmi_turbines/wind_turbine_*.tab --output static_data/turbine_database+knmi.json
  
fortran_type_database:
	json2tab --debug=3 --inverse wf101_turbines/wind_turbine_*.tab --output static_data/turbine_database+wf101.json

osm_turbines_webapi:
	json2tab --debug=3 --fetch-osm-data "static_data/windturbine_windfarm_locations_osm_$(shell date +%Y%m%d).[csv,geojson]"

osm_turbines_local:
	python -c "from json2tab.location_converters.overpass_query_builder import build_query; print(build_query(windturbine=True, windfarm=True))" > overpass_query.txt
	./run_overpass_query.sh db overpass_query.txt static_data/turbine_locations_osm_20260103.local.overpass_output.json
	json2tab --debug=3 --convert static_data/turbine_locations_osm_20260103.local.overpass_output.json --type osm --output static_data/turbine_locations_osm_20260103.csv
	rm overpass_query.txt

convert_osm_today: static_data/windturbine_windfarm_locations_osm_$(shell date +%Y%m%d).overpass_output.json
	rm -f static_data/windturbine_windfarm_locations_osm_$(shell date +%Y%m%d).csv
	json2tab --debug=3 --convert static_data/windturbine_windfarm_locations_$(shell date +%Y%m%d).overpass_output.json --type osm_windturbine_windfarm --output static_data/windturbine_windfarm_locations_osm_$(shell date +%Y%m%d).csv
	json2tab --debug=2 --convert static_data/windturbine_windfarm_locations_osm_$(shell date +%Y%m%d).csv static_data/worldmap/EEZ/EEZ_land_union_v4_202410.shp static_data/worldmap/country_borders/countries.geojson --type fix_country_offshore
	json2tab --debug=3 --convert static_data/windturbine_windfarm_locations_osm_$(shell date +%Y%m%d).csv --type csv2geojson

convert_osm_20260114:
	rm -f static_data/windturbine_windfarm_locations_osm_20260114*.csv
	json2tab --debug=3 --convert static_data/windturbine_windfarm_locations_osm_20260114.overpass_output_windturbine=true_windfarm=true.json --type osm_windturbine_windfarm --output static_data/windturbine_windfarm_locations_osm_20260114.csv
	json2tab --debug=2 --convert static_data/windturbine_windfarm_locations_osm_20260114.csv static_data/worldmap/EEZ/EEZ_land_union_v4_202410.shp static_data/worldmap/country_borders/countries.geojson --type fix_country_offshore
	json2tab --debug=3 --convert static_data/windturbine_windfarm_locations_osm_20260114.csv --type csv2geojson

# Timestamp for today in filenames
TODAY_STAMP:=$(shell date +%Y%m%d)
# Debug level as to control debug output from json2tab
DEBUG_LEVEL=3
# Minimal distance between turbines, used for merging turbines from different sources
MIN_TURBINE_DIST:=0.00025#~25m
# OSM: download todays data yes|no
OSM_DOWNLOAD:=false
# OSM: renew OSM csv-file from static_data
OSM_RENEW:=false
# Austria: Download data from IGwindkraft directly from website
IG_WINDKRAFT_DOWNLOAD:=false

# OpenStreetMap data handling
OSM_BASENAME:=windturbine_windfarm_locations_osm
OSM_REQ_DATE_STAMP:=$(shell ls -v static_data/$(OSM_BASENAME)_*.overpass_output_windturbine=true_windfarm=true.json | tail -1 | sed -e s/[^0-9]//g)
OSM_REQ_OUTPUT_FILE:=$(OSM_BASENAME)_$(OSM_REQ_DATE_STAMP).overpass_output_windturbine=true_windfarm=true.json
OSM_TODAY_FILE:=$(OSM_BASENAME)_$(TODAY_STAMP).csv
OSM_TODAY_OUTPUT_FILE:=$(OSM_BASENAME)_$(TODAY_STAMP).overpass_output_windturbine=true_windfarm=true.json

# Country/eez border files to determine country and is_offshore flags
COUNTRY_BORDER_FILE:="static_data/worldmap/country_borders/World Bank Official Boundaries - Admin 0/WB_GAD_ADM0.shp"
EEZ_FILE:="static_data/worldmap/EEZ/EEZ_land_union_v4_202410.shp"

OUTPUT_FOLDER:=generated_database

euromap:
	rm -rf $(OUTPUT_FOLDER)
	mkdir $(OUTPUT_FOLDER)
	@echo "*" > $(OUTPUT_FOLDER)/.gitignore
	@echo "=== CONVERTING EUROPE-WIDE INPUT DATA ==="

ifeq ($(OSM_RENEW), true)
ifeq ($(OSM_DOWNLOAD), true)
	@echo "=== >>> DOWNLOADING NEW OSM DATA <<< ==="
	json2tab --debug=$(DEBUG_LEVEL) --fetch-osm-data "$(OUTPUT_FOLDER)/$(OSM_TODAY_FILE)"
	cp $(OUTPUT_FOLDER)/$(OSM_BASENAME)_$(TODAY_STAMP)* static_data/
else
	@echo "=== >>> CREATING NEW OSM FILE BASED ON REQUEST static_data/$(OSM_REQ_OUTPUT_FILE) <<< ==="
	cp static_data/$(OSM_REQ_OUTPUT_FILE) $(OUTPUT_FOLDER)/$(OSM_TODAY_OUTPUT_FILE)
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/$(OSM_TODAY_OUTPUT_FILE) --type osm_windturbine_windfarm --output $(OUTPUT_FOLDER)/$(OSM_TODAY_FILE)
endif
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/$(OSM_TODAY_FILE) $(EEZ_FILE) $(COUNTRY_BORDER_FILE) --type fix_country_offshore
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/$(OSM_TODAY_FILE) --type remove_short_distance --min-distance=$(MIN_TURBINE_DIST) --output $(OUTPUT_FOLDER)/osm.csv
	cp $(OUTPUT_FOLDER)/$(OSM_TODAY_FILE) static_data/$(OSM_TODAY_FILE)
	mv $(OUTPUT_FOLDER)/osm.csv $(OUTPUT_FOLDER)/osm.copy
else
	@echo "=== >>> COPYING PROCESSED OSM DATA BASED ON REQUEST $(OSM_REQ_DATE_STAMP) <<< ==="
	cp static_data/$(OSM_BASENAME)_$(OSM_REQ_DATE_STAMP).csv $(OUTPUT_FOLDER)/osm.copy
endif

	@echo "=== >>> CREATING WF101 DATA <<< ==="
	json2tab --debug=$(DEBUG_LEVEL) --convert ms_data/wf101.txt --type wf2csv --output $(OUTPUT_FOLDER)/wf101.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/wf101.csv --type remove_short_distance --min-distance=$(MIN_TURBINE_DIST) --output $(OUTPUT_FOLDER)/wf101.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/wf101.csv $(EEZ_FILE) $(COUNTRY_BORDER_FILE) --type fix_country_offshore
	mv $(OUTPUT_FOLDER)/wf101.csv $(OUTPUT_FOLDER)/wf101.copy

	@echo "=== CONVERTING MEMBER STATE INPUT DATA TO CSV ==="
	json2tab --debug=$(DEBUG_LEVEL) --convert ms_data/nl/rivm_20250101_windturbines_vermogen/rivm_20250101_windturbines_vermogen.shp ms_data/nl/rws_20240101_windparken_turbines/windparken_turbinesPoint.shp --type netherlands --output $(OUTPUT_FOLDER)/netherlands.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert ms_data/be/er_windturb_st_aangevr/er_windturb_st_aangevr.shp --type flanders --min-distance=$(MIN_TURBINE_DIST) --output $(OUTPUT_FOLDER)/flanders_onshore.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert ms_data/be/belgian_offshore_with_types.csv --type csv2csv --output $(OUTPUT_FOLDER)/belgium_offshore.csv --write-columns source="Belgium Offshore",is_offshore=True,country=Belgium
	json2tab --debug=$(DEBUG_LEVEL) --convert ms_data/de/Gesamtdatenexport_20260101_25.2/EinheitenWind.xml --type germany --output $(OUTPUT_FOLDER)/germany.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert "ms_data/dnk/Vindmølledata til 2025-01.xlsx" --type denmark --output $(OUTPUT_FOLDER)/denmark.csv
ifeq ($(IG_WINDKRAFT_DOWNLOAD), true)
	json2tab --debug=$(DEBUG_LEVEL) --convert https://www.igwindkraft.at/aktuelles/windrad-karte --type austria --output $(OUTPUT_FOLDER)/austria_igwindkraft.csv
else
	json2tab --debug=$(DEBUG_LEVEL) --convert ms_data/at/igwindkraft-windrad-karte.json --type austria --output $(OUTPUT_FOLDER)/austria_igwindkraft.csv
endif
	json2tab --debug=$(DEBUG_LEVEL) --convert "ms_data/swe/VBK_export_allman_prod.xlsx" --type sweden --output $(OUTPUT_FOLDER)/sweden.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert "ms_data/uk/REPD_Publication_Q3_2025.xlsx" --type uk --output $(OUTPUT_FOLDER)/uk_windfarms.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert ms_data/fin/finland_wind_fleet_data_202506.json --type finland --output $(OUTPUT_FOLDER)/finland.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert ms_data/it/Italian_Wind_Farms_db.xlsx --type italy --output $(OUTPUT_FOLDER)/italy_windfarms.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert ms_data/bg/bulgarian_wind_farms_combined.csv --type csv2csv --output $(OUTPUT_FOLDER)/bulgarian_windfarms.csv --rename-columns power_kw=installed_power

#	BENCHMARK RESULTS COMPARING with WindEurope at 1-1-2025
# 	POTENTIAL CORRECTION BY LOADING TWPnet DATA: Spain (-40% -> 0%), Italy (-16% -> +6%), Poland (-25% -> -3%), Belgium (-14% -> -4%)
# 	NO CORRECTIONS KNOWN: Turkey (-46%), Greece (-81%), Ukraine (-84%), Lithuania (-12%), Croatia (-18%), Estonia (-14%)

	@echo "=== FIXING COUNTRY FLAG FOR ALL PRODUCES MS_DATA CSVs ==="
	mv $(OUTPUT_FOLDER)/osm.copy $(OUTPUT_FOLDER)/osm.csv
	mv $(OUTPUT_FOLDER)/netherlands.csv $(OUTPUT_FOLDER)/netherlands.copy
	ls -al $(OUTPUT_FOLDER)/*.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/*.csv $(EEZ_FILE) $(COUNTRY_BORDER_FILE)  --type fix_country_offshore
	mv $(OUTPUT_FOLDER)/netherlands.copy $(OUTPUT_FOLDER)/netherlands.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/netherlands.csv $(EEZ_FILE) $(COUNTRY_BORDER_FILE)  --type fix_country
#	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/finland.csv $(OUTPUT_FOLDER)/italy_windfarms.csv $(OUTPUT_FOLDER)/bulgarian_windfarms.csv $(EEZ_FILE) $(COUNTRY_BORDER_FILE)  --type fix_offshore
	mv $(OUTPUT_FOLDER)/osm.csv $(OUTPUT_FOLDER)/osm.copy
	
	@echo "=== MOVE OSM and WF101 FILES BACK AS CSV FILE ==="
	mv $(OUTPUT_FOLDER)/osm.copy $(OUTPUT_FOLDER)/osm.csv
	mv $(OUTPUT_FOLDER)/wf101.copy $(OUTPUT_FOLDER)/wf101.csv

	@echo "=== BUILD AUSTRIA, ENRICH OSM AUSTRIA DATA WITH WF101 ==="
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/wf101.csv --type select_country --country Austria --output $(OUTPUT_FOLDER)/austria_wf101.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm.csv --type select_country --country Austria --output $(OUTPUT_FOLDER)/austria_osm.csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/austria_osm.csv $(OUTPUT_FOLDER)/austria_wf101.csv --merge-mode enrich_first --output $(OUTPUT_FOLDER)/austria_osm_wf101.csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/austria_igwindkraft.csv $(OUTPUT_FOLDER)/austria_osm_wf101.csv --output $(OUTPUT_FOLDER)/austria.csv

	@echo "=== BUILD BELGIUM ==="
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/flanders_onshore.csv $(OUTPUT_FOLDER)/belgium_offshore.csv --output $(OUTPUT_FOLDER)/belgium.csv

	@echo "=== BUILD ITALY, ENRICH OSM+WF101 DATA WITH WINDFARM DATA ==="
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm.csv --type select_country --country Italy --output $(OUTPUT_FOLDER)/italy_osm.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/wf101.csv --type select_country --country Italy --output $(OUTPUT_FOLDER)/italy_wf101.csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/italy_osm.csv $(OUTPUT_FOLDER)/italy_wf101.csv --output $(OUTPUT_FOLDER)/italy_osm+wf101.csv
	json2tab --debug=$(DEBUG_LEVEL) --map $(OUTPUT_FOLDER)/italy_windfarms.csv $(OUTPUT_FOLDER)/italy_osm+wf101.csv --output $(OUTPUT_FOLDER)/italy.csv

	@echo "=== BUILD BULGARIA, ENRICH OSM DATA WITH WINDFARM DATA ==="
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm.csv --type select_country --country Bulgaria --output $(OUTPUT_FOLDER)/bulgaria_osm.csv
	json2tab --debug=$(DEBUG_LEVEL) --map $(OUTPUT_FOLDER)/bulgarian_windfarms.csv $(OUTPUT_FOLDER)/bulgaria_osm.csv --output $(OUTPUT_FOLDER)/bulgaria.csv

	@echo "=== BUILD UK, ENRICH WINDFARM DATA WITH OSM DATA ==="
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm.csv --type select_country --country "United Kingdom" --output $(OUTPUT_FOLDER)/uk_osm.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/uk_windfarms.csv --type select_offshore --output $(OUTPUT_FOLDER)/uk_windfarms_offshore.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/uk_windfarms.csv --type select_onshore --output $(OUTPUT_FOLDER)/uk_windfarms_onshore.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/uk_osm.csv --type select_offshore --output $(OUTPUT_FOLDER)/uk_osm_offshore.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/uk_osm.csv --type select_onshore --output $(OUTPUT_FOLDER)/uk_osm_onshore.csv
	json2tab --debug=$(DEBUG_LEVEL) --map $(OUTPUT_FOLDER)/uk_windfarms_onshore.csv $(OUTPUT_FOLDER)/uk_osm_onshore.csv --output $(OUTPUT_FOLDER)/uk_onshore.csv --max-distance=0.1 --merge-mode=combine
	json2tab --debug=$(DEBUG_LEVEL) --map $(OUTPUT_FOLDER)/uk_windfarms_offshore.csv $(OUTPUT_FOLDER)/uk_osm_offshore.csv --output $(OUTPUT_FOLDER)/uk_offshore.csv --max-distance=0.25 --merge-mode=enrich_first
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/uk_onshore.csv $(OUTPUT_FOLDER)/uk_offshore.csv --output $(OUTPUT_FOLDER)/uk.csv

	@echo "=== RESTRICT MS DATA TO ONLY OWN COUNTRY ==="
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/netherlands.csv --type select_country --country Netherlands
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/belgium.csv --type select_country --country Belgium
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/germany.csv --type select_country --country Germany
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/austria.csv --type select_country --country Austria
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/denmark.csv --type select_country --country Denmark
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/finland.csv --type select_country --country Finland
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/italy.csv --type select_country --country Italy
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/bulgaria.csv --type select_country --country Bulgaria
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/sweden.csv --type select_country --country Sweden
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/uk.csv --type select_country --country "United Kingdom"

	@echo "=== MERGING MEMBER STATE INPUT DATA FILES ==="
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/netherlands.csv $(OUTPUT_FOLDER)/belgium.csv --output $(OUTPUT_FOLDER)/netherlands+belgium.csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/germany.csv $(OUTPUT_FOLDER)/austria.csv --output $(OUTPUT_FOLDER)/germany+austria.csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/netherlands+belgium.csv $(OUTPUT_FOLDER)/germany+austria.csv --output $(OUTPUT_FOLDER)/netherlands+belgium+germany+austria.csv

	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/sweden.csv $(OUTPUT_FOLDER)/finland.csv --output $(OUTPUT_FOLDER)/sweden+finland.csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/denmark.csv $(OUTPUT_FOLDER)/uk.csv --output $(OUTPUT_FOLDER)/denmark+uk.csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/denmark+uk.csv $(OUTPUT_FOLDER)/sweden+finland.csv --output $(OUTPUT_FOLDER)/denmark+uk+sweden+finland.csv
	
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/italy.csv $(OUTPUT_FOLDER)/bulgaria.csv --output $(OUTPUT_FOLDER)/italy+bulgaria.csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/denmark+uk+sweden+finland.csv $(OUTPUT_FOLDER)/italy+bulgaria.csv --output $(OUTPUT_FOLDER)/denmark+uk+sweden+finland+italy+bulgaria.csv

	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/netherlands+belgium+germany+austria.csv $(OUTPUT_FOLDER)/denmark+uk+sweden+finland+italy+bulgaria.csv --output $(OUTPUT_FOLDER)/ms_data.csv


	@echo "=== REMOVE SPECIFIC COUNTRIES FROM OSM OR WF101 ==="
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/wf101.csv --type remove_country --country Netherlands

	@echo "=== MERGING EUROPE MAPS (W/O COUNTRY EXCLUSIVE DATA) ==="
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/osm.csv $(OUTPUT_FOLDER)/wf101.csv --output $(OUTPUT_FOLDER)/osm+wf101.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm+wf101.csv --type remove_country --country Germany Austria Denmark Italy Bulgaria "United Kingdom"

	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/ms_data.csv $(OUTPUT_FOLDER)/osm+wf101.csv --output $(OUTPUT_FOLDER)/euromap_$(TODAY_STAMP).[csv,geojson]
	ln -s euromap_$(TODAY_STAMP).geojson $(OUTPUT_FOLDER)/euromap.geojson
	ln -s euromap_$(TODAY_STAMP).csv $(OUTPUT_FOLDER)/euromap.csv

	@echo "=== REMOVE TEMP FILES ==="
	rm $(OUTPUT_FOLDER)/*.csv.orig

	@echo "=== COMPRESS DATABASE TO TAR FILE ==="
	cd $(OUTPUT_FOLDER) && tar -czvf euromap_$(TODAY_STAMP).tar.gz euromap_$(TODAY_STAMP).csv euromap_$(TODAY_STAMP).geojson && cd ..
	
euromap_offshore:
	json2tab --debug=2 --convert $(OUTPUT_FOLDER)/euromap.csv --type select_offshore --output $(OUTPUT_FOLDER)/euromap_offshore.csv

euromap_fix_with_thewindpower:
	json2tab --debug=3 --convert ms_data/eu/TheWindPower/Windfarms_Europe_20211112.xls --type thewindpower --output $(OUTPUT_FOLDER)/thewindpower.csv --rename-columns "Total power"="Total power [kW]"
	json2tab --debug=2 --convert $(OUTPUT_FOLDER)/thewindpower.csv $(EEZ_FILE) $(COUNTRY_BORDER_FILE) --type fix_country_offshore
	json2tab --debug=2 --convert $(OUTPUT_FOLDER)/thewindpower.csv --output $(OUTPUT_FOLDER)/thewindpower_selected_countries.csv --type select_country --country Spain Italy Poland Belgium
	json2tab --debug=2 --convert $(OUTPUT_FOLDER)/euromap.csv --output $(OUTPUT_FOLDER)/euromap_selected_countries.csv --type select_country --country Spain Italy Poland Belgium
	json2tab --debug=2 --map $(OUTPUT_FOLDER)/thewindpower_selected_countries.csv $(OUTPUT_FOLDER)/euromap_selected_countries.csv --output $(OUTPUT_FOLDER)/euromap_selected_countries_twp_fixed.csv
	json2tab --debug=2 --merge $(OUTPUT_FOLDER)/euromap.csv $(OUTPUT_FOLDER)/euromap_selected_countries_twp_fixed.csv --output $(OUTPUT_FOLDER)/euromap_twp_fixed.[csv,geojson]

