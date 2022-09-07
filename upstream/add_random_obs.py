import os
import argparse
import sys

sys.path.append('../src')

from soa_bridge_match import dataset


def process_file(opts):
    # getting the bundle
    print("Processing file: {}".format(opts.filename))
    ds = dataset.Naptha(opts.filename)
    if opts.subject_id:
        dd = ds.clone_subject(opts.subject_id)
    else:
        dd = ds
    # type: dd: dataset.Naptha
    for i in range(opts.num_obs):
        if opts.obs_type == "laboratory":
            dd.content.add_lab_value()
        else:
            dd.content.add_vitals_value()
    ds.content.dump()


def process_dir(dirname):
    for fname in os.listdir(dirname):
        if fname.endswith('.json'):
            process_file(os.path.join(dirname, fname))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Add random observations to a dataset')
    parser.add_argument('-f', '--file', dest='filename', help='The file to process')
    parser.add_argument('-n', '--count', dest='num_obs', help='How many random observations to add', type=int, default=1)
    parser.add_argument('-t', '--type', dest='obs_type', help='The type of random observations to add',
                        default='laboratory', choices=['laboratory', 'vital-signs'])
    parser.add_argument('-s', '--subject-id', dest='subject_id', help='The subject id for the random observations',)
    opts = parser.parse_args()

