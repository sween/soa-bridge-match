
import os
from turtle import st

from fhir.resources.coding import Coding
from fhir.resources.fhirtypes import Canonical

from config import Configuration
from connector import Connector
from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient
from fhir.resources.servicerequest import ServiceRequest
from fhir.resources.careplan import CarePlan, CarePlanActivity
from fhir.resources.encounter import Encounter
from fhir.resources.observation import Observation
from fhir.resources.reference import Reference
import hashlib


from bundler import SourcedBundle


class Naptha:

    def __init__(self, template: str) -> None:
        self._connector = Connector()
        self._subjects = {}
        self._patients = {}
        self._subjects = {}
        # load the template
        self._content = SourcedBundle.from_bundle_file(template)

    @property
    def content(self):
        return self._content

    def get_subjects(self):
        """
        Get the list of subjects from the CDISC Pilot Dataset
        """
        dataset = self._connector.load_cdiscpilot_dataset("DM")
        return dataset.USUBJID.unique()

    def get_subject_data(self, subject_id: str, domain: str):
        """
        Get the data for a subject for a given domain
        """
        if subject_id not in self.get_subjects():
            raise ValueError(f"Subject {subject_id} does not exist")
        dataset = self._connector.load_cdiscpilot_dataset(domain)
        dataset = dataset[dataset.USUBJID == subject_id]
        return dataset

    def get_subject_dm(self, subject_id: str):
        """
        Get the demographics for a subject from the dataset
        """
        return self.get_subject_data(subject_id, "DM")

    def get_subject_sv(self, subject_id: str):
        """
        Get the demographics for a subject from the dataset
        """
        return self.get_subject_data(subject_id, "SV")

    def parse_dataset(self, dataset_name: str):
        """
        Parse a CDISC Pilot Dataset
        """
        if not os.path.exists(os.path.join("config", f"{dataset_name}.yml")):
            print("Unable to process configuration file")
        config = Configuration.from_file(os.path.join("config", f"{dataset_name}.yml"))
        _columns = [x for x in config.columns()]
        dataset = self._connector.load_cdiscpilot_dataset(dataset_name)
        for offset, record in enumerate(dataset.iterrows()):
            
            # generate a patient resource
            patient = self._generate_patient(record.USUBJID)
            # generate a bundle
            bundle = Bundle()
            # add the patient to the bundle
            bundle.add_entry(patient)
            # add the bundle to the content
            self.content.add_entry(bundle)

    def _generate_patient(self, subject_id: str) -> Patient:
        """
        Generate a Patient resource
        """
        # Use a hash id for the Patient Resource
        _patient_id = hashlib.md5(subject_id.encode('utf-8')).hexdigest()
        dm = self.get_subject_dm(subject_id)
        patient = Patient(id=_patient_id)
        return patient

    def dump_subject(self, subject_id: str, domains: list[str]):
        if subject_id not in self.get_subjects():
            raise ValueError(f"Subject {subject_id} does not exist")
        subject = self.get_subject(subject_id)
        # the bundle will include the ResearchStudy, ResearchSubject, and Patient resources
        pass

    def parse_sv(self, subject_id: str):
        """
        Parse the SV dataset for a subject
        """
        if subject_id not in self.get_subjects():
            raise ValueError(f"Subject {subject_id} does not exist")
        # the bundle will include the ResearchStudy, ResearchSubject, and Patient resources
        subject = self.get_subject(subject_id)
        subject_hash_id = hashlib.md5(subject_id.encode('utf-8')).hexdigest()
        # slice the dataset
        sv = self.get_subject_sv(subject_id)
        for record in sv.itertuples():
            visit_num = record.VISITNUM
            plan_def_id = f"H2Q-MC-LZZT-Study-Visit-{visit_num}"
            care_plan_id = f"{subject_id}-{visit_num}"
            care_plan = CarePlan(id=care_plan_id)
            care_plan.status = CarePlan.STATUS_COMPLETED
            care_plan.intent = CarePlan.INTENT_ORDER
            care_plan.subject = Reference(reference=f"Patient/{subject_hash_id}")
            encounter = Encounter(status="finished",
                                  class_fhir=Coding(code="IMP", system="http://hl7.org/fhir/v3/ActCode"))
            encounter.id = f"{record.USUBJID}-{record.VISITNUM}-"
            encounter.subject = Reference(reference=f"Patient/{subject_hash_id}")
            encounter.basedOn = Reference(reference=f"ServiceRequest/{care_plan_id}")
            period = {}
            if record.SVSTDTC:
                period["start"] = record.SVSTDTC
            if record.SVENDTC:
                period["end"] = record.SVENDTC
            encounter.period = period

            # add the Service Request
            service_request = ServiceRequest(intent="order",)


"""
            if subject_visit.USUBJID not in subjects:
                patient = Patient()
                patient.id = record.USUBJID
                subject = ResearchSubject(status="off-study", 
                    individual = Reference(reference=f"Patient/{patient.id}") , 
                    study = Reference(reference=f"ResearchStudy/{study.id}"))
                subject.id = record.USUBJID
                subjects[record.USUBJID] = subject
            subject = subjects[record.USUBJID]
"""