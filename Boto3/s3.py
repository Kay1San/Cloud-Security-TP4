import boto3
import botocore
import os

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

BUCKET_NAME = _cfg.get("ENVIRONMENT_NAME", "polystudents3-boto3-1584966")

KMS_KEY_ARN = _cfg.get("kms_key_arn")
AWS_ACCESS_KEY = _cfg.get("aws_access_key_id")
AWS_SECRET_ACCESS_KEY = _cfg.get("aws_secret_access_key")
AWS_SESSION_TOKEN = _cfg.get("aws_session_token")

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

# ----------------------------------

def create_bucket_exists(s3):

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

def block_public_access(s3):
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


def enable_kms_encryption(s3):
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


def enable_versioning(s3):
    s3.put_bucket_versioning(
        Bucket=BUCKET_NAME,
        VersioningConfiguration={
            "Status": "Enabled"
        }
    )
    print("Versioning enabled")


def main():

    create_bucket_exists(s3)
    block_public_access(s3)
    enable_kms_encryption(s3)
    enable_versioning(s3)
    print("\n Bucket created")


if __name__ == "__main__":
    main()
