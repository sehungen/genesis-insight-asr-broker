import datetime
import os

import boto3
import logging

from .base_downloader import BaseDownloader

logging.getLogger('urllib3').setLevel(logging.CRITICAL)


class AwsS3Downloader(BaseDownloader):
    def __init__(self, bucket_name, **aws_params):
        self._bucket_name = bucket_name
        self._s3 = boto3.client('s3',
                                aws_access_key_id=aws_params['aws_access_key_id'],
                                aws_secret_access_key=aws_params['aws_secret_access_key'],
                                )

    def _process_downloading(self, src_path, download_path) -> str:
        with open(download_path, 'wb') as f:
            logging.info('download from aws: %s, %s' % (self._bucket_name, src_path))
            self._s3.download_fileobj(self._bucket_name, src_path, f)

        return download_path

    def _process_uploading(self, src_path, upload_path):
        self._s3.upload_file(src_path, self._bucket_name, upload_path)

    def _process_delete(self, target_path):
        self._s3.delete_object(Bucket=self._bucket_name, Key=target_path)

    def _process_check(self, target_path) -> bool:
        return self._s3.head_object(Bucket=self._bucket_name, Key=target_path)


def main():
    aws_credentials = {
        'aws_access_key_id': '-',
        'aws_secret_access_key': '-',
    }
    target_dir = os.path.join(os.getcwd(), 'storage/temp')
    aws = AwsS3Downloader(bucket_name='viewinter-hr-dev', **aws_credentials)
    aws.download_file('LGU+/pretest/video/data/2019/08/13/b607f536-2d2d-4d94-939e-5cfa1bf78cd5.mp4', target_dir)


if __name__ == '__main__':
    main()
