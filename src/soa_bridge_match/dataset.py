from __future__ import annotations

import datetime
import pandas as pd
import numpy as np
import hashlib
from math import floor
import random
import time
from typing import Optional

from fhir.resources.bundle import Bundle
from fhir.resources.careplan import CarePlan
from fhir.resources.coding import Coding
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.dosage import Dosage
from fhir.resources.fhirtypes import (
    DosageDoseAndRateType,
    ObservationReferenceRangeType,
)
from fhir.resources.encounter import Encounter
from fhir.resources.fhirtypes import EncounterHospitalizationType
from fhir.resources.identifier import Identifier
from fhir.resources.patient import Patient
from fhir.resources.period import Period
from fhir.resources.reference import Reference
from fhir.resources.element import Element
from fhir.resources.quantity import Quantity
from fhir.resources.servicerequest import ServiceRequest
from fhir.resources.medicationadministration import MedicationAdministration
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.observation import Observation
import pytz


from .bundler import SourcedBundle
from .connector import Connector


def hh(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def to_datetime(date) -> datetime.datetime:
    """
    Converts a numpy datetime64 object to a python datetime object 
    Input:
      date - a np.datetime64 object
    Output:
      DATE - a python datetime object
    """
    timestamp = ((date - np.datetime64('1970-01-01T00:00:00'))
                 / np.timedelta64(1, 's'))
    return datetime.datetime.utcfromtimestamp(timestamp)

class Naptha:
    def __init__(
        self, templatefile: Optional[str], templatecontent: Optional[Bundle] = None
    ) -> None:
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

    def dump(self, target_dir: Optional[str] = None, name_suffix: Optional[str] = None):
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

    def get_subject_ex(self, subject_id: str):
        """
        Get the exposure for a subject from the dataset
        """
        return self.get_subject_data(subject_id, "EX")

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

    def merge_ex(self, subject_id: Optional[str] = None, blinded: bool = False):
        """
        Merge a dataset into the template
        """
        if subject_id is None:
            for _subject_id in self.get_subjects():
                self.merge_ex(_subject_id)
            else:
                return
        if subject_id not in self.get_subjects():
            raise ValueError(f"Subject {subject_id} does not exist")
        print("Adding medications for {}".format(subject_id))

        patient_hash_id = hh(subject_id)
        # get the set of records for a subject
        ex = self.get_subject_ex(subject_id)
        dm = self.get_subject_dm(subject_id)
        sv = self.get_subject_sv(subject_id)
        visit_1 = sv[sv["VISITNUM"] == 1.0].SVSTDTC.values[0]
        # get the arm
        arm = dm.ARMCD.unique()[0]
        # Medication Request
        def get_med(arm):
            # returns the assigned medication for a given arm
            # or a placeholder if blinded
            medication = {
                "Pbo": "H2Q-MC-LZZT-LY246708-1",
                "Xan_Hi": "H2Q-MC-LZZT-LY246708-3",
                "Xan_Lo": "H2Q-MC-LZZT-LY246708-2",
                "Scrnfail": "",
            }
            if blinded:
                return "H2Q-MC-LZZT-LY246708-IP"
            return medication[arm]

        records = []
        medchoices = [
            {
                "code": "1116632",
                "display": "ticagrelor"
            },
            {
                "code": "613391",
                "display": "prasurgrel"
            },
            {
                "code": "32968",
                "display": "clopidogrel"
            }
        ]
        medchoice = random.choice(medchoices)
        medconcept = CodeableConcept(
                    coding=[
                        Coding(
                            code=medchoice["code"],
                            display=medchoice["display"],
                            system="http://www.nlm.nih.gov/research/umls/rxnorm",
                        )
                    ]
                )
        # Add the TTS-Test
        _tts_id = hh(f"{subject_id}-TTS-Test-Request")
        tts_test_request = MedicationRequest(
            id=_tts_id,
            status="active",
            medicationCodeableConcept=medconcept,
            subject=Reference(reference=f"Patient/{patient_hash_id}"),
            instantiatesCanonical=[f"ActivityDefinition/H2Q-MC-LZZT-Placebo-TTS-Admin"],
            intent="order",
            dosageInstruction=[
                Dosage(
                    route=CodeableConcept(
                        coding=[Coding(code="45890007")], text="Transdermal route"
                    ),
                    doseAndRate=[
                        DosageDoseAndRateType(
                            type=CodeableConcept(text="ordered"),
                            doseQuantity=Quantity(
                                value=1,
                                unit="TPATCH",
                                system="http://terminology.hl7.org/CodeSystem/v3-orderableDrugForm",
                            ),
                        )
                    ],
                )
            ],
        )
        self.content.add_resource(tts_test_request)
        _tts_admin_id = hh(f"{subject_id}-TTS-Test-Request")
        tts_admin = MedicationAdministration(
            id=_tts_admin_id,
            status="completed",
            medicationCodeableConcept=medconcept,
            subject=Reference(reference=f"Patient/{patient_hash_id}"),
            effectivePeriod=Period(
                start=visit_1,
                end=visit_1 + np.timedelta64(12, "h"),
            ),
            request=Reference(reference=f"MedicationRequest/{_tts_id}"),
        )
        self.content.add_resource(tts_admin)
        # get the medication request

        for offset, record in ex.iterrows():
            medchoice = random.choice(medchoices)
            medconcept = CodeableConcept(
                coding=[
                    Coding(
                        code=medchoice["code"],
                        display=medchoice["display"],
                        system="http://www.nlm.nih.gov/research/umls/rxnorm",
                    )
                ]
            )
            if pd.isna(record.EXENDTC):
                print("Subject", subject_id, f"has missing end date at {offset}")
                continue
            # calculate the duration for this dosing period
            delta = (record.EXENDTC - record.EXSTDTC).days
            # create a hash id for the medication request
            _mr_id = hh(f"{subject_id}-{record.EXSEQ}")
            mr = MedicationRequest(
                id=_mr_id,
                intent="order",
                status="active",
                medicationCodeableConcept=medconcept,
                subject=Reference(reference=f"Patient/{patient_hash_id}"),
            )
            print(
                f"Adding medication for {subject_id} from {record.EXSTDTC} to {record.EXENDTC} ({delta} days)"
            )
            if not isinstance(delta, (int,)):
                print(
                    "Subject",
                    subject_id,
                    f"has a weird delta for {record.EXSEQ} Start {record.EXSTDTC} End {record.EXENDTC}",
                )
                delta = floor(delta)
            # medication_request = MedicationRequest(id=_mr_id)
            for dt in range(delta):
                _date = record.EXSTDTC + datetime.timedelta(days=dt)
                _id = hh(f"{subject_id}-{record.EXSEQ}-{dt}")
                _stt = datetime.datetime.combine(_date, datetime.time(8, 0, 0), tzinfo=pytz.UTC)
                # add a little variation around the start/end for the medication
                if time.time() % 2 == 0:
                    _start_time = _stt - datetime.timedelta(
                        minutes=random.randint(0, 60)
                    )
                else:
                    _start_time = _stt + datetime.timedelta(
                        minutes=random.randint(0, 60)
                    )
                medication_admin = MedicationAdministration(
                    id=_id,
                    status="completed",
                    medicationCodeableConcept=medconcept,
                    subject=Reference(reference=f"Patient/{patient_hash_id}"),
                    effectivePeriod=Period(
                        start=_start_time,
                        end=_start_time + datetime.timedelta(hours=12),
                    ),
                )
                # get the medication request
                # medication_request = self._generate_medication_request(subject_id, _date, medication[arm])
                # add the medication request to the content
                # self.content.add_entry(medication_request)
                records.append(medication_admin)
        print(f"Generated {len(records)} medication administrations for {subject_id}")
        for record in records:
            self.content.add_resource(record)
        print("Done")
##

##
    def merge_unscheduled_visit(self, subject_id: str, visit_number: str):
        """
        Add an unscheduled visit for an individual
        """
        if subject_id not in self.get_subjects():
            raise ValueError(f"Subject {subject_id} does not exist")
        plan_def_id = "H2Q-MC-LZZT-Study-Unscheduled-Visit"
        patient_hash_id = hh(subject_id)
        # slice the dataset
        sv = self.get_subject_sv(subject_id)
        prior_visit = float(visit_number.split(".")[0])
        before = to_datetime(sv[sv.VISITNUM == prior_visit]["SVSTDTC"].values[0])
        visdt = before + datetime.timedelta(days=random.randint(1, 7))
        # generate the careplan
        care_plan_description = f"{patient_hash_id}-{visit_number}-CarePlan"
        care_plan_id = hh(care_plan_description)
        # create a care plan
        care_plan = CarePlan(
            id=care_plan_id,
            status="completed",
            intent="order",
            subject=Reference(reference=f"Patient/{patient_hash_id}"),
            instantiatesCanonical=[f"PlanDefinition/{plan_def_id}"],
            title=f"Subject {subject_id} {visit_number}",
        )
        care_plan.identifier = [Identifier(value=care_plan_description)]
        # bind the care plan - todo!
        # create the service request
        service_request_description = f"{patient_hash_id}-{visit_number}-ServiceRequest"
        service_request_id = hh(service_request_description)
        service_request = ServiceRequest(
            id=service_request_id,
            status="completed",
            intent="order",
            subject=Reference(reference=f"Patient/{patient_hash_id}"),
            basedOn=[Reference(reference=f"CarePlan/{care_plan_id}")],
        )
        service_request.identifier = [
            Identifier(value=f"{service_request_description}")
        ]
        _encounter_id = hh(f"{subject_id}-{visit_number}-Encounter")
        encounter = Encounter(
            id=_encounter_id,
            status="finished",
            class_fhir=Coding(code="IMP", system="http://hl7.org/fhir/v3/ActCode"),
            subject=Reference(reference=f"Patient/{patient_hash_id}"),
            basedOn=[Reference(reference=f"ServiceRequest/{service_request_id}")],
        )
        encounter.identifier = [Identifier(value=f"{care_plan_id}-Encounter")]
        period = {}
        period["start"] = visdt
        period["end"] = visdt
        encounter.period = Period(**period)
        # later
        # encounter.serviceProvider = Reference(reference=f"Organization/{self.org_id}")
        self.content.add_resource(care_plan)
        self.content.add_resource(service_request)
        self.content.add_resource(encounter)
        # add the observations
        # EG
        # VS
        for vs_obs in (
            ["8480-6", "Systolic blood pressure - standing", 110, 140, "mm[Hg]", 0],
            ["8454-1", "Diastolic blood pressure - standing", 65, 90, "mm[Hg]", 0],
            ["8867-4", "Body weight", 60, 100, "kg", 5],
            ["8310-5", "Body Temperature", 36.2, 38.1, "kg", 10],
            ["8867-4", "Heart Rate", 60, 100, "bpm", 0],
        ):
            # obs = self._generate_observation(
            #     subject_id,
            #     vs_obs[0],
            #     vs_obs[1],
            #     random.randint(vs_obs[2], vs_obs[3]),
            #     vs_obs[4],
            #     visdt,
            # )
            if isinstance(vs_obs[2], (int,)):
                _value = random.randint(vs_obs[2], vs_obs[3])
            else:
                _value = random.uniform(vs_obs[2], vs_obs[3])

            obs = Observation(
                id=hh(f"{patient_hash_id}-{visit_number}-{vs_obs[0]}"),
                status="final",
                effectiveDateTime = datetime.datetime.combine(
                    visdt, datetime.time(8, vs_obs[5], 0)
                ),
                code=CodeableConcept(
                    coding=[
                        Coding(
                            code=vs_obs[0], display=vs_obs[1], system="http://loinc.org"
                        )
                    ],
                    text=vs_obs[1],
                ),
                category=[
                    CodeableConcept(
                        coding=[
                            Coding(
                                code="vital-signs",
                                display="Vital Signs",
                                system="http://terminology.hl7.org/CodeSystem/observation-category",
                            )
                        ]
                    )
                ],
                encounter=Reference(reference=f"Encounter/{_encounter_id}"),
                subject=Reference(reference=f"Patient/{patient_hash_id}"),
                valueQuantity=Quantity(value=_value, unit=vs_obs[4]),
                basedOn=[Reference(reference=f"CarePlan/{care_plan_id}")],
            )
            self.content.add_resource(obs)
        # LB
        for lab_result in (
            ["20570-8", "Hematocrit [Volume Fraction] of Blood", 34, 48, "%"],
            ["2345-7", "Glucose [Mass/volume] in Serum or Plasma", 50, 250, "mg/dL"],
            ["718-7", "Hemoglobin [Mass/volume] in Blood", 11.5, 15.8, "g/dl"],
            [
                "2823-3",
                "Potassium [Moles/volume] in Serum or Plasma",
                3.4,
                5.4,
                "mEq/L",
            ],
        ):
            if isinstance(lab_result[2], (int,)):
                _value = random.randint(lab_result[2], lab_result[3])
            else:
                _value = random.uniform(lab_result[2], lab_result[3])
            _lb = Observation(
                id=hh(f"{patient_hash_id}-{visit_number}-{lab_result[0]}"),
                status="final",
                effectiveDateTime=datetime.datetime.combine(visdt, datetime.time(8, 15, 0)),
                code=CodeableConcept(
                    coding=[Coding(code=lab_result[0])], text=lab_result[1]
                ),
                category=[
                    CodeableConcept(
                        coding=[
                            Coding(
                                code="laboratory",
                                display="Laboratory",
                                system="http://terminology.hl7.org/CodeSystem/observation-category",
                            )
                        ]
                    )
                ],
                subject=Reference(reference=f"Patient/{patient_hash_id}"),
                referenceRange=[
                    ObservationReferenceRangeType(
                        low=Quantity(value=lab_result[2], unit=lab_result[4]),
                        high=Quantity(value=lab_result[3], unit=lab_result[4]),
                    )
                ],
                valueQuantity=Quantity(
                    value=_value,
                    unit=lab_result[4],
                ),
                encounter=Reference(reference=f"Encounter/{_encounter_id}"),
                basedOn=[Reference(reference=f"CarePlan/{care_plan_id}")],
            )

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
        pd_map = {
            "1.0": "H2Q-MC-LZZT-Study-Visit-1",
            "2.0": "H2Q-MC-LZZT-Study-Visit-2",
            "3.0": "H2Q-MC-LZZT-Study-Visit-3",
            "3.5": "H2Q-MC-LZZT-Study-Visit-3A",
            "4.0": "H2Q-MC-LZZT-Study-Visit-4",
            "5.0": "H2Q-MC-LZZT-Study-Visit-5",
            "6.0": "H2Q-MC-LZZT-Study-Visit-6",
            "7.0": "H2Q-MC-LZZT-Study-Visit-7",
            "8.0": "H2Q-MC-LZZT-Study-Visit-8",
            "8.1": "H2Q-MC-LZZT-Study-Visit-8T",
            "9.0": "H2Q-MC-LZZT-Study-Visit-9",
            "9.1": "H2Q-MC-LZZT-Study-Visit-9T",
            "10.0": "H2Q-MC-LZZT-Study-Visit-10",
            "10.1": "H2Q-MC-LZZT-Study-Visit-10T",
            "11.0": "H2Q-MC-LZZT-Study-Visit-11",
            "11.1": "H2Q-MC-LZZT-Study-Visit-11T",
            "12.0": "H2Q-MC-LZZT-Study-Visit-12",
            "13.0": "H2Q-MC-LZZT-Study-Visit-13",
            "101.0": "H2Q-MC-LZZT-Study-ET-14",
            "201.0": "H2Q-MC-LZZT-Study-RT-15",
            "501.0": "H2Q-MC-LZZT-Study-RASH-FU",
        }
        reasons = ["I21","I22","I23","I24","I25"]
        statuses = ["in-progress","finished"]
        dischargeCodes = [
            {
                "code": "home",
                "display": "Home"
            },
            {
                "code": "hosp",
                "display": "Hospice"
            },
            {
                "code": "exp",
                "display": "Expired"
            },
            {
                "code": "long",
                "display": "Long-term care"
            },
            {
                "code": "alt-home",
                "display": "Alternative home"
            },
        ]
        for record in sv.itertuples():
            if record.USUBJID not in self.content.subjects:
                continue
            print("Processing patient {} -> {}".format(record.USUBJID, record.VISITNUM))
            visit_num = record.VISITNUM
            if str(visit_num) not in pd_map:
                print("Visit {} is unscheduled".format(visit_num))
                plan_def_id = "H2Q-MC-LZZT-Study-Unscheduled-Visit"
            else:
                plan_def_id = pd_map[str(visit_num)]
            if plan_def_id is None:
                print("Ignoring visit", visit_num, "as Telephone contact")
                continue
            care_plan_description = f"{patient_hash_id}-{visit_num}-CarePlan"
            care_plan_id = hh(care_plan_description)
            # create a care plan
            care_plan = CarePlan(
                id=care_plan_id,
                status="completed",
                intent="order",
                subject=Reference(reference=f"Patient/{patient_hash_id}"),
                instantiatesCanonical=[f"PlanDefinition/{plan_def_id}"],
                title=f"Subject {record.USUBJID} {visit_num}",
            )
            care_plan.identifier = [Identifier(value=care_plan_description)]
            # bind the care plan - todo!
            # create the service request
            service_request_description = (
                f"{patient_hash_id}-{visit_num}-ServiceRequest"
            )
            service_request_id = hh(service_request_description)
            service_request = ServiceRequest(
                id=service_request_id,
                status="completed",
                intent="order",
                subject=Reference(reference=f"Patient/{patient_hash_id}"),
                basedOn=[Reference(reference=f"CarePlan/{care_plan_id}")],
            )
            service_request.identifier = [
                Identifier(value=f"{service_request_description}")
            ]
            discharge = random.choice(dischargeCodes)
            encounter = Encounter(
                id=hh(f"{care_plan_id}-{record.VISITNUM}-Encounter"),
                status=random.choice(statuses),
                hospitalization=EncounterHospitalizationType(
                    dischargeDisposition=CodeableConcept(
                        coding=[
                            Coding(
                                code=discharge["code"],
                                display=discharge["display"],
                                system="http://terminology.hl7.org/CodeSystem/discharge-disposition"
                            )
                        ]
                    ),
                    admitSource=CodeableConcept(
                        coding=[
                            Coding(
                                system="https://terminology.hl7.org/CodeSystem/admit-source",
                                code="emd",
                                display="From accident/emergency department"
                            )
                        ]
                    )
                ),
                reasonCode=[
                    CodeableConcept(
                        coding=[
                            Coding(
                                code=random.choice(reasons),
                                display="Laboratory",
                                system="http://hl7.org/fhir/ValueSet/encounter-reason",
                            )
                        ]
                    )
                ],
                class_fhir=Coding(code="IMP", system="http://hl7.org/fhir/v3/ActCode"),
                subject=Reference(reference=f"Patient/{patient_hash_id}"),
                basedOn=[Reference(reference=f"ServiceRequest/{service_request_id}")],
            )
            encounter.identifier = [Identifier(value=f"{care_plan_id}-Encounter")]
            period = {}
            if record.SVSTDTC:
                period["start"] = record.SVSTDTC.date()
            if record.SVENDTC:
                period["end"] = record.SVENDTC.date()
            if period:
                encounter.period = Period(**period)
            # later
            # encounter.serviceProvider = Reference(reference=f"Organization/{self.org_id}")
            self.content.add_resource(care_plan)
            self.content.add_resource(service_request)
            self.content.add_resource(encounter)
