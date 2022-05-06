#Overview of Files used for Mike’s Testing
##Excel Files
Each .xslx file was created by using a PowerQuery to ingest and “flatten” the .json file for Subject 01-701-1015 that was posted in in soa-bridge-match/upstream/subjects at develop · glow-mdsol/soa-bridge-match (github.com)
From that .json file for Subject 01-701-1015, separate .xlsx files were created for each Resource
-ResearchStudy
-ResearchSubject
-Patient
-PlanDefinition
-CarePlan
-ServiceRequest
-Encounter
-Observation
-ObservationDefinition

#Access Database File
Each .xlsx file was imported into the Microsoft Access database as a linked table
Queries were created to change the column names from the Excel files into “businesses speak” column names.
Joins were created to relate the Resources’ data
Queries were created to export the key data points and primary/foreign keys to illustrate the traceability of all the data from ResearchStudy to Observation. 
Query was created to show which data were expected, per ObservationDefinition
Query was created to show which data are NOT expected (not included in ObservationDefinition)
