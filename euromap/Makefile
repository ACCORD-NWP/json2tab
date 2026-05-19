INPUT_FOLDER:=../web_data
OUTPUT_FOLDER:=output


# Timestamp for today in filenames
TODAY_STAMP:=$(shell date +%Y%m%d)
# Debug level as to control debug output from json2tab
DEBUG_LEVEL=3
# Minimal distance between turbines, used for merging turbines from different sources
MIN_TURBINE_DIST:=0.00025#~25m

# Country/eez border files to determine country and is_offshore flags
EEZ_FILE:="$(PWD)/../static_data/worldmap/eez/EEZ_land_union_v4_202410.shp"
COUNTRY_BORDER_FILE:="$(PWD)/../static_data/worldmap/country_borders/WB_GAD_ADM0.shp"
PROVINCIE_BORDER_FILE:="$(PWD)/../static_data/worldmap/country_borders/WB_GAD_ADM1.shp"



.PHONY: euromap basemap merge-countries web-update list clean init compress extract update

COUNTRIES = germany france sweden united_kingdom netherlands denmark austria belgium italy bulgaria greece finland

REMOVE_FROM_WF101 := Netherlands
REMOVE_FROM_OSM := nothing
EXCLUSIVE_COUNTRIES = Germany Austria Denmark Italy Bulgaria "United Kingdom"

AUXILARY = osm wf101 osm+wf101 osm+wf101+emodnet basemap merge euromap

# basemap + merged-countries
euromap: init $(OUTPUT_FOLDER)/euromap.csv

# OSM+WF101+EMODnet
basemap: init $(OUTPUT_FOLDER)/basemap.csv

# All different countries
merge-countries: init $(OUTPUT_FOLDER)/countries.csv

update: web-update remove-euromap-link euromap

web-update:
	cd $(INPUT_FOLDER) && make

remove-euromap-link:
	rm -rf $(OUTPUT_FOLDER)/euromap.csv
	rm -rf $(OUTPUT_FOLDER)/euromap.geojson
	rm -rf euromap.csv
	rm -rf euromap.geojson

compress:
	@echo "=== COMPRESS DATA TO TAR FILE ==="
	rm -f euromap_archive_$(TODAY_STAMP).tar.gz
	tar --exclude Makefile --exclude .gitignore --exclude euromap_archive_*.tar.gz -czvf euromap_archive_$(TODAY_STAMP).tar.gz * 

extract:
	@echo "=== EXTRACT DATA FROM TAR FILE ==="
	tar -xzvf euromap_archive_$(TODAY_STAMP).tar.gz


list:
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$@$$'

clean:
	cd $(OUTPUT_FOLDER) && rm -rf $(COUNTRIES) $(AUXILARY)
	rm -rf $(OUTPUT_FOLDER)/*.csv
	rm -rf $(OUTPUT_FOLDER)/*.geojson
	rm -rf $(OUTPUT_FOLDER)/*.tar.gz


init: $(OUTPUT_FOLDER)/.gitignore
$(OUTPUT_FOLDER)/.gitignore:
	mkdir -p $(OUTPUT_FOLDER)
	@echo "*" > $(OUTPUT_FOLDER)/.gitignore




# =========================

# ==============
# OpenStreetMap
# ==============
OSM_BASENAME:=windturbine_windfarm_locations_osm
OSM_REQ_DATE_STAMP_LATEST:=$(shell ls -v $(INPUT_FOLDER)/osm/$(OSM_BASENAME)_*.overpass_output_windturbine=true_windfarm=true.json | tail -1 | sed -e s/[^0-9]//g)
OSM_REQ_DATE_STAMP_SUCCES:=$(shell ls -v $(INPUT_FOLDER)/osm/$(OSM_BASENAME)_*.csv | tail -1 | sed -e s/[^0-9]//g)
OSM_SUCCES_REQ_OUTPUT_FILE:=$(OSM_BASENAME)_$(OSM_REQ_DATE_STAMP_SUCCES).overpass_output_windturbine=true_windfarm=true.json
OSM_TODAY_FILE_BASE:=$(OSM_BASENAME)_$(TODAY_STAMP)
OSM_TODAY_FILE:=$(OSM_TODAY_FILE_BASE).csv
OSM_TODAY_OUTPUT_FILE:=$(OSM_BASENAME)_$(TODAY_STAMP).overpass_output_windturbine=true_windfarm=true.json

osm: $(OUTPUT_FOLDER)/osm_$(OSM_REQ_DATE_STAMP_SUCCES).csv

$(OUTPUT_FOLDER)/osm.csv: $(OUTPUT_FOLDER)/osm_$(OSM_REQ_DATE_STAMP_SUCCES).csv

$(OUTPUT_FOLDER)/osm_$(OSM_REQ_DATE_STAMP_SUCCES).csv:
	@echo "=== CREATING OSM DATA ==="
	@mkdir -p $(OUTPUT_FOLDER)/osm
	@echo "Latest osm request (queried):    $(OSM_REQ_DATE_STAMP_LATEST)"
	@echo "Latest osm request (successful): $(OSM_REQ_DATE_STAMP_SUCCES)"

	@echo "=== >>> CREATING NEW OSM FILE BASED ON LAST SUCCESFULL REQUEST $(OSM_REQ_DATE_STAMP_SUCCES) (source = $(INPUT_FOLDER)/$(OSM_SUCCES_REQ_OUTPUT_FILE)) <<< ==="
	ln -sf "$(PWD)/$(INPUT_FOLDER)/osm/$(OSM_SUCCES_REQ_OUTPUT_FILE)" "$(OUTPUT_FOLDER)/osm/$(OSM_TODAY_OUTPUT_FILE)"
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm/$(OSM_SUCCES_REQ_OUTPUT_FILE) --type osm_windturbine_windfarm --output $(OUTPUT_FOLDER)/osm/$(OSM_TODAY_FILE) --labels "OSM ($(OSM_REQ_DATE_STAMP_SUCCES))"

	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm/$(OSM_TODAY_FILE) $(EEZ_FILE) $(COUNTRY_BORDER_FILE) --type fix_country_offshore
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm/$(OSM_TODAY_FILE) --type remove_short_distance --min-distance=$(MIN_TURBINE_DIST) --output $(OUTPUT_FOLDER)/osm/osm.csv

	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm/osm.csv --type remove_country --country $(REMOVE_FROM_OSM)

	cp $(OUTPUT_FOLDER)/osm/osm.csv $(OUTPUT_FOLDER)/osm_$(OSM_REQ_DATE_STAMP_SUCCES).csv
	ln -sf "$(PWD)/$(OUTPUT_FOLDER)/osm_$(OSM_REQ_DATE_STAMP_SUCCES).csv" "$(OUTPUT_FOLDER)/osm.csv"


# ==============
# WF101-dataset
# ==============
wf101: $(OUTPUT_FOLDER)/wf101.csv

$(OUTPUT_FOLDER)/wf101.csv:
	@echo "=== >>> CREATING WF101 DATA <<< ==="
	@mkdir -p $(OUTPUT_FOLDER)/wf101
	json2tab --debug=$(DEBUG_LEVEL) --convert $(INPUT_FOLDER)/wf101/wf101.txt --type wf2csv --output $(OUTPUT_FOLDER)/wf101/wf101.csv --labels wf101
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/wf101/wf101.csv --type remove_short_distance --min-distance=$(MIN_TURBINE_DIST)
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/wf101/wf101.csv $(EEZ_FILE) $(COUNTRY_BORDER_FILE) --type fix_country_offshore

	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/wf101/wf101.csv --type remove_country --country $(REMOVE_FROM_WF101)

	cp $(OUTPUT_FOLDER)/wf101/wf101.csv $(OUTPUT_FOLDER)/wf101.csv

OSM_BASENAME:=windturbine_windfarm_locations_osm


osm+wf101: $(OUTPUT_FOLDER)/osm+wf101.csv
$(OUTPUT_FOLDER)/osm+wf101.csv: $(OUTPUT_FOLDER)/osm.csv $(OUTPUT_FOLDER)/wf101.csv
	@echo "=== >>> MERGING OSM+WF101 <<< ==="
	@mkdir -p $(OUTPUT_FOLDER)/osm+wf101
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/osm.csv $(OUTPUT_FOLDER)/wf101.csv --output $(OUTPUT_FOLDER)/osm+wf101/osm+wf101.csv
	cp $(OUTPUT_FOLDER)/osm+wf101/osm+wf101.csv $(OUTPUT_FOLDER)/osm+wf101.csv



EMODNET_TARGET:=osm+wf101
$(OUTPUT_FOLDER)/basemap.csv: $(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet.csv
$(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet.csv: $(OUTPUT_FOLDER)/$(EMODNET_TARGET).csv
	@echo "=== APPLY EMODnet on $(EMODNET_TARGET) ==="
	@mkdir -p $(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/$(EMODNET_TARGET).csv --type select_offshore --output $(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet/$(EMODNET_TARGET)_offshore.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/$(EMODNET_TARGET).csv --type select_onshore  --output $(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet/$(EMODNET_TARGET)_onshore.csv

	json2tab --debug=$(DEBUG_LEVEL) --map $(INPUT_FOLDER)/emodnet/emodnet_windfarms_polygon/windfarmspolyPolygon_flipped.shp $(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet/$(EMODNET_TARGET)_offshore.csv --output $(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet/$(EMODNET_TARGET)+emodnet_offshore.csv --rename-columns POWER_MW=installed_power_mw --map-mode=by_geometry --max-distance=0.01 --merge-mode=enrich_second --labels "EMODnet+$(EMODNET_TARGET)"

	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet/$(EMODNET_TARGET)+emodnet_offshore.csv $(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet/$(EMODNET_TARGET)_onshore.csv --output $(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet/$(EMODNET_TARGET)+emodnet.csv

	cp $(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet/$(EMODNET_TARGET)+emodnet.csv $(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet.csv
	ln -sf "$(PWD)/$(OUTPUT_FOLDER)/$(EMODNET_TARGET)+emodnet.csv" "$(OUTPUT_FOLDER)/basemap.csv"


# ==============
# NETHERLANDS
# ==============
NL_RIVM_REQ_STAMP:=$(shell ls -v $(INPUT_FOLDER)/netherlands/rivm/rivm_*/ | tail -1 | sed -e s/[^0-9]//g)
$(OUTPUT_FOLDER)/netherlands.csv: $(OUTPUT_FOLDER)/netherlands_$(NL_RIVM_REQ_STAMP).csv
netherlands: $(OUTPUT_FOLDER)/netherlands_$(NL_RIVM_REQ_STAMP).csv
$(OUTPUT_FOLDER)/netherlands_$(NL_RIVM_REQ_STAMP).csv:
	@echo "=== CONVERTING COUNTRY INPUT DATA FOR THE NETHERLANDS ==="
	@mkdir -p $(OUTPUT_FOLDER)/netherlands
	json2tab --debug=$(DEBUG_LEVEL) --convert $(INPUT_FOLDER)/netherlands/rivm/rivm_$(NL_RIVM_REQ_STAMP)_windturbines_vermogen/rivm_$(NL_RIVM_REQ_STAMP)_*.shp $(INPUT_FOLDER)/netherlands/rws/rws_windparken_turbines/windparken_turbinesPoint.shp --type netherlands --output $(OUTPUT_FOLDER)/netherlands/netherlands_$(NL_RIVM_REQ_STAMP).csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/netherlands/netherlands_$(NL_RIVM_REQ_STAMP).csv --type csv2csv --write-columns "country=België#->Belgium,country=Nederland#->Netherlands,country=Duitsland#->Germany"

# Note Netherlands RIVM contains some locations in BE and DE
#	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/netherlands/netherlands.csv --type select_country --country Netherlands

	cp $(OUTPUT_FOLDER)/netherlands/netherlands_$(NL_RIVM_REQ_STAMP).csv $(OUTPUT_FOLDER)/netherlands_$(NL_RIVM_REQ_STAMP).csv
	ln -sf "$(PWD)/$(OUTPUT_FOLDER)/netherlands_$(NL_RIVM_REQ_STAMP).csv" "$(OUTPUT_FOLDER)/netherlands.csv"


# ==============
# BELGIUM
# ==============
belgium: $(OUTPUT_FOLDER)/belgium.csv
$(OUTPUT_FOLDER)/belgium.csv:
	@echo "=== CONVERTING COUNTRY INPUT DATA FOR BELGIUM ==="
	@mkdir -p $(OUTPUT_FOLDER)/belgium
	json2tab --debug=$(DEBUG_LEVEL) --convert $(INPUT_FOLDER)/belgium/onshore/er_windturb_st_aangevr.lb72.gpkg --type flanders --min-distance=$(MIN_TURBINE_DIST) --output $(OUTPUT_FOLDER)/belgium/flanders_onshore.csv --labels "Flanders Onshore (Stedenbouwkundig aangevraagde windturbines)"
	json2tab --debug=$(DEBUG_LEVEL) --convert $(INPUT_FOLDER)/belgium/offshore/BELGIUM_OFFSHORE_2024.csv --type csv2csv --output $(OUTPUT_FOLDER)/belgium/belgium_offshore.csv --write-columns source="Belgium Offshore",is_offshore=True,country=Belgium

	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/belgium/flanders_onshore.csv $(OUTPUT_FOLDER)/belgium/belgium_offshore.csv --output $(OUTPUT_FOLDER)/belgium/belgium.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/belgium/belgium.csv --type select_country --country Belgium
	cp $(OUTPUT_FOLDER)/belgium/belgium.csv $(OUTPUT_FOLDER)/belgium.csv



# ==============
# FRANCE
# ==============
france: $(OUTPUT_FOLDER)/france.csv
$(OUTPUT_FOLDER)/france.csv:
	@echo "=== CONVERTING COUNTRY INPUT DATA FOR FRANCE ==="
	@mkdir -p $(OUTPUT_FOLDER)/france
	@echo "TODO"
	@echo "id,turbine_id,name,latitude,longitude,hub_height,power_rating,radius,diameter,manufacturer,type,rated_speed,cut_in_speed,cut_out_speed,height_offset,wind_farm,n_turbines,operator,start_date,end_date,source,is_offshore,country,geometry" >> $(OUTPUT_FOLDER)/france/france.csv
	cp $(OUTPUT_FOLDER)/france/france.csv $(OUTPUT_FOLDER)/france.csv


# ==============
# GERMANY
# ==============
DE_REQ_STAMP:=$(shell ls -dv $(INPUT_FOLDER)/germany/Gesamtdatenexport_*/ | tail -1 | sed -e s/[^0-9]//g)
germany: $(OUTPUT_FOLDER)/germany_$(DE_REQ_STAMP).csv
$(OUTPUT_FOLDER)/germany.csv: $(OUTPUT_FOLDER)/germany_$(DE_REQ_STAMP).csv
$(OUTPUT_FOLDER)/germany_$(DE_REQ_STAMP).csv:
	@echo "=== CONVERTING COUNTRY INPUT DATA FOR GERMANY ==="
	@mkdir -p $(OUTPUT_FOLDER)/germany
	json2tab --debug=$(DEBUG_LEVEL) --convert $(INPUT_FOLDER)/germany/Gesamtdatenexport_$(DE_REQ_STAMP)/EinheitenWind.xml --type germany --output $(OUTPUT_FOLDER)/germany/germany.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/germany/germany.csv $(EEZ_FILE) $(COUNTRY_BORDER_FILE) --type fix_country_offshore
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/germany/germany.csv --type select_country --country Germany

	cp $(OUTPUT_FOLDER)/germany/germany.csv $(OUTPUT_FOLDER)/germany_$(DE_REQ_STAMP).csv
	ln -sf "$(PWD)/$(OUTPUT_FOLDER)/germany_$(DE_REQ_STAMP).csv" "$(OUTPUT_FOLDER)/germany.csv"


# ==============
# DENMARK
# ==============
DNK_REQ_FILE:=$(shell ls -v $(INPUT_FOLDER)/denmark/Vind*.xlsx | tail -1)
DNK_REQ_STAMP:=$(shell echo "$(DNK_REQ_FILE)" | sed -e s/[^0-9]//g)
denmark: $(OUTPUT_FOLDER)/denmark_$(DNK_REQ_STAMP).csv
$(OUTPUT_FOLDER)/denmark.csv: $(OUTPUT_FOLDER)/denmark_$(DNK_REQ_STAMP).csv
$(OUTPUT_FOLDER)/denmark_$(DNK_REQ_STAMP).csv:
	@echo "=== CONVERTING COUNTRY INPUT DATA FOR DENMARK ==="
	@mkdir -p $(OUTPUT_FOLDER)/denmark
	json2tab --debug=$(DEBUG_LEVEL) --convert "$(DNK_REQ_FILE)" --type denmark --output $(OUTPUT_FOLDER)/denmark/denmark_$(DNK_REQ_STAMP).csv --labels "Denmark (Vindmølledata $(DNK_REQ_STAMP))"

	cp $(OUTPUT_FOLDER)/denmark/denmark_$(DNK_REQ_STAMP).csv $(OUTPUT_FOLDER)/denmark_$(DNK_REQ_STAMP).csv
	ln -sf "$(PWD)/$(OUTPUT_FOLDER)/denmark_$(DNK_REQ_STAMP).csv" "$(OUTPUT_FOLDER)/denmark.csv"


# ==============
# AUSTRIA
# ==============
austria: $(OUTPUT_FOLDER)/austria.csv
$(OUTPUT_FOLDER)/austria.csv: $(OUTPUT_FOLDER)/osm.csv $(OUTPUT_FOLDER)/wf101.csv
	@echo "=== CONVERTING COUNTRY INPUT DATA FOR AUSTRIA ==="
	@mkdir -p $(OUTPUT_FOLDER)/austria
	json2tab --debug=$(DEBUG_LEVEL) --convert $(INPUT_FOLDER)/austria/igwindkraft-windrad-karte.json --type austria --output $(OUTPUT_FOLDER)/austria/austria_igwindkraft.csv --labels "Austria (IG Windkraft)"

	@echo "=== BUILD AUSTRIA, ENRICH OSM AUSTRIA DATA WITH WF101 ==="
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/wf101.csv --type select_country --country Austria --output $(OUTPUT_FOLDER)/austria/austria_wf101.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm.csv --type select_country --country Austria --output $(OUTPUT_FOLDER)/austria/austria_osm.csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/austria/austria_osm.csv $(OUTPUT_FOLDER)/austria/austria_wf101.csv --merge-mode enrich_first --output $(OUTPUT_FOLDER)/austria/austria_osm_wf101.csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/austria/austria_igwindkraft.csv $(OUTPUT_FOLDER)/austria/austria_osm_wf101.csv --output $(OUTPUT_FOLDER)/austria/austria.csv

	cp $(OUTPUT_FOLDER)/austria/austria.csv $(OUTPUT_FOLDER)/austria.csv


# ==============
# SWEDEN
# ==============
SE_REQ_STAMP:=$(shell ls -v $(INPUT_FOLDER)/sweden/VBK_export_allman_prod_*.xlsx | tail -1 | sed -e s/[^0-9]//g)
sweden: $(OUTPUT_FOLDER)/sweden_$(SE_REQ_STAMP).csv
$(OUTPUT_FOLDER)/sweden.csv: $(OUTPUT_FOLDER)/sweden_$(SE_REQ_STAMP).csv
$(OUTPUT_FOLDER)/sweden_$(SE_REQ_STAMP).csv:
	@echo "=== CONVERTING COUNTRY INPUT DATA FOR SWEDEN ==="
	@mkdir -p $(OUTPUT_FOLDER)/sweden
	json2tab --debug=$(DEBUG_LEVEL) --convert "$(INPUT_FOLDER)/sweden/VBK_export_allman_prod_$(SE_REQ_STAMP).xlsx" --type sweden --output $(OUTPUT_FOLDER)/sweden/sweden_$(SE_REQ_STAMP).csv --labels "Sweden (VBK export allman prod) #$(SE_REQ_STAMP)"
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/sweden/sweden_$(SE_REQ_STAMP).csv $(EEZ_FILE) $(COUNTRY_BORDER_FILE) --type fix_country_offshore
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/sweden/sweden_$(SE_REQ_STAMP).csv --type select_country --country Sweden

	cp $(OUTPUT_FOLDER)/sweden/sweden_$(SE_REQ_STAMP).csv $(OUTPUT_FOLDER)/sweden_$(SE_REQ_STAMP).csv
	ln -sf "$(PWD)/$(OUTPUT_FOLDER)/sweden_$(SE_REQ_STAMP).csv" "$(OUTPUT_FOLDER)/sweden.csv"


# ==============
# UNITED KINGDOM
# ==============
UK_REQ_FILE:=$(shell ls -v $(INPUT_FOLDER)/united_kingdom/REPD_publication_*.xlsx | tail -1)
UK_REQ_STAMP:=$(shell echo "$(UK_REQ_FILE)" | sed -e s/[^0-9]//g)
UK_REQ_STAMP_FANCY=$(shell echo "$(UK_REQ_STAMP)" | cut -c 1-4)Q$(shell echo "$(UK_REQ_STAMP)" | cut -c 5)

uk: united_kingdom
united_kingdom: $(OUTPUT_FOLDER)/united_kingdom_$(UK_REQ_STAMP_FANCY).csv
$(OUTPUT_FOLDER)/united_kingdom.csv : $(OUTPUT_FOLDER)/united_kingdom_$(UK_REQ_STAMP_FANCY).csv
$(OUTPUT_FOLDER)/united_kingdom_$(UK_REQ_STAMP_FANCY).csv: $(OUTPUT_FOLDER)/osm.csv
	@echo "=== CONVERTING COUNTRY INPUT DATA FOR UNITED KINGDOM ==="
	@mkdir -p $(OUTPUT_FOLDER)/united_kingdom
	json2tab --debug=$(DEBUG_LEVEL) --convert "$(UK_REQ_FILE)" --type uk --output $(OUTPUT_FOLDER)/united_kingdom/uk_windfarms.csv --labels "United Kingdom (REPD publication $(UK_REQ_STAMP_FANCY))"
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/united_kingdom/uk_windfarms.csv --type csv2csv --write-columns "country=United Kingdom"

	@echo "=== BUILD UK, ENRICH WINDFARM DATA WITH OSM DATA ==="
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm.csv --type select_country --country "United Kingdom" --output $(OUTPUT_FOLDER)/united_kingdom/uk_osm.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/united_kingdom/uk_windfarms.csv --type select_offshore --output $(OUTPUT_FOLDER)/united_kingdom/uk_windfarms_offshore.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/united_kingdom/uk_windfarms.csv --type select_onshore --output $(OUTPUT_FOLDER)/united_kingdom/uk_windfarms_onshore.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/united_kingdom/uk_osm.csv --type select_offshore --output $(OUTPUT_FOLDER)/united_kingdom/uk_osm_offshore.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/united_kingdom/uk_osm.csv --type select_onshore --output $(OUTPUT_FOLDER)/united_kingdom/uk_osm_onshore.csv
	json2tab --debug=$(DEBUG_LEVEL) --map $(OUTPUT_FOLDER)/united_kingdom/uk_windfarms_onshore.csv $(OUTPUT_FOLDER)/united_kingdom/uk_osm_onshore.csv --output $(OUTPUT_FOLDER)/united_kingdom/uk_onshore.csv --max-distance=0.01 --merge-mode=enrich_second
	json2tab --debug=$(DEBUG_LEVEL) --map $(OUTPUT_FOLDER)/united_kingdom/uk_windfarms_offshore.csv $(OUTPUT_FOLDER)/united_kingdom/uk_osm_offshore.csv --output $(OUTPUT_FOLDER)/united_kingdom/uk_offshore.csv --max-distance=0.25 --merge-mode=enrich_first
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/united_kingdom/uk_onshore.csv $(OUTPUT_FOLDER)/united_kingdom/uk_offshore.csv --output $(OUTPUT_FOLDER)/united_kingdom/uk_$(UK_REQ_STAMP_FANCY).csv

	cp $(OUTPUT_FOLDER)/united_kingdom/uk_$(UK_REQ_STAMP_FANCY).csv $(OUTPUT_FOLDER)/united_kingdom_$(UK_REQ_STAMP_FANCY).csv
	ln -sf "$(PWD)/$(OUTPUT_FOLDER)/united_kingdom_$(UK_REQ_STAMP_FANCY).csv" "$(OUTPUT_FOLDER)/united_kingdom.csv"


# ==============
# FINLAND
# ==============
FIN_DATA_STAMP=$(shell ls -v $(INPUT_FOLDER)/finland/finland_wind_fleet_data_*.json | tail -1 | sed -e s/[^0-9]//g)
finland: $(OUTPUT_FOLDER)/finland_$(FIN_DATA_STAMP).csv
$(OUTPUT_FOLDER)/finland.csv: $(OUTPUT_FOLDER)/finland_$(FIN_DATA_STAMP).csv
$(OUTPUT_FOLDER)/finland_$(FIN_DATA_STAMP).csv:
	@echo "=== CONVERTING COUNTRY INPUT DATA FOR FINLAND ==="
	@mkdir -p $(OUTPUT_FOLDER)/finland
	json2tab --debug=$(DEBUG_LEVEL) --convert $(INPUT_FOLDER)/finland/finland_wind_fleet_data_$(FIN_DATA_STAMP).json --type finland --output $(OUTPUT_FOLDER)/finland/finland_$(FIN_DATA_STAMP).csv --labels "Finland (FMI)"

	cp $(OUTPUT_FOLDER)/finland/finland_$(FIN_DATA_STAMP).csv $(OUTPUT_FOLDER)/finland_$(FIN_DATA_STAMP).csv
	ln -sf "$(PWD)/$(OUTPUT_FOLDER)/finland/finland_$(FIN_DATA_STAMP).csv" "$(OUTPUT_FOLDER)/finland.csv"


# ==============
# ITALY
# ==============
italy: $(OUTPUT_FOLDER)/italy.csv
$(OUTPUT_FOLDER)/italy.csv: $(OUTPUT_FOLDER)/wf101.csv $(OUTPUT_FOLDER)/osm.csv
	@echo "=== CONVERTING COUNTRY INPUT DATA FOR ITALY ==="
	@mkdir -p $(OUTPUT_FOLDER)/italy
	json2tab --debug=$(DEBUG_LEVEL) --convert $(INPUT_FOLDER)/italy/Italian_Wind_Farms_db.xlsx --type italy --output $(OUTPUT_FOLDER)/italy/italy_windfarms.csv --labels "Italy (ItalianWindFarmsDB 20250513)"
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/italy/italy_windfarms.csv $(EEZ_FILE) $(COUNTRY_BORDER_FILE) --type fix_country_offshore

	@echo "=== BUILD ITALY, ENRICH OSM+WF101 DATA WITH WINDFARM DATA ==="
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm.csv --type select_country --country Italy --output $(OUTPUT_FOLDER)/italy/italy_osm.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/wf101.csv --type select_country --country Italy --output $(OUTPUT_FOLDER)/italy/italy_wf101.csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/italy/italy_osm.csv $(OUTPUT_FOLDER)/italy/italy_wf101.csv --output $(OUTPUT_FOLDER)/italy/italy_osm+wf101.csv
	json2tab --debug=$(DEBUG_LEVEL) --map $(OUTPUT_FOLDER)/italy/italy_windfarms.csv $(OUTPUT_FOLDER)/italy/italy_osm+wf101.csv --output $(OUTPUT_FOLDER)/italy/italy.csv
	
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/italy/italy.csv --type select_country --country Italy

	cp $(OUTPUT_FOLDER)/italy/italy.csv $(OUTPUT_FOLDER)/italy.csv


# ==============
# BULGARIA
# ==============
bulgaria: $(OUTPUT_FOLDER)/bulgaria.csv
$(OUTPUT_FOLDER)/bulgaria.csv: $(OUTPUT_FOLDER)/osm.csv
	@echo "=== CONVERTING COUNTRY INPUT DATA FOR BULGARIA ==="
	@mkdir -p $(OUTPUT_FOLDER)/bulgaria
	json2tab --debug=$(DEBUG_LEVEL) --convert $(INPUT_FOLDER)/bulgaria/bulgarian_wind_farms_combined.csv --type csv2csv --output $(OUTPUT_FOLDER)/bulgaria/bulgarian_windfarms.csv --rename-columns power_kw=installed_power
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/bulgaria/bulgarian_windfarms.csv $(EEZ_FILE) $(COUNTRY_BORDER_FILE) --type fix_country_offshore

	@echo "=== BUILD BULGARIA, ENRICH OSM DATA WITH WINDFARM DATA ==="
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm.csv --type select_country --country Bulgaria --output $(OUTPUT_FOLDER)/bulgaria/bulgaria_osm.csv
	json2tab --debug=$(DEBUG_LEVEL) --map $(OUTPUT_FOLDER)/bulgaria/bulgarian_windfarms.csv $(OUTPUT_FOLDER)/bulgaria/bulgaria_osm.csv --output $(OUTPUT_FOLDER)/bulgaria/bulgaria.csv

	cp $(OUTPUT_FOLDER)/bulgaria/bulgaria.csv $(OUTPUT_FOLDER)/bulgaria.csv


# ==============
# GREECE
# ==============
GR_REQ_STAMP:=$(shell ls -v $(INPUT_FOLDER)/greece/features_*.geojson | tail -1 | sed -e s/[^0-9]//g)
greece: $(OUTPUT_FOLDER)/greece_$(GR_REQ_STAMP).csv
$(OUTPUT_FOLDER)/greece.csv: $(OUTPUT_FOLDER)/greece_$(GR_REQ_STAMP).csv
$(OUTPUT_FOLDER)/greece_$(GR_REQ_STAMP).csv: $(OUTPUT_FOLDER)/osm.csv
	@echo "=== CONVERTING COUNTRY INPUT DATA FOR GREECE ==="
	@mkdir -p $(OUTPUT_FOLDER)/greece
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/osm.csv --type select_country --country "Greece" --output $(OUTPUT_FOLDER)/greece/greece_osm.csv
	json2tab --debug=$(DEBUG_LEVEL) --convert "$(INPUT_FOLDER)/greece/features_$(GR_REQ_STAMP).geojson" $(OUTPUT_FOLDER)/greece/greece_osm.csv --type greece --output $(OUTPUT_FOLDER)/greece/greece_$(GR_REQ_STAMP).csv --labels "Greece (Eletaen $(GR_REQ_STAMP))"

	cp $(OUTPUT_FOLDER)/greece/greece_$(GR_REQ_STAMP).csv $(OUTPUT_FOLDER)/greece_$(GR_REQ_STAMP).csv
	ln -sf "$(PWD)/$(OUTPUT_FOLDER)/greece/greece_$(GR_REQ_STAMP).csv" "$(OUTPUT_FOLDER)/greece.csv"



$(OUTPUT_FOLDER)/euromap.csv: $(OUTPUT_FOLDER)/basemap.csv $(OUTPUT_FOLDER)/countries.csv
	@echo "=== MERGING EUROPE MAPS (W/O COUNTRY EXCLUSIVE DATA) ==="
	@mkdir -p $(OUTPUT_FOLDER)/euromap
	json2tab --debug=$(DEBUG_LEVEL) --convert $(OUTPUT_FOLDER)/basemap.csv --type remove_country --country $(EXCLUSIVE_COUNTRIES) --output $(OUTPUT_FOLDER)/euromap/basemap_wo_exclusive_countries.csv

	json2tab --debug=$(DEBUG_LEVEL) --merge $(OUTPUT_FOLDER)/countries.csv $(OUTPUT_FOLDER)/euromap/basemap_wo_exclusive_countries.csv --output $(OUTPUT_FOLDER)/euromap/euromap_$(TODAY_STAMP).[csv,geojson]

	cp $(OUTPUT_FOLDER)/euromap/euromap_$(TODAY_STAMP).csv $(OUTPUT_FOLDER)/euromap_$(TODAY_STAMP).csv
	cp $(OUTPUT_FOLDER)/euromap/euromap_$(TODAY_STAMP).geojson $(OUTPUT_FOLDER)/euromap_$(TODAY_STAMP).geojson
	ln -sf "$(PWD)/$(OUTPUT_FOLDER)/euromap_$(TODAY_STAMP).csv" "$(OUTPUT_FOLDER)/euromap.csv"
	ln -sf "$(PWD)/$(OUTPUT_FOLDER)/euromap_$(TODAY_STAMP).geojson" "$(OUTPUT_FOLDER)/euromap.geojson"

	cp $(OUTPUT_FOLDER)/euromap/euromap_$(TODAY_STAMP).csv euromap_$(TODAY_STAMP).csv
	cp $(OUTPUT_FOLDER)/euromap/euromap_$(TODAY_STAMP).geojson euromap_$(TODAY_STAMP).geojson
	ln -sf "$(PWD)/euromap_$(TODAY_STAMP).csv" euromap.csv
	ln -sf "$(PWD)/euromap_$(TODAY_STAMP).geojson" euromap.geojson


	@echo "=== COMPRESS DATABASE TO TAR FILE ==="
	cd $(OUTPUT_FOLDER) && tar -czvf euromap_$(TODAY_STAMP).tar.gz euromap_$(TODAY_STAMP).csv euromap_$(TODAY_STAMP).geojson



# ==============
# MERGING
# ==============
C1:=netherlands
C2:=belgium
S1:=$(C1)+$(C2)
$(OUTPUT_FOLDER)/merge/$(S1).csv: $(OUTPUT_FOLDER)/$(C1).csv $(OUTPUT_FOLDER)/$(C2).csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $^ --output $@

C1:=germany
C2:=austria
S2:=$(C1)+$(C2)
$(OUTPUT_FOLDER)/merge/$(S2).csv: $(OUTPUT_FOLDER)/$(C1).csv $(OUTPUT_FOLDER)/$(C2).csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $^ --output $@

C1:=denmark
C2:=united_kingdom
S3:=$(C1)+$(C2)
$(OUTPUT_FOLDER)/merge/$(S3).csv: $(OUTPUT_FOLDER)/$(C1).csv $(OUTPUT_FOLDER)/$(C2).csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $^ --output $@

C1:=sweden
C2:=finland
S4:=$(C1)+$(C2)
$(OUTPUT_FOLDER)/merge/$(S4).csv: $(OUTPUT_FOLDER)/$(C1).csv $(OUTPUT_FOLDER)/$(C2).csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $^ --output $@

C1:=italy
C2:=greece
S5:=$(C1)+$(C2)
$(OUTPUT_FOLDER)/merge/$(S5).csv: $(OUTPUT_FOLDER)/$(C1).csv $(OUTPUT_FOLDER)/$(C2).csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $^ --output $@

C1:=france
C2:=bulgaria
S6:=$(C1)+$(C2)
$(OUTPUT_FOLDER)/merge/$(S6).csv: $(OUTPUT_FOLDER)/$(C1).csv $(OUTPUT_FOLDER)/$(C2).csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $^ --output $@

T1:=$(S1)+$(S2)
T2:=$(S3)+$(S4)
T3:=$(S5)+$(S6)

U1:=$(T1)+$(T2)
FINAL:=$(U1)+$(T3)

$(OUTPUT_FOLDER)/merge/$(T1).csv: $(OUTPUT_FOLDER)/merge/$(S1).csv $(OUTPUT_FOLDER)/merge/$(S2).csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $^ --output $@
$(OUTPUT_FOLDER)/merge/$(T2).csv: $(OUTPUT_FOLDER)/merge/$(S3).csv $(OUTPUT_FOLDER)/merge/$(S4).csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $^ --output $@
$(OUTPUT_FOLDER)/merge/$(T3).csv: $(OUTPUT_FOLDER)/merge/$(S5).csv $(OUTPUT_FOLDER)/merge/$(S6).csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $^ --output $@
$(OUTPUT_FOLDER)/merge/$(U1).csv: $(OUTPUT_FOLDER)/merge/$(T1).csv $(OUTPUT_FOLDER)/merge/$(T2).csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $^ --output $@
$(OUTPUT_FOLDER)/merge/$(FINAL).csv: $(OUTPUT_FOLDER)/merge/$(U1).csv $(OUTPUT_FOLDER)/merge/$(T3).csv
	json2tab --debug=$(DEBUG_LEVEL) --merge $^ --output $@

$(OUTPUT_FOLDER)/merge:
	@echo "=== START MERGING COUNTRY DATA ==="
	@mkdir -p $(OUTPUT_FOLDER)/merge

$(OUTPUT_FOLDER)/countries.csv: $(OUTPUT_FOLDER)/merge $(OUTPUT_FOLDER)/merge/$(FINAL).csv
	cp $(OUTPUT_FOLDER)/merge/$(FINAL).csv $(OUTPUT_FOLDER)/countries.csv
