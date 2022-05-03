import os
import random
from typing import Optional

from fhir.resources.bundle import Bundle
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.observation import Observation
from dotenv import load_dotenv

load_dotenv()


class SyntheaPicker:

    def __init__(self, path: Optional[str] = None):
        self.path = path if path else os.getenv('SYNTHEA_PATH')
        self._candidates = []
        self._cache = {}

    @property
    def candidates(self):
        if not self._candidates:
            self._candidates = [f for f in os.listdir(self.path) if
                                os.path.isfile(os.path.join(self.path, f)) and
                                os.path.splitext(os.path.join(self.path, f))[1] == '.json']
        return self._candidates

    def pick_file(self, file_name):
        return os.path.join(self.path, file_name)

    def get_pick(self):
        target = random.choice(self.candidates)
        print("Using {} for sample".format(target))
        bundle = Bundle.parse_file(self.pick_file(target))
        return bundle

    def _pick_observation_by_category(self, category: str) -> Observation:
        bundle = self.get_pick()
        _obs = []
        for entry in bundle.entry:
            if entry.resource.resource_type == 'Observation':
                resource = entry.resource  # type: Observation
                for code in resource.category:  # type: CodeableConcept
                    for coding in code.coding:
                        if coding.code == category:
                            _obs.append(resource)
        return random.choice(_obs)

    def get_lab_observation(self) -> Observation:
        return self._pick_observation_by_category('laboratory')

    def get_vital_observation(self) -> Observation:
        return self._pick_observation_by_category('vital-signs')
