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
	json2tab --debug=3 --fetch-osm-data "static_data/turbine_locations_osm_$(shell date +%Y%m%d).[csv,geojson]"

osm_turbines_local:
	./run_overpass_query.sh db_2022 static_data/query_windturbines.overpass static_data/turbine_locations_osm_20220101.local.overpass_output.json
	json2tab --debug=3 --convert static_data/turbine_locations_osm_20220101.local.overpass_output.json --type osm --output static_data/turbine_locations_osm_20220101.csv

convert_osm_20251210: static_data/turbine_locations_osm_20251210.overpass_output.json
	rm -f static_data/turbine_locations_osm_20251210.csv
	json2tab --debug=3 --convert static_data/turbine_locations_osm_20251210.overpass_output.json --type osm --output static_data/turbine_locations_osm_20251210.csv

convert_osm_today: static_data/turbine_locations_osm_$(shell date +%Y%m%d).overpass_output.json
	rm -f static_data/turbine_locations_osm_$(shell date +%Y%m%d).csv
	json2tab --debug=3 --convert static_data/turbine_locations_osm_$(shell date +%Y%m%d).overpass_output.json --type osm --output static_data/turbine_locations_osm_$(shell date +%Y%m%d).csv


master_geojson_012025:
	json2tab --debug=3 --wind-turbine-location-merger 012025

master_geojson_20220101:
	json2tab --debug=3 --wind-turbine-location-merger 20220101

convert_netherlands:
	json2tab --debug=3 --convert ms_data/nl/rivm_20250101_windturbines_vermogen/rivm_20250101_windturbines_vermogen.shp ms_data/nl/rws_20240101_windparken_turbines/windparken_turbinesPoint.shp --type netherlands --output static_data/netherlands_rivm+rws.geojson

convert_denmark:
	json2tab --debug=3 --convert "ms_data/dnk/Vindmølledata til 2025-01.xlsx" --type denmark --output static_data/denmark.csv
	json2tab --debug=3 --convert static_data/denmark.csv --type csv2geojson

convert_flanders:
	json2tab --debug=3 --convert ms_data/be/er_windturb_st_aangevr/er_windturb_st_aangevr.shp --type flanders --output static_data/flanders_onshore.geojson

convert_wf101:
	json2tab --debug=3 --convert ms_data/wf101.txt --type wf2csv --output static_data/wf101.csv
	json2tab --debug=3 --convert static_data/wf101.csv --type remove_duplicates --output static_data/wf101_wo_duplicates.csv
	json2tab --debug=3 --convert static_data/wf101_wo_duplicates.csv --type csv2geojson

merge_flanders_belgium:
	json2tab --debug=3 --merge static_data/flanders_onshore.csv gdrive_data/belgian_offshore_with_types.csv --labels N/A "Belgium Offshore" --output static_data/belgium.csv

merge_osm_netherlands:
	json2tab --debug=3 --merge static_data/turbine_locations_osm_20251110.csv static_data/netherlands_rivm+rws.csv --output static_data/osm+netherlands.csv

fix_country:
	json2tab --debug=2 --convert generated_database/belgium_tmp*.csv static_data/worldmap/EEZ/EEZ_land_union_v4_202410.shp static_data/worldmap/country_borders/countries.geojson --type fix_country_offshore

select_country:
	json2tab --debug=2 --convert generated_database/netherlands.csv --type select_country --country Netherlands Belgium Germany --output generated_database/netherlands_only.csv

remove_country:
	json2tab --debug=2 --convert generated_database/osm.csv --type remove_country --country Germany --output generated_database/osm_wo_germany.csv

igwindkraft_web:
	json2tab --debug=3 --convert https://www.igwindkraft.at/aktuelles/windrad-karte --type austria --output generated_database/austria.csv

igwindkraft_from_file:
	json2tab --debug=3 --convert ms_data/at/igwindkraft-windrad-karte.json --type austria --output generated_database/austria.csv

austria:
	json2tab --debug=2 --convert ms_data/at/igwindkraft-windrad-karte.json --type austria --output generated_database/austria_igwindkraft.csv
	json2tab --debug=2 --convert generated_database/wf101.csv --type select_country --country Austria --output generated_database/austria_wf101.csv
	json2tab --debug=2 --convert generated_database/osm.csv --type select_country --country Austria --output generated_database/austria_osm.csv
	json2tab --debug=3 --merge generated_database/austria_igwindkraft.csv generated_database/austria_osm.csv --output generated_database/austria_igwindkraft+osm.csv
	json2tab --debug=3 --merge generated_database/austria_igwindkraft.csv generated_database/austria_wf101.csv --output generated_database/austria_igwindkraft+wf101.csv


location_database:
	rm -rf generated_database
	mkdir generated_database
	echo "*" > generated_database/.gitignore
	echo "=== CONVERTING EUROPE-WIDE INPUT DATA ==="
	json2tab --debug=2 --convert static_data/turbine_locations_osm_20251210.overpass_output.json --type osm --output generated_database/osm.csv
	json2tab --debug=2 --convert ms_data/wf101.txt --type wf2csv --output generated_database/wf101.csv
#	json2tab --debug=2 --convert static_data/turbine_locations_osm_20250101.overpass_output.json --type osm --output generated_database/osm.csv
#	json2tab --debug=2 --convert gdrive_data/wf101.txt --type wf2csv --output generated_database/wf101.csv
	json2tab --debug=2 --convert generated_database/wf101.csv --type remove_duplicates
	
	echo "=== CONVERTING MEMBER STATE INPUT DATA TO CSV ==="
	json2tab --debug=2 --convert ms_data/nl/rivm_20250101_windturbines_vermogen/rivm_20250101_windturbines_vermogen.shp ms_data/nl/rws_20240101_windparken_turbines/windparken_turbinesPoint.shp --type netherlands --output generated_database/netherlands.csv
	json2tab --debug=2 --convert ms_data/be/er_windturb_st_aangevr/er_windturb_st_aangevr.shp --type flanders --output generated_database/flanders_onshore.csv
	json2tab --debug=2 --merge generated_database/flanders_onshore.csv ms_data/be/belgian_offshore_with_types.csv --labels N/A "Belgium Offshore" --output generated_database/belgium.csv
	json2tab --debug=2 --convert ms_data/fin/finland_wind_fleet_data_202506.json --type finland --output generated_database/finland.csv
	json2tab --debug=2 --convert ms_data/de/Gesamtdatenexport_20251113_25.2/EinheitenWind.xml --type germany --output generated_database/germany.csv
	json2tab --debug=2 --convert "ms_data/dnk/Vindmølledata til 2025-01.xlsx" --type denmark --output generated_database/denmark.csv
	json2tab --debug=3 --convert ms_data/it/Italian_Wind_Farms_db.xlsx --type italy --output generated_database/italy.csv
	json2tab --debug=3 --convert ms_data/bg/bulgarian_wind_farms_combined_v2.csv --type csv2csv --output generated_database/bulgaria.csv
	json2tab --debug=2 --convert ms_data/at/igwindkraft-windrad-karte.json --type austria --output generated_database/austria_igwindkraft.csv
	echo "TODO: SWEDEN (FOR HISTORY)"


	echo "=== FIXING COUNTRY AND IS_OFFSHORE FLAG FOR ALL PRODUCES CSVs ==="
	json2tab --debug=2 --convert generated_database/*.csv static_data/worldmap/EEZ/EEZ_land_union_v4_202410.shp static_data/worldmap/country_borders/countries.geojson --type fix_country_offshore

	echo "=== BUILD AUSTRIA, ENRICH OSM AUSTRIA DATA WITH WF101 ==="
	json2tab --debug=2 --convert generated_database/wf101.csv --type select_country --country Austria --output generated_database/austria_wf101.csv
	json2tab --debug=2 --convert generated_database/osm.csv --type select_country --country Austria --output generated_database/austria_osm.csv
	json2tab --debug=2 --merge generated_database/austria_osm.csv generated_database/austria_wf101.csv --merge-mode enrich_first --output generated_database/austria_osm_wf101.csv
	json2tab --debug=2 --merge generated_database/austria_igwindkraft.csv generated_database/austria_osm_wf101.csv --output generated_database/austria.csv

	echo "=== RESTRICT MS DATA TO ONLY OWN COUNTRY ==="
	json2tab --debug=2 --convert generated_database/netherlands.csv --type select_country --country Netherlands
	json2tab --debug=2 --convert generated_database/belgium.csv --type select_country --country Belgium
	json2tab --debug=2 --convert generated_database/germany.csv --type select_country --country Germany
	json2tab --debug=2 --convert generated_database/denmark.csv --type select_country --country Denmark
	json2tab --debug=2 --convert generated_database/finland.csv --type select_country --country Finland
	json2tab --debug=2 --convert generated_database/italy.csv --type select_country --country Italy
	json2tab --debug=2 --convert generated_database/austria.csv --type select_country --country Austria

	echo "=== MERGING MEMBER STATE INPUT DATA FILES ==="
	json2tab --debug=2 --merge generated_database/netherlands.csv generated_database/belgium.csv --output generated_database/netherlands+belgium.csv
	json2tab --debug=2 --merge generated_database/germany.csv generated_database/austria.csv --output generated_database/germany+austria.csv
	json2tab --debug=2 --merge generated_database/netherlands+belgium.csv generated_database/germany+austria.csv --output generated_database/netherlands+belgium+germany+austria.csv

	json2tab --debug=2 --merge generated_database/denmark.csv generated_database/finland.csv --output generated_database/denmark+finland.csv
	json2tab --debug=2 --merge generated_database/italy.csv generated_database/bulgaria.csv --output generated_database/italy+bulgaria.csv
	json2tab --debug=2 --merge generated_database/denmark+finland.csv generated_database/italy+bulgaria.csv --output generated_database/denmark+finland+italy+bulgaria.csv

	json2tab --debug=2 --merge generated_database/netherlands+belgium+germany+austria.csv generated_database/denmark+finland+italy+bulgaria.csv --output generated_database/ms_data.csv

	echo "=== MERGING EUROPE MAPS (W/O COUNTRY EXCLUSIVE DATA) ==="
	json2tab --debug=2 --merge generated_database/osm.csv generated_database/wf101.csv --output generated_database/osm+wf101.csv
	json2tab --debug=2 --convert generated_database/osm+wf101.csv --type remove_country --country Germany Denmark Italy Bulgaria Austria
	json2tab --debug=2 --merge generated_database/osm+wf101.csv generated_database/ms_data.csv --output generated_database/euromap_$(shell date +%Y%m%d).[csv,geojson]
	ln -s euromap_$(shell date +%Y%m%d).geojson generated_database/euromap.geojson

	echo "=== REMOVE TEMP FILES ==="
	rm generated_database/*.csv.orig


location2country:
	json2tab --debug=1 --location2country static_data/worldmap/country_borders/countries.geojson 2.9772590 51.6698336    # B331_D03, Borssele III, https://www.openstreetmap.org/node/7677766593
	json2tab --debug=1 --location2country static_data/worldmap/country_borders/countries.geojson 2.9120371 51.6446948    # NW C-10, Northwind, https://www.openstreetmap.org/node/4756304453
	json2tab --debug=1 --location2country static_data/worldmap/EEZ/EEZ_land_union_v4_202410.shp 2.9772590 51.6698336     # B331_D03, Borssele III, https://www.openstreetmap.org/node/7677766593
	json2tab --debug=1 --location2country static_data/worldmap/EEZ/EEZ_land_union_v4_202410.shp 2.9120371 51.6446948     # NW C-10, Northwind, https://www.openstreetmap.org/node/4756304453
	json2tab --debug=1 --location2country static_data/worldmap/Netherlands/gadm41_NLD_fixZH.gpkg 5.2591827 52.9995252 1  # Fiesland Windpark U49
	json2tab --debug=1 --location2country static_data/worldmap/Netherlands/gadm41_NLD_fixZH.gpkg 3.9753655 51.9780770 1  # Maasvlakte Rotterdam
	json2tab --debug=1 --location2country static_data/worldmap/Netherlands/gadm41_NLD_fixZH.gpkg 5.2591827 52.9995252 2  # Fiesland Windpark U49
	json2tab --debug=1 --location2country static_data/worldmap/Netherlands/gadm41_NLD_fixZH.gpkg 5.6307759 52.6390398 2  # Zuidermeerdijk 2w Urk
	json2tab --debug=1 --location2country static_data/worldmap/Netherlands/gadm41_NLD_fixZH.gpkg 3.9753655 51.9780770 2  # Maasvlakte Rotterdam
	json2tab --debug=1 --location2country static_data/worldmap/EEZ/EEZ_land_union_v4_202410.shp 2.363421103838799 48.826341580661605