import boto3
import os
import sys
sys.path.append("./Questions")
from dotenv import load_dotenv

from q1_vpc import *
from q2_s3 import *

load_dotenv()
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")
IAM_ARN = os.getenv("IAM_ARN")


def add_iam_role_ec2_instance(ec2_client, subnet_id, security_group_id):

    iam_response = ec2_client.run_instances(
        ImageId='ami-0ecb62995f68bb549',
        InstanceType = 't3.micro',
        SubnetId=subnet_id,
        SecurityGroupIds=[
            security_group_id,
        ],
        IamInstanceProfile={
            'Name': 'LabInstanceProfile'
        },
        MinCount =1,
        MaxCount =1,
    )

    instance_id = iam_response['Instances'][0]['InstanceId']
    print("Launched Instance ID:", instance_id)
    return instance_id


def add_cloudwatch_alarm(cloudwatch_client, subnets_instance_ids):
    
    for instance_id in subnets_instance_ids:
        cloudwatch_client.put_metric_alarm(
            AlarmName = 'IngressNumberofPackets',
            Statistic='Average',
            Period=60,
            Dimensions=[
                {"Name": "InstanceId", "Value": instance_id}
            ],
            Namespace="AWS/EC2",
            MetricName="NetworkPacketsIn",
            EvaluationPeriods=1,
            Threshold=1000.0,
            ComparisonOperator="GreaterThanThreshold",
            TreatMissingData="notBreaching",
            ActionsEnabled=False     
        )

        print(f"Alarm IngressNumberofPackets created for instance {instance_id}")

if __name__ == "__main__":
    ec2_client = boto3.client('ec2', 
                            region_name='us-east-1',        
                            aws_access_key_id=ACCESS_KEY,
                            aws_secret_access_key=SECRET_KEY,
                        )
    
    iam_client = boto3.client('iam',
                            region_name='us-east-1',
                            aws_access_key_id=ACCESS_KEY,
                            aws_secret_access_key=SECRET_KEY,
                            )
    
    cloudwatch_client = boto3.client('cloudwatch',
                            region_name='us-east-1',
                            aws_access_key_id=ACCESS_KEY,
                            aws_secret_access_key=SECRET_KEY,
                            )
    
    iam_response = iam_client.list_instance_profiles()
    profile = iam_response['InstanceProfiles']
    print('IAM Profiles : ', profile)
    print('IAM Role : ', profile[0]['Roles'])

    # Create VPC Architecture
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

    # Launch EC2 Instance with IAM Role on each Subnet
    instance_public_1_id = add_iam_role_ec2_instance(ec2_client, public_subnet1_id, security_group_id)
    instance_public_2_id = add_iam_role_ec2_instance(ec2_client, public_subnet2_id, security_group_id)
    instance_private_1_id = add_iam_role_ec2_instance(ec2_client, private_subnet1_id, security_group_id)
    instance_private_2_id = add_iam_role_ec2_instance(ec2_client, private_subnet2_id, security_group_id)

    subnets_instance_ids = [instance_public_1_id, instance_public_2_id, instance_private_1_id, instance_private_2_id]

    # Create a CloudWatch alarm for each subnet instance
    add_cloudwatch_alarm(cloudwatch_client, subnets_instance_ids)