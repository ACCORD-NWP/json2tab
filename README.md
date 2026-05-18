# JSON-2-TAB

The JSON-2-TAB converter is a command line tool and library to crop global JSON windturbine database to domain specific TAB-file.

Optionally this tool can generate plots to visualize results, therefore only some additional optional python packages need to be installed. These are grouped in the `plotting` group in the poetry project configuration

## Setup
### Installation
To install the core of the JSON-2-TAB converter just call
```shell
make install
```

To install the JSON-2-TAB converter including the plotting functionality one can use the following install option
```shell
make install/plotting
```

### Preparation
When using json2tab it is expected that the *static_data* is prepared. Most of the statc_data files are already stored in the repository; but some has to be downloaded. To prepare the *static_data* folder run the make command in that folder, i.e:

```shell
cd static_data && make
```

**Note:** The make command `worldmap/eez` is likely to fail due to required user interation. So to continue preparation of static data download www.marineregions.org/download_file.php?name=EEZ_land_union_v4_202410.zip and save it to `static_data/worldmap/eez/EEZ_land_union_v4_202410.zip`

Afterwards rerun the `make` command:
```shell
cd static_data && make
```
Now all static data needed to run JSON-2-TAB is installed in the `static_data` folder.


## Usage
After installation of `json2tab` one can use the commandline interface using options as listed by

```shell
json2tab --help
```

See for more details of usage and configuration: [Wind Turbine Location Processor and Visualizer](json2tab/README.md)


---

## Meta-data generation: instructions to build (or update) master turbine location database
The input data to create the master turbine location database (a.k.a. euromap) is basically split in two main categories of data;

1. The first part is collecting so called *static_data*; this is static data that is expected not to change. For example information about country borders or the known wind turbine type database.
2. The second part is called *web_data* and is about collecting country/source specific wind turbine location information. Different countries/sources might have different update intervals to update the wind turbine location information. Therefore, to update the master turbine database one can update the *web_data* folder and all sources where new data is expected will fetch the latest wind turbine location information.

With both a populates *static_data* and *web_data* we can use `json2tab`'s convert, map and merge functionality to combine and build a single master wind turbine location file.

### Euromap build/update procedure
To build your own version of the master turbine location database use the following instructions:
  1. Install optional packages needed for euromap generation: `make install/euromap_generation`
  3. Enter folder `euromap`
  4. Run `make web-update`
  5. Run `make`

**Note:** it is assumed you have the JSON-2-TAB package installed and the *static_data* downloaded; if you haven't done it see section [Preparation](#Preparation) how to do it.



### Data sources for master turbine database
The master turbine database combines wind turbine location information from different sources. At the moment data from the following countries/sources are used:
- Austria
- Belgium [Flanders + Offshore]
- Bulgaria (static)
- Denmark (yearly?)
- EMODnet
- Finland (static)
- France (daily)
- Germany (daily)
- Greece (manual)
- Italy (static)
- Netherlands [onshore: RIVM, offshore: RWS] (yearly)
- OpenStreetMap (daily)
- Sweden (daily)
- United Kingdom (quarterly)
- wf101 [Old Austrian dataset based on flight obstables]

**Note:** For some countries there is not automated procedure to update country information; for these countries the `make web-update` will create a text-file with instructions how to fetch data for these countries.

