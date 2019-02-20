import argparse
import os
import sys

import boto3

from beaker import beaker_client

AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
TOKEN = os.environ['BEAKER_CLIENT_TOKEN']
ADDRESS = "http://beaker-internal.allenai.org"

if __name__ == '__main__':

    parser = argparse.ArgumentParser()  # pylint: disable=invalid-name
    parser.add_argument('-d',
                        '--dataset',
                        type=str,
                        help='name of dataset (e.g. ds_nc05x1bc54o5)',
                        required=True)
    parser.add_argument('-o',
                        '--output_dir',
                        type=str,
                        help='output dir',
                        required=True)
    parser.add_argument("-f", "--files", nargs="+", type=str, required=True)
    parser.add_argument('-s',
                        '--s3',
                        action='store_true',
                        help='send output to s3 at this bucket')
    args = parser.parse_args()

    client = beaker_client.Client(ADDRESS, token=TOKEN)

    ds = beaker_client.Dataset(client, args.dataset)

    output = {}
    for file_ in ds.files:
        output[file_.path.replace('/', '', 1)] = file_

    files = ", ".join(output.keys())

    if not os.path.exists(args.output_dir):
        os.mkdir(args.output_dir)

    for file in args.files:
        assert file in output

    for file in args.files:
        if not os.path.exists(os.path.join(args.output_dir, file)):
            print(f"getting {file}...")
            output[file].download(output_dir=args.output_dir)
        else:
            print(f"{os.path.join(args.output_dir, file)} already exists, skipping...")

    if args.s3:
        s3 = boto3.resource('s3', region_name = 'us-west-2')
        bucket = s3.Bucket("suching-dev")
        for file in args.files:
            print(f"Uploading {file} to Amazon S3 bucket suching-dev")
            file = file.split("/")[-1]
            bucket.upload_file(os.path.join(args.output_dir, file), os.path.join("pretrained-models", args.output_dir, file))
