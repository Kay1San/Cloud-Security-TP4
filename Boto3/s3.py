import boto3
import botocore
import os
import json

# ------------- CONFIG -------------
ENV_FILE = os.getenv("ENV_FILE", "Boto3/.env")

def _read_dotenv(path: str) -> dict:
    vals = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return vals

_cfg = {**_read_dotenv(ENV_FILE), **os.environ}

AWS_REGION = "us-east-1"

BUCKET_NAME_SOURCE = "polystudents3-boto3-1584966-source"

BUCKET_NAME_REPLICA = "polystudents3-boto3-1584966-replica"

ROLE_ARN = _cfg.get("ROLE_ARN")

KMS_KEY_ARN = _cfg.get("kms_key_arn")
AWS_ACCESS_KEY = _cfg.get("aws_access_key_id")
AWS_SECRET_ACCESS_KEY = _cfg.get("aws_secret_access_key")
AWS_SESSION_TOKEN = _cfg.get("aws_session_token")

FILE = 'barbenoir.jpg'

print("AK:", bool(AWS_ACCESS_KEY))
print("SK:", bool(AWS_SECRET_ACCESS_KEY))
print("ST:", AWS_SESSION_TOKEN is not None, len(AWS_SESSION_TOKEN or ""))

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN,
    region_name=AWS_REGION
)   

s3 = session.client('s3')

ct = session.client('cloudtrail')

# ----------------------------------

def create_bucket_exists(s3 , BUCKET_NAME):

    create_kwargs = {
        "Bucket": BUCKET_NAME
    }

    try:
        s3.create_bucket(**create_kwargs)
        print(f"Bucket created: {BUCKET_NAME} in {AWS_REGION}")
    except botocore.exceptions.ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print(f"Bucket {BUCKET_NAME} already exists.")
        else:
            raise
    
    return BUCKET_NAME

def block_public_access(s3 , BUCKET_NAME):
    s3.put_public_access_block(
        Bucket=BUCKET_NAME,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    print("Public access fully blocked")


def enable_kms_encryption(s3 , BUCKET_NAME):
    s3.put_bucket_encryption(
        Bucket=BUCKET_NAME,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "aws:kms",
                        "KMSMasterKeyID": KMS_KEY_ARN,
                    }
                }
            ]
        },
    )
    print(f"KMS encryption enabled with key: {KMS_KEY_ARN}")


def enable_versioning(s3 , BUCKET_NAME):
    s3.put_bucket_versioning(
        Bucket=BUCKET_NAME,
        VersioningConfiguration={
            "Status": "Enabled"
        }
    )
    print("Versioning enabled")

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

def show_objects(s3 , BUCKET_NAME):
    response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    if 'Contents' in response:
        for obj in response['Contents']:
            print(f" - {obj['Key']} (VersionId: {obj.get('VersionId', 'N/A')})")
    else:
        print("No objects found in the bucket.")

def setup_cloudtrail():
    
    response = ct.create_trail(
        Name="polystudents3-1584966-cloudtrail",
        S3BucketName=BUCKET_NAME_SOURCE,
        IsMultiRegionTrail=True,
    )

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
                            "arn:aws:s3:::polystudents3-boto3-1584966-source/"
                        ],
                    }
                ],
            }
        ],
    )
    
    print(f"CloudTrail setup completed : {response}")
    
    
def main():

    print("\n Creating S3 buckets")
    create_bucket_exists(s3 , BUCKET_NAME_SOURCE)
    create_bucket_exists(s3 , BUCKET_NAME_REPLICA)
    
    print("\n Configuring S3 buckets")
    block_public_access(s3 , BUCKET_NAME_SOURCE)
    block_public_access(s3 , BUCKET_NAME_REPLICA)
    
    print("\n Enabling KMS encryption")
    enable_kms_encryption(s3, BUCKET_NAME_SOURCE)
    enable_kms_encryption(s3, BUCKET_NAME_REPLICA)
    
    print("\n Enabling versioning")
    enable_versioning(s3, BUCKET_NAME_SOURCE)
    enable_versioning(s3, BUCKET_NAME_REPLICA)
    
    print("\n Bucket created")
    
    print("\n Upload a sample file and replicate it")
    upload_sample_file(s3 , BUCKET_NAME_SOURCE , BUCKET_NAME_REPLICA , FILE )
    
    
    
    print("\n Setting up CloudTrail")
    setup_cloudtrail()

if __name__ == "__main__":
    main()
