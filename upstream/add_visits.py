import os
import sys

from soa_bridge_match.dataset import Naptha

def process_file(filename):
    # getting the bundle
    print("Processing file: {}".format(filename))
    ds = Naptha(filename)
    subject_id = os.path.basename(filename).split('_')[3]
    assert subject_id.startswith('01-701')
    ds.merge_sv(subject_id=subject_id)
    ds.content.dump()


def process_dir(dirname):
    for fname in os.listdir(dirname):
        if fname.endswith('.json'):
            process_file(os.path.join(dirname, fname))


if __name__ == "__main__":
    process_dir(sys.argv[1])
