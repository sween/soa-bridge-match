import os
import argparse

from soa_bridge_match.dataset import Naptha

def process_file(filename, blinded=False):
    # getting the bundle
    print("Processing file: {}".format(filename))
    ds = Naptha(filename)
    subject_id = os.path.basename(filename).split('_')[3]
    assert subject_id.startswith('01-701')
    ds.merge_ex(subject_id=subject_id, blinded=blinded)
    ds.content.dump()


def process_dir(dirname, blinded=False):
    for fname in os.listdir(dirname):
        if fname.endswith('.json'):
            process_file(os.path.join(dirname, fname), blinded=blinded)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='Path to the directory or file')
    parser.add_argument('--blinded', action='store_true', help='Blinded mode')
    opts = parser.parse_args()
    process_dir(opts.path, opts.blinded)
