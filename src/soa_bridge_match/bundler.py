from __future__ import annotations
import hashlib
import os
import random
from typing import Optional, List
from fhir.resources.bundle import Bundle, BundleEntry, BundleEntryRequest

import uuid

from fhir.resources.patient import Patient, PatientLink
from fhir.resources.plandefinition import PlanDefinition
from fhir.resources.reference import Reference
from fhir.resources.researchstudy import ResearchStudy
from fhir.resources.researchsubject import ResearchSubject
from fhir.resources.resource import Resource

from .synthea import SyntheaPicker

class SourcedBundle:
    """
    Wraps the bundle and generation thereof.
    """

    def __init__(self, bundle: Optional[Bundle],
                 identifier: Optional[str],
                 filename: Optional[str]) -> None:
        self._resources = []
        self._identifier = identifier if identifier else uuid.uuid4().hex
        self._filename = filename if filename else None
        self._bundle = bundle if bundle else None
        self._entities = {}
        self._synthea = None

    @property
    def synthea_bridge(self):
        if not self._synthea:
            self._synthea = SyntheaPicker()
        return self._synthea

    @property
    def filename(self) -> str:
        return os.path.basename(self._filename) if self._filename else f"{self._identifier}.json"

    @property
    def dirname(self) -> str:
        return os.path.dirname(self._filename) if self._filename else "."

    @property
    def plan_definitions(self) -> List[str]:
        if 'PlanDefinition' not in self._entities:
            for entry in self._bundle.entry:
                if entry.resource.resource_type == 'PlanDefinition':
                    self._entities.setdefault('PlanDefinition', []).append(entry.resource.id)
        return self._entities.get('PlanDefinition', [])

    @property
    def subjects(self) -> List[str]:
        """
        Extracts the list of subjects from the bundle
        """
        if 'ResearchSubject' not in self._entities:
            for entry in self._bundle.entry:
                if entry.resource.resource_type == 'ResearchSubject':
                    self._entities.setdefault('ResearchSubject', []).append(entry.resource.id)
        return self._entities.get('ResearchSubject', [])

    @property
    def studies(self) -> List[str]:
        """
        Extracts the list of studies from the bundle
        """
        if 'ResearchStudy' not in self._entities:
            for entry in self._bundle.entry:
                if entry.resource.resource_type == 'ResearchStudy':
                    self._entities.setdefault('ResearchStudy', []).append(entry.resource.id)
        return self._entities.get('ResearchStudy', [])

    @property
    def patients(self) -> List[Patient]:
        """
        Extracts the list of patients from the bundle
        """
        if 'Patient' not in self._entities:
            for entry in self._bundle.entry:
                if entry.resource.resource_type == 'Patient':
                    self._entities.setdefault('Patient', []).append(entry.resource.id)
        return self._entities.get('Patient', [])

    def subject(self, subject_id: str) -> Optional[ResearchSubject]:
        """
        Get a Patient Resource
        """
        for entry in self._bundle.entry:
            if entry.resource.resource_type == 'ResearchSubject' and entry.resource.id == subject_id:
                return entry.resource
        return None

    def patient(self, patient_id: str) -> Optional[Patient]:
        """
        Get a Patient Resource
        """
        for entry in self._bundle.entry:
            if entry.resource.resource_type == 'Patient' and entry.resource.id == patient_id:
                return entry.resource
        return None

    def study(self, study_id: str) -> Optional[ResearchStudy]:
        """
        Get a Study Resource
        """
        for entry in self._bundle.entry:
            if entry.resource.resource_type == 'ResearchStudy' and entry.resource.id == study_id:
                return entry.resource
        return None

    @property
    def bundle(self) -> Bundle:
        if not isinstance(self._bundle, Bundle):
            # create a new bundle
            self._bundle = Bundle(id=self._identifier, type="transaction")
        return self._bundle

    def dump(self, target_dir: Optional[str] = None,
             name: Optional[str] = None,
             bundle: Optional[Bundle] = None) -> None:
        """
        Dumps a bundle to a directory
        """
        if name:
            _fname = name + ".json"
        else:
            _fname = self.filename
        if target_dir:
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            fname = os.path.join(target_dir, _fname)
        else:
            fname = os.path.join(self.dirname, _fname)
        with open(fname, 'w') as f:
            if bundle:
                f.write(bundle.json(indent=2))
            else:
                f.write(self._bundle.json(indent=True))

    def add_lab_value(self, subject_id: Optional[str] = None):
        subject_id = subject_id or random.choice(self.subjects)
        if subject_id not in self.subjects:
            raise ValueError(f"Subject {subject_id} does not exist")
        # get the patient ID
        patient_id = self.subject(subject_id).individual.reference.split('/')[-1]
        lab_obs = self.synthea_bridge.get_lab_observation()
        lab_obs.subject.reference = f"Patient/{patient_id}"
        lab_obs.fhir_comments = ["This is a synthetic observation"]
        # remove the encounter reference
        del lab_obs.encounter
        # sanitise the lab observation
        self.add_resource(lab_obs)

    def add_vitals_value(self, subject_id: Optional[str] = None):
        subject_id = subject_id or random.choice(self.subjects)
        if subject_id not in self.subjects:
            raise ValueError(f"Subject {subject_id} does not exist")
        # get the patient ID
        patient_id = self.subject(subject_id).individual.reference.split('/')[-1]
        vital_obs = self.synthea_bridge.get_vital_observation()
        vital_obs.subject.reference = f"Patient/{patient_id}"
        vital_obs.fhir_comments = ["This is a synthetic observation"]
        # remove the encounter reference
        del vital_obs.encounter
        # sanitise the lab observation
        self.add_resource(vital_obs)

    def add_resource(self, resource: Resource):
        """
        Adds a resource to the bundle
        """
        for entry in self._bundle.entry:
            if entry.resource.resource_type == resource.resource_type and entry.resource.id == resource.id:
                print(f"Resource {resource.resource_type}/{resource.id} already exists in bundle")
                return
        else:
            print("Adding resource to bundle: {}".format(resource.resource_type))
            entry = BundleEntry(resource=resource,
                                request=BundleEntryRequest(method="PUT",
                                                           url=f"{resource.resource_type}/{resource.id}",
                                                           ifNoneExist=f"identifier={resource.id}"))
            self._bundle.entry.append(entry)

    def clone_subject(self, new_subject_id: str) -> SourcedBundle:
        """
        Clones a patient by taking a random subject in the bundle and creating a new patient with the new_patient_id
        """
        # get a random subject
        _subject_id = random.choice(self.subjects)
        _subject = self.subject(_subject_id)
        # Get the old subject ID
        _old_subject_id = _subject.id
        # get the patient identifer
        _patient_id = _subject.individual.reference.split('/')[-1]
        # hashed id
        _new_patient_id = hashlib.md5(new_subject_id.encode('utf-8')).hexdigest()
        # create a new bundle
        _bundle = Bundle(id=str(uuid.uuid4()), type="transaction", entry=[])
        for entry in self._bundle.entry:  # type: BundleEntry
            if entry.resource.resource_type == 'Patient' and entry.resource.id == _patient_id:
                resource = entry.resource.copy()  # type: Patient
                # clone the patient
                resource.id = _new_patient_id
                link = PatientLink(type='refer', other=Reference(reference=f"Patient/{_old_subject_id}"))
                if not getattr(resource, 'link'):
                    resource.link = []
                resource.link.append(link)
                resource.fhir_comments = ["Cloned from Subject {}".format(_old_subject_id)]
                _entry = BundleEntry(resource=resource,
                                     request=BundleEntryRequest(method="PUT",
                                                                url=f"{resource.resource_type}/{resource.id}",
                                                                ifNoneExist=f"identifier={resource.id}"))

                # add the patient to the bundle
                _bundle.entry.append(_entry)
            elif entry.resource.resource_type == 'ResearchSubject'\
                    and entry.resource.id == _subject.id:
                resource = entry.resource.copy()
                # clone the subject
                resource.id = new_subject_id
                resource.individual.reference = f"Patient/{_new_patient_id}"

                _entry = BundleEntry(resource=resource,
                                     request=BundleEntryRequest(method="PUT",
                                                                url=f"{resource.resource_type}/{resource.id}",
                                                                ifNoneExist=f"identifier={resource.id}"))

                # add the subject to the bundle
                _bundle.entry.append(_entry)
            elif entry.resource.resource_type in ("ResearchStudy", "Group", "Organization",
                                                  "Practitioner", "Medication") \
                    or entry.resource.resource_type.endswith('Definition'):
                # add the common entities to the bundle
                _bundle.entry.append(entry)
            elif entry.resource.subject.reference == f"Patient/{_patient_id}":
                # id resources where the subject is the patient
                resource = entry.resource.copy()
                resource.subject.reference = f"Patient/{_new_patient_id}"
                if getattr(resource.subject, 'display', None):
                    resource.subject.display = new_subject_id
                if resource.resource_type == "CarePlan":
                    # clear this up
                    resource.title = resource.title.replace(_subject_id, new_subject_id)

                # need a deterministic id
                hashed_id = hashlib.md5(f"{_patient_id}-{resource.resource_type}-{resource.id}".encode('utf-8')).hexdigest()
                # need to map the IDs
                resource.id = hashed_id
                if getattr(resource, 'contained', None):
                    for contained in resource.contained:
                        # Look for contained references
                        if hasattr(contained, 'subject'):
                            # map to the new ID
                            contained.subject.reference = f"Patient/{_new_patient_id}"
                _entry = BundleEntry(resource=resource,
                                     request=BundleEntryRequest(method="PUT",
                                                                url=f"{resource.resource_type}/{resource.id}",
                                                                ifNoneExist=f"identifier={resource.id}"))
                # add the cloned entity
                _bundle.entry.append(_entry)
            instance = SourcedBundle(bundle=_bundle,
                                     identifier=str(_bundle.identifier),
                                     filename=self.filename.replace(_old_subject_id, _new_patient_id))
        return instance

    @classmethod
    def from_bundle_file(cls, filename: str):
        """
        Convert a FHIR Bundle to a SourcedBundle
        """
        if not os.path.exists(filename):
            raise ValueError("File does not exist")
        bundle = Bundle.parse_file(filename)
        return cls(bundle, bundle.id, filename)

    @classmethod
    def from_bundle(cls, bundle: Bundle):
        """
        Convert a FHIR Bundle to a SourcedBundle
        """
        return cls(bundle, bundle.id)
