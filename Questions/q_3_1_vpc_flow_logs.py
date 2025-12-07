
import boto3
import os
import sys
sys.path.append("./Questions")
from dotenv import load_dotenv

from q1_vpc import *


load_dotenv()
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")
BUCKET_NAME = "polystudents3-tp4-1989922"
BUCKET_ARN = os.getenv("BUCKET_ARN")

def create_vpc_flow_logs(ec2_client, vpc_id):
    flow_logs_response = ec2_client.create_flow_logs(
        ResourceType='VPC',
        ResourceIds=[vpc_id],
        TrafficType = 'REJECT',
        LogDestinationType = 's3',
        LogDestination = f"{BUCKET_ARN}/tp4-vpc-flow-logs/",
        TagSpecifications=[
        {
            'ResourceType': 'vpc-flow-log',
            'Tags': [
                {
                    'Key': 'vpc-flow-logs',
                    'Value': 'TP4-VPC-Flow-Logs'
                },
            ]
        },
    ],
    )

    flow_ids = flow_logs_response
    print("VPC Flow Log IDs:", flow_ids)
    return flow_ids


if __name__ == "__main__":
    ec2_client = boto3.client('ec2', 
                            region_name='us-east-1',        
                            aws_access_key_id=ACCESS_KEY,
                            aws_secret_access_key=SECRET_KEY,
                        )
    # Create VPC Template
    vpc_id = create_vpc(ec2_client)

    # Add Public and Private Subnets to VPC
    public_subnet1_id, public_subnet2_id = create_public_subnets(ec2_client, vpc_id)
    private_subnet1_id, private_subnet2_id = create_private_subnets(ec2_client, vpc_id)

    # Add Internet Gateway to VPC
    internet_gateway_id = create_internet_gateway(ec2_client, vpc_id)

    # Create NAT Gateway in Public Subnet 1 and Public Subnet 2
    nat_gateway1_id = create_nat_gateway(ec2_client, public_subnet1_id)
    nat_gateway2_id = create_nat_gateway(ec2_client, public_subnet2_id)

    # Create Route Table and Public Routes to Subnets
    public_route_table_id = create_public_route_table(ec2_client, vpc_id, internet_gateway_id, public_subnet1_id, public_subnet2_id)
    private_route_table1_id, private_route_table2_id = create_private_route_table(ec2_client, vpc_id, nat_gateway1_id, nat_gateway2_id, private_subnet1_id, private_subnet2_id)

    # Create Security Group
    security_group_id = create_security_group(ec2_client, vpc_id)

    # Create VPC Flow Logs
    flow_ids = create_vpc_flow_logs(ec2_client, vpc_id)