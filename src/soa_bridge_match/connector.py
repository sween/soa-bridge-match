from urllib.request import urlopen
import pandas as pd
from typing import Optional
from pandas import DataFrame

# define a prefix for the CDISC Pilot Datasets
PREFIX = "https://github.com/phuse-org/phuse-scripts/raw/master/data/sdtm/cdiscpilot01/"
PREFIX_UPDATED = "https://raw.githubusercontent.com/phuse-org/phuse-scripts/master/data/sdtm/updated_cdiscpilot/"

def check_link(url: str) -> bool:
    """
    ensure that the URL exists
    """
    # this will attempt to open the URL, and extract the response status code
    # - status codes are a HTTP convention for responding to requests
    # 200 - OK
    # 403 - Not authorized   
    # 404 - Not found   
    status_code = urlopen(url).getcode()
    return status_code == 200


# List of datasets
DATASETS = ["AE", "CM", "DM", "DS", "EX", "LB", "MH", "QS", "RELREC", "SC", "SE",
            "SUPPAE", "SUPPDM", "SUPPDS",
            "SUPPLB", "SV", "TA", "TV", "TI", "TS", "TV", "VS"]


class Connector:
    def __init__(self) -> None:
        self.__cache = {}
        self.__exists = {}

    def exists(self, domain_prefix: str):
        """
        check if a CDISC Pilot Dataset exists
        @param domain_prefix: the Domain Prefix for the Domain (eg DM, VS)
        """
        if domain_prefix not in self.__exists:
            # define the target for our read_sas directive
            target = f"{PREFIX}{domain_prefix.lower()}.xpt"
            # make sure that the URL exists first
            self.__exists[domain_prefix] = check_link(target)

        return self.__exists[domain_prefix]

    def load_cdiscpilot_dataset(self, domain_prefix: str, updated: bool = False) -> Optional[DataFrame]:
        """
        load a CDISC Pilot Dataset from the GitHub site
        @param domain_prefix: the Domain Prefix for the Domain (eg DM, VS)
        @param updated: if True, load the updated version of the dataset
        """
        _prefix = PREFIX_UPDATED if updated else PREFIX
        if domain_prefix not in self.__cache:
            # define the target for our read_sas directive
            target = f"{_prefix}{domain_prefix.lower()}.xpt"
            # make sure that the URL exists first
            if check_link(target):
                # let pandas work it out
                dataset = pd.read_sas(target, encoding="utf-8", format="xport")
                # need to infer datatypes
                for datecol in [x for x in dataset.columns if x.endswith("DTC")]:
                    dataset[datecol] = pd.to_datetime(dataset[datecol])
                self.__cache[domain_prefix] = dataset
            else:
                self.__cache[domain_prefix] = None
        return self.__cache[domain_prefix]
