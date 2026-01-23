#!/bin/sh
echo "Used database: $1"
echo "Query file:    $2"
echo "Output file:   $3"

export LOCAL_OVERPASS_API="/home/$USER/software/overpass-api/osm-3s_v0.7.62.8"
export DB_VERSION="$1"
export DB_DIR="$LOCAL_OVERPASS_API/$DB_VERSION"

$LOCAL_OVERPASS_API/bin/osm3s_query --db-dir=$DB_DIR --progress < $2 > $3

