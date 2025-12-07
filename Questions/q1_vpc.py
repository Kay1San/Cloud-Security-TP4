"Python Script to reproduce a VPC architecture in AWS through Boto3"

import boto3
import os
import json
from dotenv import load_dotenv

load_dotenv()
ENVIRONMENT_NAME = "TP4"
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

AVAILABILITYZONE1 = "us-east-1a"
AVAILABILITYZONE2 = "us-east-1b"


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

    return vpc_id

def create_public_subnets(ec2_client, vpc_id):

    response1 = ec2_client.create_subnet(
        VpcId=vpc_id,
        CidrBlock="10.0.0.0/24",
        AvailabilityZone=AVAILABILITYZONE1,
        TagSpecifications=[
            {
                'ResourceType': 'subnet',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': "public subnet in Availability Zone 1"
                    },
                ]
            },
        ],
    )

    response2 = ec2_client.create_subnet(
        VpcId=vpc_id,
        CidrBlock="10.0.16.0/24",
        AvailabilityZone=AVAILABILITYZONE2,
        TagSpecifications=[
            {
                'ResourceType': 'subnet',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': "public subnet in Availability Zone 2"
                    },
                ]
            },
        ],
    )

    subnet1_id = response1['Subnet']['SubnetId']
    subnet2_id = response2['Subnet']['SubnetId']

    ec2_client.modify_subnet_attribute(
        SubnetId=subnet1_id,
        MapPublicIpOnLaunch={'Value': True}
    )

    ec2_client.modify_subnet_attribute(
        SubnetId=subnet2_id,
        MapPublicIpOnLaunch={'Value': True}
    )

    print("Public Subnet 1 ID:", subnet1_id)
    print("Public Subnet 2 ID:", subnet2_id)

    return subnet1_id, subnet2_id


def create_private_subnets(ec2_client, vpc_id):

    response1 = ec2_client.create_subnet(
        VpcId=vpc_id,
        CidrBlock="10.0.128.0/24",
        AvailabilityZone=AVAILABILITYZONE1,
        TagSpecifications=[
            {
                'ResourceType': 'subnet',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': "private subnet in Availability Zone 1"
                    },
                ]
            },
        ],
    )

    response2 = ec2_client.create_subnet(
        VpcId=vpc_id,
        CidrBlock="10.0.144.0/24",
        AvailabilityZone=AVAILABILITYZONE2,
        TagSpecifications=[
            {
                'ResourceType': 'subnet',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': f"{ENVIRONMENT_NAME} Public Subnet (AZ2)"
                    },
                ]
            },
        ],
    )

    subnet1_id = response1['Subnet']['SubnetId']
    subnet2_id = response2['Subnet']['SubnetId']

    ec2_client.modify_subnet_attribute(
        SubnetId=subnet1_id,
        MapPublicIpOnLaunch={'Value': False}
    )

    ec2_client.modify_subnet_attribute(
        SubnetId=subnet2_id,
        MapPublicIpOnLaunch={'Value': False}
    )

    print("Private Subnet 1 ID:", subnet1_id)
    print("Private Subnet 2 ID:", subnet2_id)

    return subnet1_id, subnet2_id

def create_internet_gateway(ec2_client, vpc_id):

    response = ec2_client.create_internet_gateway(
        TagSpecifications=[
        {
            'ResourceType': 'internet-gateway',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': f'{ENVIRONMENT_NAME}'
                },
            ]
        },
    ],
    )

    ec2_client.attach_internet_gateway(
        InternetGatewayId=response['InternetGateway']['InternetGatewayId'],
        VpcId=vpc_id   
    )

    print("Internet Gateway ID:", response['InternetGateway']['InternetGatewayId'])

    return response['InternetGateway']['InternetGatewayId']

def create_nat_gateway(ec2_client, subnet_id):
    
    eip_response = ec2_client.allocate_address(Domain='vpc')
    allocation_id = eip_response['AllocationId']

    response = ec2_client.create_nat_gateway(
        SubnetId=subnet_id,
        AllocationId=allocation_id,
        TagSpecifications=[
            {
                'ResourceType': 'natgateway',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': f'{ENVIRONMENT_NAME} NAT Gateway'
                    },
                ]
            },
        ],
    )
    nat_gateway_id = response['NatGateway']['NatGatewayId']
    print("NAT Gateway ID:", nat_gateway_id)

    print(f"Waiting for NAT Gateway")
    waiter = ec2_client.get_waiter('nat_gateway_available')
    waiter.wait(NatGatewayIds=[nat_gateway_id])
    print(f"NAT Gateway is available.")

    return nat_gateway_id

def create_public_route_table(ec2_client, vpc_id, internet_gateway_id, subnet1_id, subnet2_id):

    route_table_response = ec2_client.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'route-table',
                'Tags': [
                    {'Key': 'Name', 
                     'Value': f'{ENVIRONMENT_NAME} Public Routes'
                     }
                    ]
            }
        ]
    )
    route_table_id = route_table_response['RouteTable']['RouteTableId']

    ec2_client.create_route(
        RouteTableId=route_table_id,
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId=internet_gateway_id
    )

    ec2_client.associate_route_table(
        RouteTableId=route_table_id,
        SubnetId=subnet1_id
    )

    ec2_client.associate_route_table(
        RouteTableId=route_table_id,
        SubnetId=subnet2_id
    )

    print("Public Route Table ID:", route_table_id)
    return route_table_id


def create_private_route_table(ec2_client, vpc_id, nat_gateway_id1, nat_gateway_id2, subnet1_id, subnet2_id):

    route_table1_response = ec2_client.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'route-table',
                'Tags': [
                    {'Key': 'Name', 
                     'Value': f'{ENVIRONMENT_NAME} Private Routes (AZ1)'
                     }
                    ]
            }
        ]
    )
    route_table1_id = route_table1_response['RouteTable']['RouteTableId']

    ec2_client.create_route(
        RouteTableId=route_table1_id,
        DestinationCidrBlock='0.0.0.0/0',
        NatGatewayId=nat_gateway_id1
    )

    ec2_client.associate_route_table(
        RouteTableId=route_table1_id,
        SubnetId=subnet1_id
    )

    route_table2_response = ec2_client.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'route-table',
                'Tags': [
                    {'Key': 'Name', 
                     'Value': f'{ENVIRONMENT_NAME} Private Routes (AZ2)'
                     }
                    ]
            }
        ]
    )
    route_table2_id = route_table2_response['RouteTable']['RouteTableId']

    ec2_client.create_route(
        RouteTableId=route_table2_id,
        DestinationCidrBlock='0.0.0.0/0',
        NatGatewayId=nat_gateway_id2
    )
    
    ec2_client.associate_route_table(
        RouteTableId=route_table2_id,
        SubnetId=subnet2_id
    )

    print("Private Route Table 1 ID:", route_table1_id)
    print("Private Route Table 2 ID:", route_table2_id)
    return route_table1_id, route_table2_id


def create_security_group(ec2_client, vpc_id):

    response = ec2_client.create_security_group(
        GroupName="polystudent-sg",
        Description="Security group allows SSH, HTTP, HTTPS, MSSQL, etc...",
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'security-group',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': "polystudent-sg"
                    },
                ]
            },
        ],
    )
    security_group_id = response['GroupId']

    ports = [22, 80, 443, 53, 1433, 5432, 3306, 3389, 1514, 9200]
    ip_permissions = []

    for port in ports:
        ip_permissions.append({
            'IpProtocol': 'tcp',
            'FromPort': port,
            'ToPort': port,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        })

    ec2_client.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=ip_permissions
    )

    print("Security Group ID:", security_group_id)

    return security_group_id


if __name__ == "__main__":
    ec2_client = boto3.client('ec2', 
                            region_name='us-east-1',        
                            aws_access_key_id=ACCESS_KEY,
                            aws_secret_access_key=SECRET_KEY,
                        )
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