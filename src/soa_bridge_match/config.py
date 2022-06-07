
import pandas as pd
from typing import List

import yaml


class Configuration:

    def __init__(self, config) -> None:
        self._config = config
    
    @classmethod
    def from_file(cls, filename: str) -> "Configuration":
        """
        Load a configuration from a file
        """
        with open(filename, "r") as f:
            config = yaml.safe_load(f)
        return cls(**config)
    
    def columns(self):
        for column in self._config["columns"]:
            yield column
    
    def keys(self) -> List[str]:
        return self._config["keys"]


LBCAT = {'HEMATOLOGY'}

class TestCodeMapper:
    
    def __init__(self, config: Configuration):
        self._config = config
        self._dataset = None
    
    @property
    def dataset(self):
        if not self._dataset:
            self._dataset = pd.load_csv("resources/LOINC_to_LB_Mapping Document_FINAL.csv")
        return self._dataset

    def map(self, lbtestcd: str, lbcat: str) -> str:
        """
        Map a code to a test
        """
        if lbcat == "HEMATOLOGY":
            system = ('Ser/Plas', 'Plas', 'Bld')
        elif lbcat == "UNRINALYSIS":
            system = ('Urine')
        elif lbcat == "CHEMISTRY":
            system = ('Ser/Plas', 'Serum', 'Ser', 'Ser/Plas/Bld')
    