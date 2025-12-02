import boto3
import os

# -----------------------------
# PARAMÈTRES & ENV
# -----------------------------

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
AZ1 = "us-east-1a"
AZ2 = "us-east-1b"

ENV_NAME = _cfg.get("ENVIRONMENT_NAME", "polystudent-vpc-boto3")

KEY_NAME = _cfg.get("KEY_NAME", "cle_log8102")
AWS_ACCESS_KEY = _cfg.get("aws_access_key_id")
AWS_SECRET_ACCESS_KEY = _cfg.get("aws_secret_access_key")
AWS_SESSION_TOKEN = _cfg.get("aws_session_token")

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN,
    region_name=AWS_REGION
)   

ec2 = session.resource('ec2')
ec2_client = session.client('ec2')

# -----------------------------
# CRÉATION VPC & SUBNETS
# -----------------------------

def create_vpc():
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc.wait_until_available()
    
    vpc.modify_attribute(EnableDnsSupport={'Value': True})
    vpc.modify_attribute(EnableDnsHostnames={'Value': True})
    
    vpc.create_tags(Tags=[{'Key': 'Name', 'Value': ENV_NAME}])
    
    print(f'VPC: {vpc.id}')
    return vpc

def create_subnet(vpc):
    
    public_subnet_01 = vpc.create_subnet(
        CidrBlock='10.0.0.0/24',
        AvailabilityZone=AZ1,
    )
    public_subnet_02 = vpc.create_subnet(
        CidrBlock='10.0.16.0/24',
        AvailabilityZone=AZ2,
    )
    private_subnet_01 = vpc.create_subnet(
        CidrBlock='10.0.128.0/24',
        AvailabilityZone=AZ1,
    )
    private_subnet_02 = vpc.create_subnet(
        CidrBlock='10.0.144.0/24',
        AvailabilityZone=AZ2,
    )

    public_subnet_01.create_tags(Tags=[
        {"Key": "Name", "Value": f"{ENV_NAME} Public Subnet (AZ1)"}
    ])
    public_subnet_02.create_tags(Tags=[
        {"Key": "Name", "Value": f"{ENV_NAME} Public Subnet (AZ2)"}
    ])
    private_subnet_01.create_tags(Tags=[
        {"Key": "Name", "Value": f"{ENV_NAME} Private Subnet (AZ1)"}
    ])
    private_subnet_02.create_tags(Tags=[
        {"Key": "Name", "Value": f"{ENV_NAME} Private Subnet (AZ2)"}
    ])

    # MapPublicIpOnLaunch = true pour les subnets publics
    ec2_client.modify_subnet_attribute(
        SubnetId=public_subnet_01.id,
        MapPublicIpOnLaunch={'Value': True}
    )
    ec2_client.modify_subnet_attribute(
        SubnetId=public_subnet_02.id,
        MapPublicIpOnLaunch={'Value': True}
    )
       
    print(f'Public_subnet_01 : {public_subnet_01.id},Public_subnet_02: {public_subnet_02.id},Private_subnet_01: {private_subnet_01.id},Private_subnet_02: {private_subnet_02.id}')
    return public_subnet_01, public_subnet_02, private_subnet_01, private_subnet_02

def create_internet_gateway(vpc):
    igw = ec2.create_internet_gateway()
    igw.create_tags(Tags=[{'Key': 'Name', 'Value': f'{ENV_NAME} IGW'}])
    
    
    vpc.attach_internet_gateway(InternetGatewayId=igw.id)
    print(f'Internet Gateway: {igw.id}')
    return igw

def create_public_route_table(vpc, igw, public_subnets):
    route_table = vpc.create_route_table()
    route_table.create_tags(Tags=[{'Key': 'Name', 'Value': f'{ENV_NAME} Public Route'}])
    
    route_table.create_route(
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId=igw.id,
    )
    
    for subnet in public_subnets:
        route_table.associate_with_subnet(SubnetId=subnet.id)
        
    print(f'RouteTable-Public : {route_table.id}')
    return route_table

def nat_gateway_setup(public_subnet):
    eip = ec2_client.allocate_address(Domain='vpc')
    allocation_id = eip['AllocationId']
    print(f'Elastic IP Public Subnet : {allocation_id}')
    
    nat_gateway_response = ec2.meta.client.create_nat_gateway(
        SubnetId=public_subnet.id,
        AllocationId=allocation_id,
        TagSpecifications=[
            {
                'ResourceType': 'natgateway',
                'Tags': [{'Key': 'Name', 'Value': f'{ENV_NAME} NAT Gateway'}]
            },
        ],
    )
    
    nat_gateway_id = nat_gateway_response['NatGateway']['NatGatewayId']
    print(f'NAT Gateway : {nat_gateway_id} ')
    
    waiter = ec2_client.get_waiter('nat_gateway_available')
    waiter.wait(NatGatewayIds=[nat_gateway_id])
    
    return nat_gateway_id

def create_private_route_table(vpc, nat_gateway_id, private_subnet):
    route_table = vpc.create_route_table()
    route_table.create_tags(Tags=[{'Key': 'Name', 'Value': f'{ENV_NAME} Private Route'}])
    
    route_table.create_route(
        DestinationCidrBlock='0.0.0.0/0',
        NatGatewayId=nat_gateway_id,
    )
    
    route_table.associate_with_subnet(SubnetId=private_subnet.id)
    print(f'Private Route Table {route_table.id}')
    print(f'Subnet_Private: {private_subnet.id} -> NAT: {nat_gateway_id}')
    
    return route_table

def create_security_group(vpc):
    sg = ec2.create_security_group(
        GroupName='polystudent-sg-boto',
        Description='Security group allows SSH , HTTP , HTTPS , MSSQL , etc',
        VpcId=vpc.id
    )
    
    sg.create_tags(Tags=[{'Key': 'Name', 'Value': f'{ENV_NAME} SG'}])
    
    sg.authorize_ingress(
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },  
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp':'0.0.0.0/0'}]\
            },
            {   'IpProtocol': 'tcp',
                'FromPort': 443,
                'ToPort': 443,
                'IpRanges': [{'CidrIp':'0.0.0.0/0'}]
            },
            {   'IpProtocol': 'tcp',
                'FromPort': 1433,
                'ToPort': 1433,
                'IpRanges': [{'CidrIp':'0.0.0.0/0'}]
            },
            {   'IpProtocol': 'tcp',
                'FromPort': 3389,
                'ToPort': 3389,
                'IpRanges': [{'CidrIp':'0.0.0.0/0'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 53,
                'ToPort': 53,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },  
            {
                'IpProtocol': 'tcp',
                'FromPort': 5432,
                'ToPort': 5432,
                'IpRanges': [{'CidrIp':'0.0.0.0/0'}]\
            },
            {   'IpProtocol': 'tcp',
                'FromPort': 3306,
                'ToPort': 3306,
                'IpRanges': [{'CidrIp':'0.0.0.0/0'}]
            },
            {   'IpProtocol': 'tcp',
                'FromPort': 1514,
                'ToPort': 1514,
                'IpRanges': [{'CidrIp':'0.0.0.0/0'}]
            },
            {   'IpProtocol': 'tcp',
                'FromPort': 9200,
                'ToPort': 9200,
                'IpRanges': [{'CidrIp':'0.0.0.0/0'}]
            },
        ]
    )
    print(f'Security Group: {sg.id}')
    return sg    

if __name__ == "__main__":
    # Creation VPC
    vpc = create_vpc()
    
    # Creation des subnets
    public_subnet_01, public_subnet_02, private_subnet_01, private_subnet_02 = create_subnet(vpc)
    
    # Creation Igw
    igw = create_internet_gateway(vpc)
    
    # Creation des Public Route Tables
    create_public_route_table(vpc, igw, [public_subnet_01, public_subnet_02])
    
    # Creation des NAT Gateways 
    nat_gateway_id_az1 = nat_gateway_setup(public_subnet_01)
    nat_gateway_id_az2 = nat_gateway_setup(public_subnet_02)
    
    # Creation des Private Route Tables
    create_private_route_table(vpc, nat_gateway_id_az1, private_subnet_01)
    create_private_route_table(vpc, nat_gateway_id_az2, private_subnet_02)
    
    # Creation des Security Groups
    create_security_group(vpc)