# Available Evaluations
## Stress Test Evaluation
Tests each service on increasing number of concurrent requests/second.
Used to identify lightweight, regular and heavy processing tasks.

### Service Tasks Evaluated
#### Farm Calendar
* Register Farm Parcel
* Register Crop
* Register Generic Activity
* Register Built-in Activity
* List Farm Parcels
* Filter Parcel by lat/long
* List All activitities
* List Built-in Activity


### Main Metrics
* Latency
* Memory
* CPU

## Single Farm Crop Protection
### Concurrent Users: 2
### Farm Tasks:
* Register (once) Farm, Parcels, Crops, Materials, and Machinery
* Drone flying registering FC data?
* Tractor tiling parcel, pesticie spraying
* Report on pest Risk

### Data Workload Profile
#### Sensing: 80%
* registering monitoring observations in FC

#### Processing: 10%
* registering farm assets (farm, parcel, crops, etc..)
* ? Pest/desease processig? dataset processing?
#### Heavy Processing: 10%
* ? report generation?

### OA Services
* Gatekeeper
* Farm Calendar
* Pest And Disease
* Weather Service
* Reporting Service
### Main Metrics
* Energy Consumption
* Memory
* CPU
* Latency

## Three Farms Smart Irrigation (need to be written, text is from other case)
### Concurrent Users: 2
### Farm Tasks:
* Register (once) Farm, Parcels, Crops, Materials, and Machinery
* Drone flying registering FC data?
* Tractor tiling parcel, pesticie spraying
* Report on pest Risk
### OA Services
* Gatekeeper
* Farm Calendar
* Pest And Disease
* Weather Service
* Reporting Service
### Main Metrics
* Energy Consumption
* Memory
* CPU
* Latency

## Fifty Farms Compost Monitoring

