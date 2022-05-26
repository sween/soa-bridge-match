"""
Clones an existing subject.
"""
import argparse
import os
import sys


from soa_bridge_match import dataset
from soa_bridge_match import bundler


def process_file(filename):
    # getting the bundle
    print("Processing file: {}".format(filename))
    ds = dataset.Naptha(filename)
    ds.merge_sv()
    ds.content.dump()


def clone_subject(old_subject_bundle: str, new_subject_id: str):
    # getting the bundle
    bundle = bundler.SourcedBundle.from_bundle_file(old_subject_bundle)
    assert len(bundle.subjects) == 1, "Only one subject is allowed"
    old_subject_id = bundle.subjects[0]
    print("Cloning subject: {}".format(old_subject_id))
    clone = bundle.clone_subject(new_subject_id)
    fname = os.path.splitext(os.path.basename(old_subject_bundle))[0]
    ofname = fname.replace(old_subject_id, new_subject_id)
    dirname = os.path.dirname(old_subject_bundle)
    clone.dump(target_dir=dirname, name=ofname)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clones an existing subject.")
    parser.add_argument("old_subject_bundle", help="The subject to clone.")
    parser.add_argument("--subject-id", dest="new_subject_id", help="The new subject ID.")
    opts = parser.parse_args()
    if not opts.new_subject_id:
        parser.print_help()
        sys.exit(1)
    if not opts.old_subject_bundle:
        parser.print_help()
        sys.exit(1)
    if not os.path.exists(opts.old_subject_bundle):
        parser.print_help()
        sys.exit(1)

    clone_subject(opts.old_subject_bundle, opts.new_subject_id)