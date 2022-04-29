import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from soa_bridge_match import dataset


def process_file(filename):
    # getting the bundle
    print("Processing file: {}".format(filename))
    ds = dataset.Naptha(filename)
    ds.merge_sv()
    ds.content.dump()


def process_dir(dirname):
    for fname in os.listdir(dirname):
        if fname.endswith('.json'):
            process_file(os.path.join(dirname, fname))


if __name__ == "__main__":
    process_dir(sys.argv[1])
