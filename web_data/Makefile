TODAY_STAMP:=$(shell date +%Y%m%d)
TODAY_YEAR:=$(shell date +%Y)
TODAY_QUARTER:=$(shell date +%q)


# Germany MaStR daten version (see https://www.marktstammdatenregister.de/MaStR/Datendownload or https://www.marktstammdatenregister.de/MaStRHilfe/subpages/releasenotes.html for latest version)
GERMANY_DATEN_VERSION=$(shell python -c "from gen_mastr_version import gen_mastr_version; print(gen_mastr_version())")

.PHONY: all list clean compress extract

DAILY_COUNTRIES = germany france sweden united_kingdom netherlands
STATIC_COUNTRIES = denmark austria belgium italy bulgaria
MANUAL_COUNTRIES = greece finland
MULTI_COUNTRY = osm wf101 emodnet

META_DATA = turbine_database worldmap

all: $(DAILY_COUNTRIES) $(STATIC_COUNTRIES) $(MANUAL_COUNTRIES) $(MULTI_COUNTRY)

list:
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$@$$'

clean:
	rm -rf $(DAILY_COUNTRIES)
	rm -rf $(STATIC_COUNTRIES)
	rm -rf $(MANUAL_COUNTRIES)
	rm -rf $(MULTI_COUNTRY)

compress:
	@echo "=== COMPRESS DATA TO TAR FILE ==="
	rm -f web_data_archive_$(TODAY_STAMP).tar.gz
	tar --exclude Makefile --exclude .gitignore --exclude web_data_archive_*.tar.gz -czvf web_data_archive_$(TODAY_STAMP).tar.gz * 

extract:
	@echo "=== EXTRACT DATA FROM TAR FILE ==="
	tar -xzvf web_data_archive_$(TODAY_STAMP).tar.gz


austria:
	@echo """=== AUSTRIA ==="
	@mkdir -p austria/
	wget https://www.igwindkraft.at/aktuelles/windrad-karte -O austria/windrad-karte.html
	grep -oP "wheels='.*'" austria/windrad-karte.html | cut -c 9- | rev | cut -c 2- | rev > austria/windrad-karte.wheels
	cat austria/windrad-karte.wheels | python3 -m json.tool > austria/igwindkraft-windrad-karte.json

belgium: belgium/onshore belgium/offshore

belgium/onshore:
	@echo """=== BELGIUM/ONSHORE ==="
	@mkdir -p belgium/onshore
	wget https://dataplatform.omgeving.vlaanderen.be/public/mercatornet/er_windturb_st_aangevr -O belgium/onshore/er_windturb_st_aangevr.zip
	unzip -j belgium/onshore/er_windturb_st_aangevr.zip -d belgium/onshore

belgium/offshore: belgium/offshore/BELGIUM_OFFSHORE_2024.csv

belgium/offshore/BELGIUM_OFFSHORE_2024.csv:
	@echo """=== BELGIUM/OFFSHORE ==="
	@rm -rf belgium/offshore/repo
	@mkdir -p belgium/offshore/repo
	git clone --depth 1 git@github.com:destination-earth-digital-twins/nwp2windpower.git belgium/offshore/repo
	mv belgium/offshore/repo/METADATA/UseCase/BELGIUM_OFFSHORE*.csv belgium/offshore/
	rm -rf belgium/offshore/repo/

germany: germany/Gesamtdatenexport_$(TODAY_STAMP)/EinheitenWind.xml

germany/Gesamtdatenexport_$(TODAY_STAMP)/EinheitenWind.xml:
	@echo """=== GERMANY ==="
	@mkdir -p germany/
	wget https://download.marktstammdatenregister.de/Gesamtdatenexport_$(TODAY_STAMP)_$(GERMANY_DATEN_VERSION).zip -O germany/Gesamtdatenexport_$(TODAY_STAMP)_$(GERMANY_DATEN_VERSION).zip
	unzip -j germany/Gesamtdatenexport_$(TODAY_STAMP)_$(GERMANY_DATEN_VERSION).zip EinheitenWind.xml Katalogwerte.xml -d germany/Gesamtdatenexport_$(TODAY_STAMP)
	rm germany/Gesamtdatenexport_$(TODAY_STAMP)_$(GERMANY_DATEN_VERSION).zip


denmark/data-oversigt-over-energisektoren.html:
	@echo """=== DENMARK ==="
	@mkdir -p denmark/
	wget --prefer-family=IPv4 "https://ens.dk/analyser-og-statistik/data-oversigt-over-energisektoren" -O "denmark/data-oversigt-over-energisektoren.html"

denmark: denmark/data-oversigt-over-energisektoren.html
	@touch denmark
	cd denmark && wget "https://ens.dk$(shell grep -o 'href=.*>Data for eksisterende og afmeldte anlæg' denmark/data-oversigt-over-energisektoren.html | grep -o '/.*/download')" --content-disposition

france: france/windturbines_$(TODAY_STAMP).csv

france/windturbines_$(TODAY_STAMP).csv:
	@echo """=== FRANCE ==="
	@mkdir -p france/
	wget "https://georisques.gouv.fr/services?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:eolienne_wfs&SRSNAME=urn:ogc:def:crs:EPSG::3857&OUTPUTFORMAT=CSV" -O france/windturbines_$(TODAY_STAMP).csv


netherlands: netherlands/rws netherlands/rivm
	@touch netherlands

netherlands/rws:
	@echo """=== NETHERLANDS/RWS ==="
	@mkdir -p netherlands/rws
	wget "https://geo.rijkswaterstaat.nl/services/ogc/gdr/windenergiegebieden/ows?service=WFS&version=2.0.0&request=GetFeature&typeName=windparken_turbines&outputFormat=SHAPE-ZIP" -O netherlands/rws/rws_windparken_turbines.zip
	unzip netherlands/rws/rws_windparken_turbines.zip -d netherlands/rws/rws_windparken_turbines


netherlands/rivm: netherlands/rivm/rivm_$(TODAY_YEAR)0101_windturbines_vermogen/rivm_$(TODAY_YEAR)0101_windturbines_vermogen.shp

netherlands/rivm/rivm_$(TODAY_YEAR)0101_windturbines_vermogen/rivm_$(TODAY_YEAR)0101_windturbines_vermogen.shp:
	@echo """=== NETHERLANDS/RIVM ==="
	@mkdir -p netherlands/rivm
	wget --prefer-family=IPv4 "https://data.rivm.nl/geo/alo/wfs?service=WFS&version=2.0.0&request=GetFeature&typeName=alo:rivm_$(TODAY_YEAR)0101_windturbines_vermogen&outputFormat=SHAPE-ZIP" -O netherlands/rivm/rivm_$(TODAY_YEAR)0101_windturbines_vermogen.zip
	unzip netherlands/rivm/rivm_$(TODAY_YEAR)0101_windturbines_vermogen.zip -d netherlands/rivm/rivm_$(TODAY_YEAR)0101_windturbines_vermogen
	@touch netherlands/rivm/rivm_$(TODAY_YEAR)0101_windturbines_vermogen/rivm_$(TODAY_YEAR)0101_windturbines_vermogen.shp


sweden: sweden/VBK_export_allman_prod_$(TODAY_STAMP).xlsx
sweden/VBK_export_allman_prod_$(TODAY_STAMP).xlsx:
	@echo """=== SWEDEN ==="
	@mkdir -p sweden
	wget "https://ext-dokument.lansstyrelsen.se/Gemensamt/Geodata/Externa%20dokument/VBK/VBK_export_allman_prod.xlsx" -O sweden/VBK_export_allman_prod_$(TODAY_STAMP).xlsx



# Compute quarter and year to fetch for united kingdom data set
QUERY_QUARTER:=$(shell expr $(TODAY_QUARTER) - 1)
ifeq ($(QUERY_QUARTER), 0)
	QUERY_QUARTER:=4
	QUERY_YEAR:=$(shell expr $(TODAY_YEAR) - 1)
else
	QUERY_YEAR:=$(TODAY_YEAR)
endif

UK_HTML_FILE:=united_kingdom/REPD_extract_$(TODAY_YEAR)_Q$(TODAY_QUARTER).html
$(UK_HTML_FILE):
	@echo """=== UNITED KINGDOM ==="
	@mkdir -p united_kingdom
	wget --prefer-family=IPv4 "https://www.gov.uk/government/publications/renewable-energy-planning-database-quarterly-extract" -O $(UK_HTML_FILE)
	
united_kingdom: $(UK_HTML_FILE)
	cd united_kingdom && wget --prefer-family=IPv4 "$(shell grep -o 'https://.*.xlsx' $(UK_HTML_FILE) | head -n 1)"
#	Delete html-file to contunue fetching RERD-page to get new data when available
	@if [ -f united_kingdom/REPD_publication_Q$(QUERY_QUARTER)_$(QUERY_YEAR).xlsx ]; then mv united_kingdom/REPD_publication_Q$(QUERY_QUARTER)_$(QUERY_YEAR).xlsx united_kingdom/REPD_publication_$(QUERY_YEAR)_Q$(QUERY_QUARTER).xlsx; else rm $(UK_HTML_FILE); fi

italy:
	@echo """=== ITALY ==="
	@mkdir -p italy
	wget --prefer-family=IPv4 https://github.com/lacconito/Wind_turbine_onshore_IT_db/raw/refs/heads/main/Italian_Wind_Farms_db.xlsx -O italy/Italian_Wind_Farms_db.xlsx

greece: greece/features_$(TODAY_STAMP).geojson

greece/features_$(TODAY_STAMP).geojson:
	@echo """=== GREECE ==="
	@mkdir -p greece
	@echo "# Instructions to manually download (new) GeoJSON data for Greece" > greece/README.md
	@echo "1. Visit https://eletaen.maps.arcgis.com/apps/webappviewer/index.html?id=875b7ea838cf4fe6a937c4be90fa8edd&extent=2070592.4486%2C4027438.181%2C3489263.6936%2C5196618.9657%2C102100" >> greece/README.md
	@echo "2. Query all turbine locations." >> greece/README.md
	@echo "3. Export output to GeoJSON." >> greece/README.md
	@echo "4. Save the output to $(PWD)/greece/features_$(TODAY_STAMP).geojson" >> greece/README.md
	@cat greece/README.md

bulgaria: bulgaria/bulgarian_wind_farms_combined.csv
bulgaria/bulgarian_wind_farms_combined.csv:
	@echo """=== BULGARIA ==="
	@mkdir -p bulgaria
	cd bulgaria && wget https://drive.google.com/uc?id=10I3J96tD4LD2n-CtByW5Tiu3I9gYMwUi --content-disposition

finland:
	@echo """=== FINLAND ==="
	@mkdir -p finland
	@echo "TODO: copy static data for Finland" > finland/TODO.md
	@cat finland/TODO.md



# OpenStreetMap data handling
OSM_BASENAME:=windturbine_windfarm_locations_osm
OSM_TODAY_FILE_BASE:=$(OSM_BASENAME)_$(TODAY_STAMP)
OSM_TODAY_FILE:=$(OSM_TODAY_FILE_BASE).csv
OSM_REQ_OUTPUT_FILE:=$(OSM_TODAY_FILE_BASE).overpass_output_windturbine=true_windfarm=true.json

#OVERPASS_API_URL:=https://overpass-api.de/api/interpreter
OVERPASS_API_URL:=https://overpass.private.coffee/api/interpreter
#OVERPASS_API_URL:=https://localhost/api/interpreter

osm: osm/$(OSM_TODAY_FILE)
osm/$(OSM_TODAY_FILE):
	@echo """=== OpenStreetMap ==="
	@mkdir -p osm
	@rm -f osm/$(OSM_REQ_OUTPUT_FILE)
	json2tab --debug=3 --fetch-osm-data "osm/$(OSM_TODAY_FILE)" --overpass-url $(OVERPASS_API_URL)



emodnet: emodnet/emodnet_windfarms_polygon/windfarmspolyPolygon_flipped.shp

emodnet/emodnet_windfarms_polygon.zip:
	@echo """=== EMODnet (WFS-based) ==="
	@mkdir -p emodnet
	wget --prefer-family=IPv4 "https://ows.emodnet-humanactivities.eu/wfs?service=WFS&version=2.0.0&request=GetFeature&typeName=emodnet:windfarmspoly&outputFormat=SHAPE-ZIP" -O emodnet/emodnet_windfarms_polygon.zip

emodnet/EMODnet_HA_Energy_WindFarms_20260127.zip:
	@echo """=== EMODnet (EMODnet_HA_Energy_WindFarms_20260127-based) ==="
	@mkdir -p emodnet
	cd emodnet && wget --prefer-family=IPv4 https://ows.emodnet-humanactivities.eu/geonetwork/srv/api/records/8201070b-4b0b-4d54-8910-abcea5dce57f/attachments/EMODnet_HA_Energy_WindFarms_20260127.zip --content-disposition

emodnet/emodnet_windfarms_polygon/windfarmspolyPolygon.shp: emodnet/emodnet_windfarms_polygon.zip
	unzip -j emodnet/emodnet_windfarms_polygon.zip -d emodnet/emodnet_windfarms_polygon
	@touch emodnet/emodnet_windfarms_polygon/windfarmspolyPolygon.shp

emodnet/emodnet_windfarms_polygon/windfarmspolyPolygon_flipped.shp: emodnet/emodnet_windfarms_polygon/windfarmspolyPolygon.shp
# 	Flip lan/lon as they are wrongly encoded in the WFS output (but not in the zip-package)
	@python -c "import geopandas as gpd; from shapely.ops import transform as T; f = 'emodnet/emodnet_windfarms_polygon/windfarmspolyPolygon'; gdf = gpd.read_file(f'{f}.shp'); gdf['geometry'] = gdf['geometry'].map(lambda p: T(lambda x, y: (y, x), p)); gdf.to_file(f'{f}_flipped.shp'); print(f'lat/lon converted to expected order for file {f}.shp.')"


wf101: wf101/wf101.txt
wf101/wf101.txt:
	@echo """=== WF101 ==="
	@mkdir -p wf101
	@rm -rf wf101/repo
	git clone --depth 1 --no-checkout git@github.com:destination-earth-digital-twins/DE330_WP8-Wind.git wf101/repo
	cd wf101/repo && git sparse-checkout init && git sparse-checkout set data/WFP_input && git checkout main  -- "*.txt"
	rm -rf wf101/repo/.git
	mv wf101/repo/data/WFP_input/wf101.txt wf101/wf101.txt
	rm -rf wf101/repo/

