import boto3
import botocore
import os
import json
from dotenv import load_dotenv
import time

load_dotenv()

AWS_REGION = "us-east-1"
BUCKET_NAME_SOURCE = "polystudents3-boto3-1584966-source-2"
BUCKET_NAME_REPLICA = "polystudents3-boto3-1584966-replica-2"
KMS_KEY_ARN = os.getenv("KEY_NAME_S3_ARN")
AWS_ACCESS_KEY = os.getenv("aws_access_key_id")
AWS_SECRET_ACCESS_KEY = os.getenv("aws_secret_access_key")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")
AWS_SESSION_TOKEN = os.getenv("aws_session_token")
FILE = 'barbenoir.jpg'

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN, 
    region_name=AWS_REGION
)   


def create_bucket_exists(s3 , bucket_name):

    s3_response = s3.create_bucket(
        Bucket=bucket_name,
    )

    print('S3 Bucket Created \n')
    print("S3 Bucket Path:", s3_response['Location'], "\n")

    encryption_response = s3.put_bucket_encryption(
        Bucket=bucket_name,
        ServerSideEncryptionConfiguration = {
            'Rules': [
                {
                'ApplyServerSideEncryptionByDefault': {
                    'SSEAlgorithm': 'aws:kms',
                    'KMSMasterKeyID': KMS_KEY_ARN
                },
                }
            ]
        }
    )
    print("Added Encryption to the bucket \n")
    print('ENCRYPTION : ', encryption_response , '\n')

    public_access_block_response = s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': True,
            'BlockPublicPolicy': True,
            'IgnorePublicAcls': True,
            'RestrictPublicBuckets': True
        }
    )
    print("Added Public Access Block to the bucket \n")
    print('PUBLIC ACCESS BLOCK : ', public_access_block_response , '\n')

    version_config_response = s3.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={
            'Status': 'Enabled'
        }
    )
    print("Added Version Cofniguration to the bucket \n")
    print('VERSION CONFIG : ', version_config_response , '\n')

    
def upload_sample_file(s3, source_bucket, replica_bucket, key_name):
    
    response = s3.put_object(
        Bucket=source_bucket,
        Key=key_name,
        Body=b"This is a sample file for testing manual replication."
    )
    print(f"\nUploaded: {key_name}")

    
    version_id = response.get("VersionId")
    print(f"Version ID of uploaded object: {version_id}")

    
    copy_source = {
        "Bucket": source_bucket,
        "Key": key_name,
        "VersionId": version_id
    }

    s3.copy_object(
        Bucket=replica_bucket,
        Key=key_name,
        CopySource=copy_source
    )

    print(f"Replicated {key_name} → {replica_bucket}")

def show_objects(s3 , bucket_name):
    response = s3.list_objects_v2(Bucket=bucket_name)
    if 'Contents' in response:
        for obj in response['Contents']:
            print(f" - {obj['Key']} (VersionId: {obj.get('VersionId', 'N/A')})")
    else:
        print("No objects found in the bucket.")

def setup_cloudtrail(s3, ct):

    cloudtrail_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AWSCloudTrailAclCheck",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:GetBucketAcl",
                "Resource": f"arn:aws:s3:::{BUCKET_NAME_SOURCE}",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceArn": f"arn:aws:cloudtrail:{AWS_REGION}:{ACCOUNT_ID}:trail/polystudents3-1584966-cloudtrail"
                    }
                }
            },
            {
                "Sid": "AWSCloudTrailWrite",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:PutObject",
                "Resource": f"arn:aws:s3:::{BUCKET_NAME_SOURCE}/AWSLogs/{ACCOUNT_ID}/*",
                "Condition": {
                    "StringEquals": {
                        "s3:x-amz-acl": "bucket-owner-full-control",
                        "aws:SourceArn": f"arn:aws:cloudtrail:{AWS_REGION}:{ACCOUNT_ID}:trail/polystudents3-1584966-cloudtrail"
                    }
                }
            }
        ]
    }

    s3.put_bucket_policy(
        Bucket=BUCKET_NAME_SOURCE,
        Policy=json.dumps(cloudtrail_policy)
    )
    
    print(f"Added CloudTrail policy to S3 bucket for trail: polystudents3-1584966-cloudtrail")
    time.sleep(10)


    trail_response = ct.create_trail(
        Name="polystudents3-1584966-cloudtrail",
        S3BucketName=BUCKET_NAME_SOURCE,
        IsMultiRegionTrail=True,
    )
    
    print("Trail Created")
    print("TRAIL : ", trail_response , '\n')


    ct.start_logging(Name="polystudents3-1584966-cloudtrail")

    ct.put_event_selectors(
        TrailName="polystudents3-1584966-cloudtrail",
        EventSelectors=[
            {
                "ReadWriteType": "All",
                "IncludeManagementEvents": True,
                "DataResources": [
                    {
                        "Type": "AWS::S3::Object",
                        "Values": [
                            f"arn:aws:s3:::{BUCKET_NAME_SOURCE}/"
                        ],
                    }
                ],
            }
        ],
    )
    
    print(f"CloudTrail setup completed")
    
    
def main():

    s3 = session.client('s3')
    ct = session.client('cloudtrail')

    print("\n Creating and configuring S3 buckets")
    create_bucket_exists(s3 , BUCKET_NAME_SOURCE)
    create_bucket_exists(s3 , BUCKET_NAME_REPLICA)
    
    print("\n Upload a sample file and replicate it")
    upload_sample_file(s3 , BUCKET_NAME_SOURCE , BUCKET_NAME_REPLICA , FILE )
    
    print("\n Setting up CloudTrail")
    setup_cloudtrail(s3, ct)

if __name__ == "__main__":
    main()
