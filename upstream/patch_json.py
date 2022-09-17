import hashlib
import json
import os.path
import sys
import uuid
from datetime import datetime

"""
This script does some elementary patching of the JSON files from the upstream
- adds a transaction type to the Bundle
- changes Patient.id to a hash of the Subject ID
- binds the Subject ID to the ResearchSubject Resource
- updates all Patient.id references to the hash of the Subject ID
- adds the Study Medication as the suspectEntity for the AE
- adds the subject reference for the contained Condition resource for the AE
- adds the actuality reference for the AE
- fixes some id duplication for Observations
- adds request metadata for the entries to try and use UPSERT semantics for the resources
- replaces OTHER LONG LOINC name with Temp measurement 
- add status to observations (wierdly it thinks some are missing)   
"""

STATUS = dict(Observation=dict(status="final"),
              MedicationStatement=dict(status="completed"))

SUBJECT_MAP = {}

IP_ID = "H2Q-MC-LZZT-LY246708"


def update_references(parent: dict):
    """
    Update the Patient to use a Hash rather than the Subject ID
    """
    if not isinstance(parent, (dict, list)):
        return
    if 'resourceType' in parent and parent['resourceType'] == 'ResearchSubject':
        return
    if 'reference' in parent:
        if parent['reference'].startswith('Patient/'):
            # already hashed
            if '-' in parent['reference']:
                patient_id = parent['reference'].split('/')[-1]
                hashed = hashlib.md5(patient_id.encode('utf-8')).hexdigest()
                parent['reference'] = f"Patient/{hashed}"
        elif parent['reference'].startswith('Organization/'):
            org_id = parent['reference'].split('/')[-1]
            if str(org_id).isdigit():
                hashed = hashlib.md5(org_id.encode('utf-8')).hexdigest()
                parent['reference'] = f"Organization/{hashed}"
        elif parent['reference'].startswith('ResearchStudy/'):
            parent['reference'] = f"ResearchStudy/H2Q-MC-LZZT-ResearchStudy"
    else:
        if isinstance(parent, list):
            for child in parent:
                update_references(child)
        elif isinstance(parent, dict):
            # these have been manually patched
            for child in parent.values():
                update_references(child)


def patch_research_subject(research_subject: dict) -> str:
    """
    Need to:
    * update the reference to Subject to use the hashed id
    * update the identifier to use the subject id
    """
    subject_id = research_subject["individual"]["reference"].split("/")[-1]
    hashed = hashlib.md5(subject_id.encode('utf-8')).hexdigest()
    research_subject["individual"]["reference"] = f"Patient/{hashed}"
    research_subject["id"] = subject_id
    return subject_id


def patch_patient(patient: dict) -> str:
    """
    Need to:
    * update the reference to Patient to use the hashed id
    * update the identifier to use the patient id
    """
    patient_id = patient["id"]
    hashed = hashlib.md5(patient_id.encode('utf-8')).hexdigest()
    patient["id"] = hashed
    return hashed


def patch_adverse_event(adverse_event: dict):
    """
    Add the medication reference to the suspectEntity
    """
    if 'suspectEntity' in adverse_event:
        for item in adverse_event['suspectEntity']:
            if 'instance' not in item:
                # add a link to the medication (currently dangling)
                item['instance'] = dict(reference=f'Medication/{IP_ID}')
    if 'contained' in adverse_event:
        for item in adverse_event['contained']:
            # clone the subject from the event
            if item['resourceType'] == 'Condition':
                item['subject'] = adverse_event['subject']
    if 'actuality' not in adverse_event:
        adverse_event['actuality'] = 'actual'


def patch_observation(observation: dict):
    """
    Add the OTHER LOINC LONG NAME fix
    """
    identifier = observation["id"]
    code = observation['code']
    if 'text' in code and code['text'] == 'OTHER LOINC LONG NAME':
        code['text'] = 'Body temperature'
        coding = code['coding'][0]
        coding['code'] = '8310-5'
        coding['system'] = 'http://loinc.org'
        coding['display'] = 'Body temperature'
        print("Patched OTHER LOINC LONG NAME")
    if 'status' not in observation:
        observation['status'] = 'final'
    if 'effectiveDateTime' in observation:
        if 'T' not in observation['effectiveDateTime']:
            observation['effectiveDateTime'] = observation['effectiveDateTime'] + 'T08:00:00Z'
        elif not observation['effectiveDateTime'].endswith('Z'):
            observation['effectiveDateTime'] = observation['effectiveDateTime'] + 'Z'
    if 'start' in observation:
        if 'T' in observation['start'] and not observation['start'].endswith('Z'):
            observation['start'] = observation['start'] + 'Z'
    if 'end' in observation:
        if 'T' in observation['end'] and not observation['end'].endswith('Z'):
            observation['end'] = observation['end'] + 'Z'
    return identifier

def purge_comments(resource: dict):
    """
    Remove comments from the resource
    """
    if not isinstance(resource, (dict, list)):
        return
    if 'fhir_comments' in resource:
        del resource['fhir_comments']
    if isinstance(resource, list):
        for child in resource.copy():
            purge_comments(child)
    elif isinstance(resource, dict):
        for child_name, child in resource.copy().items():
            # remove the 
            if child_name.startswith('_'):
                del resource[child_name]
            purge_comments(child)


def split_bundle(bundle: dict, expected: list[str]) -> dict:
    """
    Split a bundle into a list of entries
    """
    cache = {}
    common = []
    patients = []
    for entry in bundle['entry']:
        rtype = entry['resource']['resourceType']
        # maybe this should check for 'subject' or 'individual'
        if rtype == "ObservationDefinition":
            # ignore ObservationDefinition
            continue
        elif rtype in ("ResearchStudy", "Group", "Organization", "Practitioner", "Medication") or rtype.endswith(
                "Definition"):
            # design elements
            common.append(entry)
        else:
            if rtype == "Patient":
                _id = entry['resource']['id']
                patients.append(_id)
            elif rtype == "ResearchSubject":
                _id = entry['resource']['individual']['reference'].split("/")[-1]
            else:
                try:
                    subject = entry['resource']['subject']
                except KeyError as exc:
                    print("Subject missing on {} {}".format(rtype, entry['resource']['id']))
                    raise exc
                _id = subject['reference'].split("/")[-1]
            if _id not in cache:
                if _id not in expected:
                    # this might not be a problem
                    # print("Unknown patient {} on {} {}".format(_id, rtype, entry['resource']['id']))
                    continue
            cache.setdefault(_id, []).append(entry)
    for _id, entries in cache.items():
        cache[_id] = entries + common
    if cache.keys() != patients:
        print("Extra patients: {}".format(set(cache.keys()) - set(patients)))
    return cache


def patch_file(filename, output_dir):
    if os.path.exists(filename):
        id_cache = {}
        dupes = {}
        prefix, ext = os.path.splitext(filename)
        with open(filename, 'r') as f:
            data = json.load(f)
        if "type" not in data:
            data["type"] = "transaction"
        subjects = []
        patients = []
        patient_ids = {}
        for idx, entry in enumerate(data['entry']):
            resource = entry['resource']
            resource_type = resource['resourceType']
            _identifier = resource['id']
            if _identifier in id_cache.get(resource_type, []):
                print(f"{idx}: Updating duplicate identifier", _identifier, "for resource", resource_type)
                _id = str(uuid.uuid4())
                # add a reference to the duplicate
                dupes.setdefault(resource_type, []).append(dict(id=_identifier, new_id=_id, idx=idx))
                resource['id'] = _id
            else:
                id_cache.setdefault(resource_type, []).append(_identifier)
            if resource['resourceType'] == 'AdverseEvent':
                patch_adverse_event(resource)
            elif resource['resourceType'] == 'ResearchSubject':
                subjects.append(resource)
                # update the identifier
                _identifier = patch_research_subject(resource)
            elif resource['resourceType'] == 'Patient':
                original_id = resource['id']
                patients.append(resource)
                # update the identifier
                _identifier = patch_patient(resource)
                # track the patient ids
                patient_ids[_identifier] = original_id
            elif resource['resourceType'] == 'Observation':
                _identifier = patch_observation(resource)
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
            update_references(resource)
            purge_comments(resource)
            # if 'fullUrl' not in entry:
            #     # ADD THE FULL URL
            #     entry['fullUrl'] = _identifier
            if 'request' not in entry:
                # ADD THE REQUEST (to create the resource)
                entry['request'] = dict(method='PUT',
                                        url=f"{resource_type}/{_identifier}",
                                        ifNoneExist=f"identifier={_identifier}")
        # add the site
        _site_id = hashlib.md5("701".encode('utf-8')).hexdigest()
        site_entry = dict(resource=dict(
            resourceType='Organization',
            id=_site_id,
            name="H2Q-MC-LZZT Site 701"),
            request=dict(method='PUT',
                         url=f'Organization/{_site_id}',
                         ifNoneExist=f"id={_site_id}")
        )
        data['entry'].append(site_entry)
        # add a record for the medication (IP)
        medication_entry = dict(resource=dict(
            resourceType='Medication',
            id=IP_ID),
            request=dict(method='PUT',
                         url=f'Medication/{IP_ID}',
                         ifNoneExist=f"id={IP_ID}")
        )
        data['entry'].append(medication_entry)
        # check we haven't made a new subject or two
        assert len(patients) == len(subjects)
        with open(f"{prefix}_patched{ext}", 'w') as f:
            json.dump(data, f, indent=2)
        with open(f"{prefix}_dupes{ext}", 'w') as f:
            json.dump(dupes, f, indent=2)
        split_entries = split_bundle(data, patient_ids.keys())
        for patient_id, entries in split_entries.items():
            content = dict(resourceType="Bundle",
                           id=str(uuid.uuid4()),
                           type="transaction",
                           meta=dict(lastUpdated=datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')),
                           entry=entries)

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            with open(f"{output_dir}/{os.path.basename(prefix).replace('10_Patients', patient_ids.get(patient_id))}{ext}", 'w') as f:
                json.dump(content, f, indent=2)

    else:
        raise FileNotFoundError(filename)


if __name__ == "__main__":
    patch_file(sys.argv[1], sys.argv[2])
