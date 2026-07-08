all: turbine_database worldmap

.PHONY: all list compress extract

list:
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$@$$'

TODAY_STAMP:=$(shell date +%Y%m%d)

compress:
	@echo "=== COMPRESS DATA TO TAR FILE ==="
	rm -f static_data_archive_$(TODAY_STAMP).tar.gz
	tar --exclude Makefile --exclude .gitignore --exclude *.tgz --exclude "worldmap/eez/EEZ_land_union_v4_202410.zip"  --exclude "worldmap/country_borders/World Bank Official Boundaries - Admin *.zip" -czvf static_data_archive_$(TODAY_STAMP).tar.gz * 

extract:
	@echo "=== EXTRACT DATA FROM TAR FILE ==="
	tar -xzvf static_data_archive_$(TODAY_STAMP).tar.gz


turbine_database: turbine_database+gened_ct_curves.json

turbine_database+gened_ct_curves.json:
	wget --prefer-family=IPv4 -O turbine_database+gened_ct_curves.json "https://drive.usercontent.google.com/download?export=download&id=19We1qP3inHrx3D_tbb6fpn0nJOEI_n97&confirm=t" --content-disposition

worldmap: worldmap/country_borders/WB_GAD_ADM0.shp worldmap/eez

# Worldmap data from: https://datacatalog.worldbank.org/search/dataset/0038272/world-bank-official-boundaries
DATASET_ID:=0038272
DOC_ID:=DR0095371
VERSION:=2
WORLDMAP_URL:=https://datacatalogfiles.worldbank.org/ddh-published/$(DATASET_ID)/$(VERSION)/$(DOC_ID)/World Bank Official Boundaries (Shapefiles)

FILENAME0:=World Bank Official Boundaries - Admin 0.zip
worldmap/country_borders/WB_GAD_ADM0.shp:
	@mkdir -p worldmap/country_borders
	cd worldmap/country_borders && wget --prefer-family=IPv4 "$(WORLDMAP_URL)/$(FILENAME0)"
	cd worldmap/country_borders && unzip "$(FILENAME0)"

FILENAME1=World Bank Official Boundaries - Admin 1.zip
worldmap/country_borders/WB_GAD_ADM1.shp:
	@mkdir -p worldmap/country_borders
	cd worldmap/country_borders && wget --prefer-family=IPv4 "$(WORLDMAP_URL)/$(FILENAME1)"
	cd worldmap/country_borders && unzip "$(FILENAME1)"

FILENAME2=World Bank Official Boundaries - Admin 2.zip
worldmap/country_borders/WB_GAD_ADM2.shp:
	@mkdir -p worldmap/country_borders
	cd worldmap/country_borders && wget --prefer-family=IPv4 "$(WORLDMAP_URL)/$(FILENAME2)"
	cd worldmap/country_borders && unzip "$(FILENAME2)"


worldmap/netherlands: worldmap/netherlands/gadm41_NLD.gpkg

worldmap/netherlands/gadm41_NLD.gpkg:
	@mkdir -p worldmap/netherlands
	cd worldmap/netherlands && wget https://geodata.ucdavis.edu/gadm/gadm4.1/gpkg/gadm41_NLD.gpkg
	@python -c "import geopandas as gpd; gdf = gpd.read_file('worldmap/netherlands/gadm41_NLD.gpkg', layer='ADM_ADM_1'); gdf.loc[gdf['GID_1'] == 'NLD.14_1', ['NAME_1', 'TYPE_1', 'ISO_1']] = ['Zuid-Holland', 'Provincie', 'NL-ZH']; gdf.to_file('worldmap/netherlands/gadm41_NLD.gpkg', layer='ADM_ADM_1', driver='GPKG'); print('Fixed missing data for Zuid-Holland')"

worldmap/eez/EEZ_land_union_v4_202410.zip:
	@mkdir -p worldmap/eez

	@echo ""
	@echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
	@echo "!!!                  INSTRUCTIONS TO CONTUNUE                       !!!"
	@echo "!!! vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv !!!"
	@echo "!!! Automatic download will fail due to the need to accept licence. !!!"
	@echo "!!! Please visit                                                    !!!"
	@echo "!!! www.marineregions.org/download_file.php?name=EEZ_land_union_v4_202410.zip !!!"
	@echo "!!! and save the zip-file in folder $(PWD)/worldmap/eez/ !!!"
	@echo "!!! ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ !!!"
	@echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
	@echo ""

	cd worldmap/eez && wget www.marineregions.org/download_file.php?name=EEZ_land_union_v4_202410.zip

worldmap/eez/EEZ_land_union_v4_202410.shp: worldmap/eez/EEZ_land_union_v4_202410.zip
	cd worldmap/eez && unzip -j EEZ_land_union_v4_202410.zip
	@touch worldmap/eez/EEZ_land_union_v4_202410.shp


worldmap/eez: worldmap/eez/EEZ_land_union_v4_202410.shp