# Getting the source file

Download it from:
* https://sourceforge.net/projects/fhirloinc2sdtm/files/LZZT_Study_Bundle/

Run the script:
```
python patch_json.py LZZT_FHIR_Bundle_10_Patients_All_Resources.json
```

The files herein are:
* [LZZT_FHIR_Bundle_10_Patients_All_Resources.json]() - the source FHIR bundled copied from the link above
* [LZZT_FHIR_Bundle_10_Patients_All_Resources_Patched.json]() - the patched FHIR bundle


## Design

```mermaid
graph TD
    ResearchSubject --individual--> Patient 
    subgraph Design
    ResearchStudy --protocol--> PlanDefinition
    ResearchSubject --study--> ResearchStudy
    PlanDefinition --> PlanDefinition
    end
    subgraph Execution
    CarePlan --basedOn--> PlanDefinition
    ServiceRequest --basedOn--> CarePlan
    Encounter --basedOn--> ServiceRequest
    Observation --encounter--> Encounter
    CarePlan --subject--> Patient
    ServiceRequest --subject--> Patient
    Encounter --subject--> Patient
    Observation --subject--> Patient
    end
```