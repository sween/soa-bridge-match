import re
from datetime import datetime
from typing import Optional, List

import requests
from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from fhir.resources.condition import Condition
from fhir.resources.medication import Medication
from fhir.resources.plandefinition import PlanDefinition, PlanDefinitionActionRelatedAction, PlanDefinitionAction
from fhir.resources.range import Range
from fhir.resources.researchstudy import ResearchStudy
from fhir.resources.researchsubject import ResearchSubject
from fhir.resources.encounter import Encounter
from fhir.resources.careplan import CarePlan
from fhir.resources.resource import Resource
from fhir.resources.servicerequest import ServiceRequest

"""
1. Identify the ResearchStudy (`ResearchStudy?_id=PROTOCOL_ID`)
2. Identify the Protocol Design **PlanDefinition** through the `protocol` field of the research study
3. Identify the initial activity:
   1. Iterate over the `action` elements in the **PlanDefinition** to extract the `relatedAction`  and `id` attributes (if present)
   2. The `relatedAction` these will have a reference to the `actionId` which is the `action.id` for the action we need to query
      1. Extract the `offsetRange` from the `relatedAction` and use this to define the `low` and `high` values for the `offset`
      2. Extract the `relationship` from the `relatedAction` and use this to define the `relationship`
   3. Record the `definitionUri` for the initial activity
4. Identify the Research Subject(`ResearchSubject?study=PROTOCOL_ID`)
5. Extract the Patient from the Research Subject through the `individual` field
6. Select the **CarePlan** for the Patient for the initial activity using the Patient id and the `definitionUri`
7. Select the **ServiceRequest** for the CarePlan (`ServiceRequest?patient=XXX&basedOn=CarePlan/TTTT`)
8. Select the **Encounter** for the ServiceRequest (`Encounter?patient=XXX&basedOn=ServiceRequest/YYYY`)
9. Extract the `period` from the `Encounter` and use this to define the `start`
10. For each of the related Actions use the `low` and `high` values to define the expected date
11. Identify the encounters
    1. For the naive example (CarePlan link not present) 
       1. Select the Encounters based on the expected times:
          1. For Green (`Encounter?patient=XXX&date={START}`) -> returns a result
          2. For Orange (`Encounter?patient=XXX&date=ge{START}&date=le{END}`) -> returns a result
          3. For Red we have no matching result
    2. For the CarePlan link present
       1. Select the Encounters based on the expected times:
          1. For Green (`Encounter?patient=XXX&date={START}&basedOn=ServiceRequest/TTTT`) -> returns a result
          2. For Orange (`Encounter?patient=XXX&date=ge{START}&date=le{END}&basedOn=ServiceRequest/TTTT`) -> returns a result
          3. For Red we have no matching result
"""


class StudyWindow:

    def __init__(self, baseurl: str, study_id: str):
        self._baseurl = baseurl if baseurl.endswith('/') else baseurl + '/'
        self.study_id = study_id
        self._visits = []
        self._session = None

    @property
    def client(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({'Accept': 'application/json'})
            self._session.headers.update({'Content-Type': 'application/json'})
        return self._session

    def _get(self, url) -> Optional[Resource]:
        all_url = self._baseurl + url
        print(f'Fetching {all_url}')
        response = self.client.get(all_url)
        if response.status_code == 200:
            if '?' in all_url:
                return Bundle.parse_obj(response.json())
            else:
                pattern = re.compile(r'([A-z]+)/(.*)')
                rtype, _ = pattern.match(url).groups()

                if rtype == 'Encounter':
                    return Encounter.parse_obj(response.json())
                elif rtype == 'ServiceRequest':
                    return ServiceRequest.parse_obj(response.json())
                elif rtype == 'CarePlan':
                    return CarePlan.parse_obj(response.json())
                elif rtype == 'ResearchSubject':
                    return ResearchSubject.parse_obj(response.json())
                elif rtype == 'Patient':
                    return Patient.parse_obj(response.json())
                elif rtype == 'PlanDefinition':
                    return PlanDefinition.parse_obj(response.json())
                else:
                    print(f"No idea how to work with this type: {rtype}")
        return None

    def _get_research_study(self) -> Optional[ResearchStudy]:
        url = f'ResearchStudy?identifier={self.study_id}'
        bundle = self._get(url)
        if bundle.total != 1:
            raise Exception(f'No ResearchStudy found for {self.study_id}')
        return bundle.entry[0].resource

    def _get_research_subjects(self) -> Optional[List[ResearchSubject]]:
        url = f'ResearchSubject?study={self.study_id}'
        bundle = self._get(url)
        if bundle.total == 0:
            raise Exception(f'No ResearchSubject found for {self.study_id}')
        return [x.resource for x in bundle.entry if x.resource.resource_type == 'ResearchSubject']

    def _get_research_subject(self, subject_id: str) -> Optional[ResearchSubject]:
        study = self._get_research_study()
        if study is None:
            return None
        url = f'ResearchSubject?_id={subject_id}&study={study.id}'
        bundle = self._get(url)
        if bundle.total != 1:
            raise Exception(f'No ResearchSubject {subject_id} found for {self.study_id} or more than one')
        return bundle.entry[0].resource

    def get_protocol(self) -> Optional[PlanDefinition]:
        research_study = self._get_research_study()
        if research_study is None:
            return None
        if research_study.protocol:
            # NOTE: assuming current design patter
            pdef = self._get(research_study.protocol[0].reference)
            return pdef
        return None

    def process_protocol(self, protocol: PlanDefinition) -> dict:
        """
        Extracts the protocol information and returns a dictionary with the planned encounters
        """
        ids = {}
        encounters = {}
        for idx, action in enumerate(protocol.action):  # type: int, PlanDefinitionAction
            design = {"definition": action.definitionUri,
                      "is_index": False,
                      "offset": idx}
            if action.id:
                ids[action.id] = action.definitionUri
            # assuming encounters
            # action: PlanDefinitionAction
            if getattr(action, 'relatedAction') != None:
                for rel_action in action.relatedAction:  # type: PlanDefinitionActionRelatedAction
                    if rel_action.actionId:
                        design['action_id'] = rel_action.actionId
                        if rel_action.relationship:
                            design['relationship'] = rel_action.relationship
                        if rel_action.offsetRange:
                            if rel_action.offsetRange:  # type: Range
                                design['offset_low'] = dict(value=int(rel_action.offsetRange.low.value),
                                                            unit=rel_action.offsetRange.low.code)
                                if rel_action.offsetRange.high is not None:
                                    design['offset_high'] = dict(value=int(rel_action.offsetRange.high.value),
                                                                 unit=rel_action.offsetRange.high.code)
            encounters[action.definitionUri] = design
        for encounter in encounters.values():
            if 'action_id' in encounter:
                ref = encounters[ids[encounter['action_id']]]
                ref['is_index'] = True
                encounters[ids[encounter['action_id']]] = ref

        return encounters

    def get_index_date(self, subject_id: str, protocol: dict) -> Optional[datetime]:
        """
        Returns the index date for a subject
        """
        research_subject = self._get_research_subject(subject_id)
        if research_subject is None:
            # can't find subject
            return None
        trigger_events = [x for x in protocol.values() if x['is_index']]
        print("Trigger events:", trigger_events)
        assert len(trigger_events) == 1, "Unable to id index event"
        idx_pd = self._get(trigger_events[0]['definition'])
        if idx_pd is None:
            raise Exception(f'No PlanDefinition found for {trigger_events[0]["definition"]}')

        # get the careplan
        cp_bnd = self._get(
            "CarePlan?patient={}&"
            "instantiates-canonical=PlanDefinition/{}".format(research_subject.individual.reference,
                                                              idx_pd.id))
        if cp_bnd.total != 1:
            raise Exception(f'No CarePlan found for {idx_pd.id}')
        cp = cp_bnd.entry[0].resource  # type: CarePlan
        print("CarePlan:", cp)
        # get the service request
        sr_bnd = self._get("ServiceRequest?patient={}&"
                           "based-on=CarePlan/{}".format(research_subject.individual.reference,
                                                         cp.id))
        if sr_bnd.total == 0:
            raise Exception(f'No ServiceRequest found for {cp.id}')
        sd = sr_bnd.entry[0].resource  # type: ServiceRequest
        # get the encounter
        enc_bnd = self._get("Encounter?patient={}&based-on=ServiceRequest/{}".format(
            research_subject.individual.reference, sd.id))
        if research_subject.indexDate:
            return research_subject.indexDate
        return None
