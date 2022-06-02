from __future__ import annotations

import hashlib
import os
from typing import Optional

from fhir.resources.bundle import Bundle
from fhir.resources.careplan import CarePlan
from fhir.resources.coding import Coding
from fhir.resources.encounter import Encounter
from fhir.resources.identifier import Identifier
from fhir.resources.patient import Patient
from fhir.resources.period import Period
from fhir.resources.reference import Reference
from fhir.resources.servicerequest import ServiceRequest

from .bundler import SourcedBundle
from .connector import Connector


def hh(s: str) -> str:
    return hashlib.md5(s.encode('utf-8')).hexdigest()


class Naptha:

    def __init__(self, templatefile: Optional[str],
                 templatecontent: Optional[Bundle] = None) -> None:
        self._connector = Connector()
        self._subjects = {}
        self._patients = {}
        self._subjects = {}
        self._synthea = None
        # load the template
        if templatecontent:
            self._content = templatecontent
        else:
            self._content = SourcedBundle.from_bundle_file(templatefile)

    @property
    def content(self):
        return self._content

    def dump(self, target_dir: Optional[str] = None,
             name_suffix: Optional[str] = None):
        self._content.dump(target_dir, name_suffix)

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

    def get_subject_cm(self, subject_id: str):
        """
        Get the demographics for a subject from the dataset
        """
        return self.get_subject_data(subject_id, "CM")

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

    # def parse_dataset(self, dataset_name: str):
    #     """
    #     Parse a CDISC Pilot Dataset
    #     """
    #     if not os.path.exists(os.path.join("../../doc/config", f"{dataset_name}.yml")):
    #         print("Unable to process configuration file")
    #     config = Configuration.from_file(os.path.join("../../doc/config", f"{dataset_name}.yml"))
    #     _columns = [x for x in config.columns()]
    #     dataset = self._connector.load_cdiscpilot_dataset(dataset_name)
    #     for offset, record in enumerate(dataset.iterrows()):
    #         # generate a patient resource
    #         patient = self._generate_patient(record.USUBJID)
    #         # generate a bundle
    #         bundle = Bundle()
    #         # add the patient to the bundle
    #         bundle.add_entry(patient)
    #         # add the bundle to the content
    #         self.content.add_entry(bundle)

    # def _generate_patient(self, subject_id: str) -> Patient:
    #     """
    #     Generate a Patient resource
    #     """
    #     # Use a hash id for the Patient Resource
    #     _patient_id = hashlib.md5(subject_id.encode('utf-8')).hexdigest()
    #     dm = self.get_subject_dm(subject_id)
    #     patient = Patient(id=_patient_id)
    #     return patient

    def clone(self, subject_id: str) -> Naptha:
        cloned = self._content.clone_subject(subject_id)
        return Naptha(templatefile=None, templatecontent=cloned)

    def merge_sv(self, subject_id: Optional[str] = None):
        """
        Parse the SV dataset for a subject
        """
        if subject_id is None:
            for _subject_id in self.get_subjects():
                self.merge_sv(_subject_id)
            else:
                return
        if subject_id not in self.get_subjects():
            raise ValueError(f"Subject {subject_id} does not exist")
        # the bundle will include the ResearchStudy, ResearchSubject, and Patient resources
        patient_hash_id = hh(subject_id)
        # slice the dataset
        sv = self.get_subject_sv(subject_id)
        pd_map = {"1.0": "H2Q-MC-LZZT-Study-Visit-1",
                  "2.0": "H2Q-MC-LZZT-Study-Visit-2",
                  "3.0": "H2Q-MC-LZZT-Study-Visit-3",
                  "3.5": None,
                  "4.0": "H2Q-MC-LZZT-Study-Visit-4",
                  "5.0": "H2Q-MC-LZZT-Study-Visit-5",
                  "6.0": "H2Q-MC-LZZT-Study-Visit-6",
                  "7.0": "H2Q-MC-LZZT-Study-Visit-7",
                  "8.0": "H2Q-MC-LZZT-Study-Visit-8",
                  "8.1": None,
                  "9.0": "H2Q-MC-LZZT-Study-Visit-9",
                  "9.1": None,
                  "10.0": "H2Q-MC-LZZT-Study-Visit-10",
                  "10.1": None,
                  "11.0": "H2Q-MC-LZZT-Study-Visit-11",
                  "11.1": None,
                  "12.0": "H2Q-MC-LZZT-Study-Visit-12",
                  "13.0": "H2Q-MC-LZZT-Study-Visit-13",
                  "101.0": "H2Q-MC-LZZT-Study-ET-14",
                  "201.0": "H2Q-MC-LZZT-Study-RT-15",
                  "501.0": None}
        for record in sv.itertuples():
            if record.USUBJID not in self.content.subjects:
                continue
            print("Processing patient {} -> {}".format(record.USUBJID, record.VISITNUM))
            visit_num = record.VISITNUM
            if str(visit_num) not in pd_map:
                print("Skipping visit {}".format(visit_num))
                continue
            plan_def_id = pd_map[str(visit_num)]
            if plan_def_id is None:
                print("Ignoring visit", visit_num)
                continue
            care_plan_description = f"{patient_hash_id}-{visit_num}-CarePlan"
            care_plan_id = hh(care_plan_description)
            # create a care plan
            care_plan = CarePlan(id=care_plan_id,
                                 status="completed",
                                 intent="order",
                                 subject=Reference(reference=f"Patient/{patient_hash_id}"),
                                 instantiatesCanonical=[f"PlanDefinition/{plan_def_id}"],
                                 title=f"Subject {record.USUBJID} {visit_num}")
            care_plan.identifier = [Identifier(value=care_plan_description)]
            # bind the care plan - todo!
            # create the service request
            service_request_description = f"{patient_hash_id}-{visit_num}-ServiceRequest"
            service_request_id = hh(service_request_description)
            service_request = ServiceRequest(id=service_request_id,
                                             status="completed",
                                             intent="order",
                                             subject=Reference(reference=f"Patient/{patient_hash_id}"),
                                             basedOn=[Reference(reference=f"CarePlan/{care_plan_id}")])
            service_request.identifier = [Identifier(value=f"{service_request_description}")]
            encounter = Encounter(id=hh(f"{care_plan_id}-{record.VISITNUM}-Encounter"),
                                  status="finished",
                                  class_fhir=Coding(code="IMP",
                                                    system="http://hl7.org/fhir/v3/ActCode"),
                                  subject=Reference(reference=f"Patient/{patient_hash_id}"),
                                  basedOn=[Reference(reference=f"ServiceRequest/{service_request_id}")])
            encounter.identifier = [Identifier(value=f"{care_plan_id}-Encounter")]
            period = {}
            if record.SVSTDTC:
                period["start"] = record.SVSTDTC
            if record.SVENDTC:
                period["end"] = record.SVENDTC
            if period:
                encounter.period = Period(**period)
            # later
            # encounter.serviceProvider = Reference(reference=f"Organization/{self.org_id}")
            self.content.add_resource(care_plan)
            self.content.add_resource(service_request)
            self.content.add_resource(encounter)
