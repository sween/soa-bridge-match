# Using the Sample Resource file

Download it from:
* https://sourceforge.net/projects/fhirloinc2sdtm/files/LZZT_Study_Bundle/

## Patching and splitting the file
There are a couple of changes made to the sample resource file including:
* Use Subject ID for the ResearchSubject ID, rather than the Patient ID
* Ensure the IDs are unique

Run the script:
```
python patch_json.py LZZT_FHIR_Bundle_10_Patients_All_Resources.json
```

It will generate a file per subject in a subjects subdirectory.

The files herein are:
* [LZZT_FHIR_Bundle_10_Patients_All_Resources.json]() - the source FHIR bundled copied from the link above
* [LZZT_FHIR_Bundle_10_Patients_All_Resources_Patched.json]() - the patched FHIR bundle

## Adding the encounters 

The subjects can have one or more Encounters merged into the file using the **SV** domain as a source; 

In this case the subject bundles are in the `subjects` subdirectory.
```shell
python add_visits.py subjects
```

## Cloning a Research Subject
A subject bundle can be cloned into a new file using the following command:

```shell
python clone_subject.py --subject-id 01-701-9998 subjects/LZZT_FHIR_Bundle_01-701-1118_All_Resources.json
```

## Synthea Data

You can use the **Synthea** data to add resources for a subject.  In this case we use a script to add Observation Resources

1. Download the dataset from: [Synthea Synthetic Data](https://github.com/synthetichealth/synthea-sample-data)
2. Extact the zip file, record the path to the extracted files 
3. Create a `.env` file with the following variables:
    ```dotenv
    SYNTHEA_DATA_DIR=/path/to/synthea-sample-data
    ```
4. Run the script (in this example we add 10 lab results for one subject)
    ```
    python add_random_obs.py -f subjects/LZZT_FHIR_Bundle_01-701-9999_All_Resources.json -n 10 -t laboratory
    ```
