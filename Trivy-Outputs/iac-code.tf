terraform {
    required_providers {
        aws = {
            source = "hashicorp/aws"
            version = "~> 3.0"
        }
    }
}

provider "aws" {
    region = "us-east-1"
}

resource "aws_s3_bucket" "S3Bucket" {
    bucket = "polystudents3-boto3-1584966-source"
}

resource "aws_vpc" "EC2VPC" {
    cidr_block = "10.0.0.0/16"
    enable_dns_support = true
    enable_dns_hostnames = true
    instance_tenancy = "default"
    tags = {
        Name = "polystudent-vpc-boto3"
    }
}

resource "aws_subnet" "EC2Subnet" {
    availability_zone = "us-east-1b"
    cidr_block = "10.0.144.0/24"
    vpc_id = "${aws_vpc.EC2VPC.id}"
    map_public_ip_on_launch = false
}

resource "aws_subnet" "EC2Subnet2" {
    availability_zone = "us-east-1a"
    cidr_block = "10.0.128.0/24"
    vpc_id = "${aws_vpc.EC2VPC.id}"
    map_public_ip_on_launch = false
}

resource "aws_subnet" "EC2Subnet3" {
    availability_zone = "us-east-1b"
    cidr_block = "10.0.16.0/24"
    vpc_id = "${aws_vpc.EC2VPC.id}"
    map_public_ip_on_launch = true
}

resource "aws_subnet" "EC2Subnet4" {
    availability_zone = "us-east-1a"
    cidr_block = "10.0.0.0/24"
    vpc_id = "${aws_vpc.EC2VPC.id}"
    map_public_ip_on_launch = true
}

resource "aws_internet_gateway" "EC2InternetGateway" {
    tags = {
        Name = "polystudent-vpc-boto3 IGW"
    }
    vpc_id = "${aws_vpc.EC2VPC.id}"
}

resource "aws_eip" "EC2EIP" {
    vpc = true
}

resource "aws_eip" "EC2EIP2" {
    vpc = true
}

resource "aws_route_table" "EC2RouteTable" {
    vpc_id = "${aws_vpc.EC2VPC.id}"
    tags = {
        Name = "polystudent-vpc-boto3 Private Route"
    }
}

resource "aws_route_table" "EC2RouteTable2" {
    vpc_id = "${aws_vpc.EC2VPC.id}"
    tags = {
        Name = "polystudent-vpc-boto3 Public Route"
    }
}

resource "aws_route_table" "EC2RouteTable3" {
    vpc_id = "${aws_vpc.EC2VPC.id}"
    tags = {
        Name = "polystudent-vpc-boto3 Private Route"
    }
}

resource "aws_route" "EC2Route" {
    destination_cidr_block = "0.0.0.0/0"
    nat_gateway_id = "nat-049d8d38b13a9382f"
    route_table_id = "rtb-044a80e6642628b9c"
}

resource "aws_route" "EC2Route2" {
    destination_cidr_block = "0.0.0.0/0"
    gateway_id = "igw-0f421c4eb16c9a7a4"
    route_table_id = "rtb-0cb6c018b95d3c7c4"
}

resource "aws_route" "EC2Route3" {
    destination_cidr_block = "0.0.0.0/0"
    nat_gateway_id = "nat-02fb71fea687d18ae"
    route_table_id = "rtb-0a2005c4c1560bd5c"
}

resource "aws_nat_gateway" "EC2NatGateway" {
    subnet_id = "subnet-0caef12a92edad9f0"
    tags = {
        Name = "polystudent-vpc-boto3 NAT Gateway"
    }
    allocation_id = "eipalloc-0cc9a50e266588e57"
}

resource "aws_nat_gateway" "EC2NatGateway2" {
    subnet_id = "subnet-0a1540ab55fed475b"
    tags = {
        Name = "polystudent-vpc-boto3 NAT Gateway"
    }
    allocation_id = "eipalloc-08a90b21f986ba308"
}
