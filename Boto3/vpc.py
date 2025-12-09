import boto3
import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = "us-east-1"
AZ1 = "us-east-1a"
AZ2 = "us-east-1b"

ENV_NAME = os.getenv("ENVIRONMENT_NAME", "polystudent-vpc-boto3")
KEY_NAME = os.getenv("KEY_NAME", "cle-inf8102")
AWS_ACCESS_KEY = os.getenv("aws_access_key_id")
AWS_SECRET_ACCESS_KEY = os.getenv("aws_secret_access_key")
AWS_SESSION_TOKEN = os.getenv("aws_session_token")
BUCKET_ARN = os.getenv("bucket_arn")
AMI_ID = "ami-0ecb62995f68bb549"
INSTANCE_TYPE = "t3.micro"

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN,
    region_name=AWS_REGION
)   

ec2 = session.resource('ec2')
ec2_client = session.client('ec2')
cloudwatch = session.client('cloudwatch')


def create_vpc():
    
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc.wait_until_available()
    
    vpc.modify_attribute(EnableDnsSupport={'Value': True})
    vpc.modify_attribute(EnableDnsHostnames={'Value': True})
    
    vpc.create_tags(Tags=[{'Key': 'Name', 'Value': ENV_NAME}])
    
    print(f'VPC: {vpc.id}')
    return vpc

def create_public_subnet(vpc):
    
    public_subnet_01 = vpc.create_subnet(
        CidrBlock='10.0.0.0/24',
        AvailabilityZone=AZ1,
    )
    public_subnet_02 = vpc.create_subnet(
        CidrBlock='10.0.16.0/24',
        AvailabilityZone=AZ2,
    )
    
    public_subnet_01.create_tags(Tags=[
        {"Key": "Name", "Value": f"{ENV_NAME} Public Subnet (AZ1)"}
    ])
    public_subnet_02.create_tags(Tags=[
        {"Key": "Name", "Value": f"{ENV_NAME} Public Subnet (AZ2)"}
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
       
    print(f'Public_subnet_01 : {public_subnet_01.id},Public_subnet_02: {public_subnet_02.id}')
    return public_subnet_01, public_subnet_02

def create_private_subnet(vpc):
    
    private_subnet_01 = vpc.create_subnet(
        CidrBlock='10.0.128.0/24',
        AvailabilityZone=AZ1,
    )
    private_subnet_02 = vpc.create_subnet(
        CidrBlock='10.0.144.0/24',
        AvailabilityZone=AZ2,
    )

    private_subnet_01.create_tags(Tags=[
        {"Key": "Name", "Value": f"{ENV_NAME} Private Subnet (AZ1)"}
    ])
    private_subnet_02.create_tags(Tags=[
        {"Key": "Name", "Value": f"{ENV_NAME} Private Subnet (AZ2)"}
    ])

    print(f'Private_subnet_01: {private_subnet_01.id},Private_subnet_02: {private_subnet_02.id}')

    return private_subnet_01, private_subnet_02

def create_internet_gateway(vpc):
    
    igw = ec2.create_internet_gateway()
    igw.create_tags(Tags=[{'Key': 'Name', 'Value': f'{ENV_NAME} IGW'}])
    
    vpc.attach_internet_gateway(InternetGatewayId=igw.id, VpcId = vpc.id)
    print(f'Internet Gateway: {igw.id}')
    return igw


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
    print("NAT Gateway is now available")
    
    return nat_gateway_id

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
        GroupId=sg.id,
        IpPermissions=ip_permissions
    )

    print(f'Security Group: {sg.id}')
    return sg    

#Function that enable the use of VPC Flow Logs (Question 3.1)
def enable_vpc_flow_logs(vpc):
    
    bucket_arn = BUCKET_ARN
    
    response = ec2_client.create_flow_logs(
        ResourceIds=[vpc.id],
        ResourceType='VPC',
        TrafficType='REJECT',
        LogDestinationType='s3',
        LogDestination=bucket_arn,
    )
    print(f'VPC Flow Logs enabled for VPC: {vpc.id}')
    return response 
    
# Show the flow log function
def show_vpc_flow_logs(vpc):
    resp = ec2_client.describe_flow_logs(
        Filter=[
            {   'Name': 'resource-id',
                'Values': [vpc.id]
            },
        ]
    )
    print(f'Flow Logs for VPC {vpc.id}:')
    for flow_log in resp.get('FlowLogs',[]):
        print("  - FlowLogId:", flow_log["FlowLogId"],
              "| Status:", flow_log["FlowLogStatus"],
              "| TrafficType:", flow_log["TrafficType"],
              "| Dest:", flow_log["LogDestination"])

def lauch_instance(sg, public_subnet_01, public_subnet_02, private_subnet_01, private_subnet_02):
    
    # Same arguments for all instances
    common_args = {
        'ImageId': AMI_ID,
        'InstanceType': INSTANCE_TYPE,
        'MinCount': 1,
        'MaxCount': 1,
        'SecurityGroupIds': [sg.id],
        
        'IamInstanceProfile': {
            'Name': 'LabInstanceProfile'  
        },
    }
    
    # Launch instance in public subnet 1
    public_az1 = ec2.create_instances(
        SubnetId=public_subnet_01.id,
        KeyName=KEY_NAME,
        **common_args,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value':'Public Instance AZ1'}
                    ]
            }
        ]
    )[0]

    # Launch instance in public subnet 2
    public_az2 = ec2.create_instances(
        SubnetId=public_subnet_02.id,
        KeyName=KEY_NAME,
        **common_args,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value':'Public Instance AZ2'}
                    ]
            }
        ]
    )[0]

    # Launch instance in private subnet 1
    private_az1 = ec2.create_instances(
        SubnetId=private_subnet_01.id,
        KeyName=KEY_NAME,
        **common_args,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value':'Private Instance AZ1'}
                    ]
            }
        ]
    )[0]

    # Launch instance in private subnet 2
    private_az2 = ec2.create_instances(
        SubnetId=private_subnet_02.id,
        KeyName=KEY_NAME,
        **common_args,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value':'Private Instance AZ2'}
                    ]
            }
        ]
    )[0]

    instances = [public_az1, public_az2, private_az1, private_az2]
    
    for inst in instances:
        print(f'Instance launched: {inst.id} in Subnet: {inst.subnet_id}')

    return [inst.id for inst in instances]

# Create CloudWatch Alarms for Ingress Network Packets (Question 3.2)
def create_ingress_packet_alarms(instance_ids):
    
    for instance_id in instance_ids:
        alarm_name = f"IngressPacketsHigh-{instance_id}"
        cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            AlarmDescription=(
                "Alarm when average NetworkPacketsIn over the period "
                "exceeds 1000 packets per second."
            ),
            Namespace="AWS/EC2",
            MetricName="NetworkPacketsIn",
            Dimensions=[
                {"Name": "InstanceId", "Value": instance_id}
            ],
            Statistic="Average",
            Period=60,                 # 60s period
            EvaluationPeriods=1,
            Threshold=1000.0,          # 1000 pkts/sec
            ComparisonOperator="GreaterThanThreshold",
            TreatMissingData="notBreaching",
            ActionsEnabled=False     
        )
        print(f"Alarm {alarm_name} created for instance {instance_id}")

if __name__ == "__main__":
    # Creation VPC (Question 1)
    vpc = create_vpc()
    
    # Enable VPC Flow Logs (Question 3.1)
    enable_vpc_flow_logs(vpc)
    
    # Creation des subnets (Question 1)
    public_subnet_01, public_subnet_02 = create_public_subnet(vpc)
    private_subnet_01, private_subnet_02 = create_private_subnet(vpc)
    
    # Creation Igw (Question 1)
    igw = create_internet_gateway(vpc)
    
    # Creation des Public Route Tables (Question 1)
    create_public_route_table(vpc, igw, [public_subnet_01, public_subnet_02])
    
    # Creation des NAT Gateways (Question 1)
    nat_gateway_id_az1 = nat_gateway_setup(public_subnet_01)
    nat_gateway_id_az2 = nat_gateway_setup(public_subnet_02)
    
    # Creation des Private Route Tables (Question 1)
    create_private_route_table(vpc, nat_gateway_id_az1, private_subnet_01)
    create_private_route_table(vpc, nat_gateway_id_az2, private_subnet_02)
    
    # Creation des Security Groups (Question 1)
    sg = create_security_group(vpc)
    
    # Show VPC Flow Logs (Question 3.1)
    show_vpc_flow_logs(vpc)
    
    # Launch 4 EC2 instances with IAM role LabRole (Question 3.2)
    instance_ids = lauch_instance(sg, public_subnet_01, public_subnet_02, private_subnet_01, private_subnet_02,)
    
    # Create CloudWatch Alarms for Ingress Network Packets (Question 3.2)
    create_ingress_packet_alarms(instance_ids)