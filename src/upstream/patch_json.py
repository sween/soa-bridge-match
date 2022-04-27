import hashlib
import json
import os.path
import sys

"""
This script does some elementary patching of the JSON files from the upstream
- changes Patient.id to a hash of the Subject ID
- binds the Subject ID to the Research Subject 
- adds the study Medication as the suspectEntity for the AE
- adds the subject reference for the contained Condition resource for the AE
- adds the actuality reference for the AE
"""

STATUS = dict(Observation=dict(status="final"),
              MedicationStatement=dict(status="completed"))

SUBJECT_MAP = {}

def update_patient_reference(parent: dict):
    """
    Update the Patient to use a Hash rather than the Subject ID
    """
    if 'reference' in parent:
        if parent['reference'].startswith('Patient/'):
            patient_id = parent['reference'].split('/')[-1]
            hashed = hashlib.md5(patient_id.encode('utf-8')).hexdigest()
            parent['reference'] = f"Patient/{hashed}"
    else:
        # these have been manually patched
        for child in parent.values():
            if isinstance(child, dict):
                update_patient_reference(child)


def patch_research_subject(research_subject: dict):
    """
    Need to:
    * update the reference to Subject to use the hashed id
    * update the identifier to use the subject id
    """
    patient_id = research_subject["individual"]["reference"].split("/")[-1]
    hashed = hashlib.md5(patient_id.encode('utf-8')).hexdigest()
    research_subject["individual"]["reference"] = f"Patient/{hashed}"
    research_subject["id"] = patient_id


def patch_patient(patient: dict):
    """
    Need to:
    * update the reference to Patient to use the hashed id
    * update the identifier to use the patient id
    """
    patient_id = patient["id"]
    hashed = hashlib.md5(patient_id.encode('utf-8')).hexdigest()
    patient["id"] = hashed


def patch_adverse_event(adverse_event: dict):
    event = adverse_event['event']
    if 'suspectEntity' in adverse_event:
        for item in adverse_event['suspectEntity']:
            if 'instance' not in item:
                # add a link to the medication (currently dangling)
                item['instance'] = dict(reference='Medication/LY246708')
    if 'contained' in adverse_event:
        for item in adverse_event['contained']:
            # clone the subject from the event
            if item['resourceType'] == 'Condition':
               item['subject'] = adverse_event['subject']
    if 'actuality' not in adverse_event:
        adverse_event['actuality'] = 'actual'


def patch_file(filename):
    if os.path.exists(filename):
        prefix, ext = os.path.splitext(filename)
        with open(filename, 'r') as f:
            data = json.load(f)
        for entry in data['entry']:
            resource = entry['resource']
            resource_type = resource['resourceType']
            _identifier = resource['id']
            if resource['resourceType'] == 'AdverseEvent':
                patch_adverse_event(resource)
            elif resource['resourceType'] == 'ResearchSubject':
                patch_research_subject(resource)
            elif resource['resourceType'] == 'Patient':
                patch_patient(resource)
            elif resource['resourceType'] in STATUS:
                _sets = STATUS[resource['resourceType']]
                for key, value in _sets.items():
                    if isinstance(value, dict):
                        element = resource[key]
                        if isinstance(element, list):
                            for item in element:
                                for k, v in value.items():
                                    item[k] = v
                        else:
                            for k, v in value.items():
                                element[k] = v
                    elif key not in entry['resource']:
                        entry['resource'][key] = value
            update_patient_reference(resource)
            # if 'fullUrl' not in entry:
            #     # ADD THE FULL URL
            #     entry['fullUrl'] = _identifier
            if 'request' not in entry:
                # ADD THE REQUEST (to create the resource)
                entry['request'] = dict(method='POST',
                                        url=f"{resource_type}",
                                        ifNoneExist=f"identifier={_identifier}")
        with open(f"{prefix}_patched{ext}", 'w') as f:
            json.dump(data, f, indent=2)
    else:
        raise FileNotFoundError(filename)


if __name__ == "__main__":
    patch_file(sys.argv[1])
