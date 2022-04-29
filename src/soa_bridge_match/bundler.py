import os
from typing import Optional
from fhir.resources.bundle import Bundle, BundleEntry, BundleEntryRequest
from fhir.resources.encounter import Encounter

import uuid

from fhir.resources.resource import Resource


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

    @property
    def filename(self) -> str:
        return os.path.basename(self._filename) if self._filename else f"{self._identifier}.json"

    @property
    def dirname(self) -> str:
        return os.path.dirname(self._filename) if self._filename else "."

    @property
    def plan_definitions(self):
        if 'PlanDefinition' not in self._entities:
            for entry in self._bundle.entry:
                if entry.resource.resource_type == 'PlanDefinition':
                    self._entities.setdefault('PlanDefinition', []).append(entry.resource.id)
        return self._entities.get('PlanDefinition', [])

    @property
    def subjects(self):
        """
        Extracts the list of subjects from the bundle
        """
        if 'ResearchSubject' not in self._entities:
            for entry in self._bundle.entry:
                if entry.resource.resource_type == 'ResearchSubject':
                    self._entities.setdefault('ResearchSubject', []).append(entry.resource.id)
        return self._entities.get('ResearchSubject', [])

    @property
    def studies(self):
        """
        Extracts the list of studies from the bundle
        """
        if 'ResearchStudy' not in self._entities:
            for entry in self._bundle.entry:
                if entry.resource.resource_type == 'ResearchStudy':
                    self._entities.setdefault('ResearchStudy', []).append(entry.resource.id)
        return self._entities.get('ResearchStudy', [])

    @property
    def patients(self):
        """
        Extracts the list of patients from the bundle
        """
        if 'Patient' not in self._entities:
            for entry in self._bundle.entry:
                if entry.resource.resource_type == 'Patient':
                    self._entities.setdefault('Patient', []).append(entry.resource.id)
        return self._entities.get('Patient', [])

    def subject(self, subject_id: str):
        """
        Get a Patient Resource
        """
        for entry in self._bundle.entry:
            if entry.resource.resource_type == 'ResearchSubject' and entry.resource.id == subject_id:
                return entry.resource
        return None

    def patient(self, patient_id: str):
        """
        Get a Patient Resource
        """
        for entry in self._bundle.entry:
            if entry.resource.resource_type == 'Patient' and entry.resource.id == patient_id:
                return entry.resource
        return None

    def study(self, study_id: str):
        """
        Get a Study Resource
        """
        for entry in self._bundle.entry:
            if entry.resource.resource_type == 'ResearchStudy' and entry.resource.id == study_id:
                return entry.resource
        return None

    @property
    def bundle(self):
        if not isinstance(self._bundle, Bundle):
            # create a new bundle
            self._bundle = Bundle(id=self._identifier, type="transaction")
        return self._bundle

    def dump(self, target_dir: Optional[str] = None):
        """
        Dumps the bundle to a directory
        """

        if target_dir:
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            fname = os.path.join(target_dir, self.filename)
        else:
            fname = os.path.join(self.dirname, self.filename)
        with open(fname, 'w') as f:
            f.write(self._bundle.json(indent=True))

    def add_resource(self, resource: Resource):
        """
        Adds a resource to the bundle
        """
        for entry in self._bundle.entry:
            if entry.resource.resource_type == resource.resource_type and entry.resource.id == resource.id:
                print("Resource already exists in bundle")
                return
        else:
            print("Adding resource to bundle: {}".format(resource.resource_type))
            entry = BundleEntry(resource=resource,
                                request=BundleEntryRequest(method="PUT",
                                                           url=f"{resource.resource_type}/{resource.id}",
                                        ifNoneExist=f"identifier={resource.id}"))
            self._bundle.entry.append(entry)

    @classmethod
    def from_bundle_file(cls, filename: str):
        """
        Convert a FHIR Bundle to a SourcedBundle
        """
        if not os.path.exists(filename):
            raise ValueError("File does not exist")
        bundle = Bundle.parse_file(filename)
        return cls(bundle, bundle.id, filename)