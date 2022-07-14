from .base_transcriber import BaseTranscriber
from .enums import Lang, Vendor
from .transcription import Transcription, TranscriptionWord

from .utils.aws_waiter import TranscribeCompleteWaiter

import hashlib
import logging

import requests
import boto3


logger = logging.getLogger(__name__)


class AwsTranscriber(BaseTranscriber):
    def __init__(self, access_key: str, secret_access_key: str, region: str, bucket: str, timeout=180):
        self.__transcriber = boto3.client('transcribe', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key, region_name=region)
        self.__region = region
        self.__bucket = bucket
        self.__timeout = timeout

    def delete_job(self, job_name):
        try:
            return self.__transcriber.delete_transcription_job(TranscriptionJobName=job_name)
        except:
            logging.error(f'Failed to delete job. JobName={job_name}')

    def get_job(self, job_name):
        return self.__transcriber.get_transcription_job(TranscriptionJobName=job_name)

    @staticmethod
    def get_transcription_result(job):
        if job['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
            save_json_uri = job['TranscriptionJob']['Transcript']['TranscriptFileUri']

            try:
                pydict = requests.get(save_json_uri).json()
            except:
                return None

            transcripts = [transcript['transcript'] for transcript in pydict['results']['transcripts']]
            confidence = 0
            words = []
            for item in pydict['results']['items']:
                word = item['alternatives'][0]
                if item['type'] == 'punctuation' and len(words):
                    words[-1].word += word['content']
                else:
                    confidence += float(word['confidence'])
                    words.append(TranscriptionWord(word['content'], float(item['start_time']), float(item['end_time'])))
            confidences = [round(confidence / len(words), 2) if len(words) > 0 else 0]
            return Transcription(transcripts, confidences, words, vendor=Vendor.AWS.value)

    def transcribe(self, src: str, lang: Lang):
        job_name = str(hashlib.sha256(src.encode()).hexdigest())
        uri = f'https://{self.__bucket}.s3.{self.__region}.amazonaws.com/{src}'
        logging.info(f'Started to transcribe. [AWS] JobName={job_name}')

        try:
            self.__transcriber.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': uri},
                MediaFormat='wav',
                LanguageCode=lang.value
            )

            waiter = TranscribeCompleteWaiter(self.__transcriber, timeout=self.__timeout)
            waiter.wait(job_name=job_name)
            job = self.get_job(job_name)
            result = self.get_transcription_result(job)
            logging.info(f'Transcribing is completed [AWS] JobName={job_name}')
            return result
        except Exception as e:
            logging.error(f'Failed to transcribe. [AWS] JobName={job_name}')
            return None
        finally:
            self.delete_job(job_name)
