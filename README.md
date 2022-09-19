# SOA BRIDGE

This repository is a set of scripts and output to build on top of the excellent work by [JozefAerts](https://github.com/JozefAerts).

The input is taken in and a few patches are applied to the content and it is split out by patient.

This can then be augmented elements on an adhoc basis:
- Current implementation is using the **SV** dataset to generate encounters

## Installation
1. Install Poetry (https://python-poetry.org/docs/#installation)
2. Clone the repository
  ```
  git clone https://github.com/glow-mdsol/soa-bridge-match
  ```
3. Install the requirements
  ```
  poetry install
  ```

## Generating the files.

To regenerate the files, run the following command (in the upstream folder):
1. Patch the current implementation and split the content into patients
```
python patch_json.py source/LZZT_FHIR_Bundle_10_Patients_All_Resources.json
```
2. Merge in the visit information (it will scan all the json files in the directory)
```
python add_visits.py subjects
```