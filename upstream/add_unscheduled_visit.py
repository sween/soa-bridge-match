import os
from re import S
import sys

from soa_bridge_match.dataset import Naptha


def process_file(filename: str, visit_number: str):
    # getting the bundle
    print("Processing file: {}".format(filename))
    ds = Naptha(filename)
    subject_id = os.path.basename(filename).split('_')[3]
    assert subject_id.startswith('01-701')
    ds.merge_unscheduled_visit(subject_id=subject_id, visit_number=visit_number)
    ds.content.dump()


def process_dir(dirname: str, subject_id: str, visit_number: str):
    for fname in os.listdir(dirname):
        if fname.endswith('.json') and subject_id in fname:
            process_file(os.path.join(dirname, fname), visit_number=visit_number)


def main(subject_bundle: str, subject_id: str, visit_number: str):
    process_dir(subject_bundle, subject_id, visit_number)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 add_unscheduled_visit.py <subject_bundle> <subject_id> <visit_number>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])