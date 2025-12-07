"Python Script to reproduce a AWS S3 Bucket through Boto3"


import boto3
import os
import json
from dotenv import load_dotenv

load_dotenv()
BUCKET_NAME = "polystudents3-tp4-1989922"
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
KMSMASTERKEYID = os.getenv("KMSMASTERKEYID")


def create_s3_bucket(s3_client):

    s3_response = s3_client.create_bucket(
        Bucket=BUCKET_NAME,
    )

    encryption_response = s3_client.put_bucket_encryption(
        Bucket=BUCKET_NAME,
        ServerSideEncryptionConfiguration = {
            'Rules': [
                {
                'ApplyServerSideEncryptionByDefault': {
                    'SSEAlgorithm': 'aws:kms',
                    'KMSMasterKeyID': KMSMASTERKEYID
                },
                }
            ]
        }
    )

    version_config_response = s3_client.put_bucket_versioning(
        Bucket=BUCKET_NAME,
        VersioningConfiguration={
            'Status': 'Enabled'
        }
    )

    public_access_block_response = s3_client.put_public_access_block(
        Bucket=BUCKET_NAME,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': True,
            'BlockPublicPolicy': True,
            'IgnorePublicAcls': True,
            'RestrictPublicBuckets': True
        }
    )

    print("S3 Bucket Path:", s3_response['Location'])

    
if __name__ == "__main__":
    s3_client = boto3.client(
        's3',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name='us-east-1'
    )

    create_s3_bucket(s3_client)


