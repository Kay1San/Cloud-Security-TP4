"Python Script to reproduce a VPC architecture in AWS through Boto3"

import boto3
import os
import json
from dotenv import load_dotenv

load_dotenv()
ENVIRONMENT_NAME = "TP4"
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")


def create_vpc(ec2_client):
    response = ec2_client.create_vpc(
        CidrBlock="10.0.0.0/16",
        TagSpecifications=[
            {
                'ResourceType': 'vpc',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': f"{ENVIRONMENT_NAME}"
                    }
                ]
            }
        ]
    )
    vpc_id = response['Vpc']['VpcId']
    print("VPC ID:", vpc_id)

    ec2_client.modify_vpc_attribute(
        VpcId=vpc_id,
        EnableDnsSupport={'Value': True}
    )
    
    ec2_client.modify_vpc_attribute(
        VpcId=vpc_id,
        EnableDnsHostnames={'Value': True}
    )


if __name__ == "__main__":
    ec2_client = boto3.client('ec2', 
                            region_name='us-east-1',        
                            aws_access_key_id=ACCESS_KEY,
                            aws_secret_access_key=SECRET_KEY,
                        )
    create_vpc(ec2_client)