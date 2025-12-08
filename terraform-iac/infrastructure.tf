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
    bucket = "polystudents3-tp4-1989922"
}

resource "aws_vpc" "EC2VPC" {
    cidr_block = "10.0.0.0/16"
    enable_dns_support = true
    enable_dns_hostnames = true
    instance_tenancy = "default"
    tags = {
        Name = "TP4"
    }
}

resource "aws_subnet" "EC2Subnet" {
    availability_zone = "us-east-1a"
    cidr_block = "10.0.0.0/24"
    vpc_id = "${aws_vpc.EC2VPC.id}"
    map_public_ip_on_launch = true
}

resource "aws_subnet" "EC2Subnet2" {
    availability_zone = "us-east-1b"
    cidr_block = "10.0.16.0/24"
    vpc_id = "${aws_vpc.EC2VPC.id}"
    map_public_ip_on_launch = true
}

resource "aws_subnet" "EC2Subnet3" {
    availability_zone = "us-east-1a"
    cidr_block = "10.0.128.0/24"
    vpc_id = "${aws_vpc.EC2VPC.id}"
    map_public_ip_on_launch = false
}

resource "aws_subnet" "EC2Subnet4" {
    availability_zone = "us-east-1b"
    cidr_block = "10.0.144.0/24"
    vpc_id = "${aws_vpc.EC2VPC.id}"
    map_public_ip_on_launch = false
}

resource "aws_internet_gateway" "EC2InternetGateway" {
    tags = {
        Name = "TP4"
    }
    vpc_id = "${aws_vpc.EC2VPC.id}"
}

resource "aws_eip" "EC2EIP" {
    vpc = true
}

resource "aws_eip_association" "EC2EIPAssociation" {
    allocation_id = "eipalloc-08b1a36487f59c4c7"
    network_interface_id = "eni-020d92b15080c92a2"
    private_ip_address = "10.0.0.209"
}

resource "aws_eip" "EC2EIP2" {
    vpc = true
}

resource "aws_eip_association" "EC2EIPAssociation2" {
    allocation_id = "eipalloc-0e645937148adce6e"
    network_interface_id = "eni-05f807e9c564dba2a"
    private_ip_address = "10.0.16.233"
}

resource "aws_nat_gateway" "EC2NatGateway" {
    subnet_id = "subnet-08f31a838f10604e5"
    tags = {
        Name = "TP4 NAT Gateway"
    }
    allocation_id = "eipalloc-0e645937148adce6e"
}

resource "aws_nat_gateway" "EC2NatGateway2" {
    subnet_id = "subnet-057e64d27a7ecc595"
    tags = {
        Name = "TP4 NAT Gateway"
    }
    allocation_id = "eipalloc-08b1a36487f59c4c7"
}

resource "aws_route" "EC2Route" {
    destination_cidr_block = "0.0.0.0/0"
    nat_gateway_id = "nat-0bf846a32c36184fd"
    route_table_id = "rtb-02668c575fd23057e"
}

resource "aws_route" "EC2Route2" {
    destination_cidr_block = "0.0.0.0/0"
    nat_gateway_id = "nat-0a712b5d0c4147672"
    route_table_id = "rtb-069915c96b9fb1a71"
}

resource "aws_route" "EC2Route3" {
    destination_cidr_block = "0.0.0.0/0"
    gateway_id = "igw-08c5560cd95135dcd"
    route_table_id = "rtb-0b365a756b1c12d1b"
}

resource "aws_route_table" "EC2RouteTable" {
    vpc_id = "${aws_vpc.EC2VPC.id}"
    tags = {
        Name = "TP4 Private Routes (AZ2)"
    }
}

resource "aws_route_table" "EC2RouteTable2" {
    vpc_id = "${aws_vpc.EC2VPC.id}"
    tags = {
        Name = "TP4 Private Routes (AZ1)"
    }
}

resource "aws_route_table" "EC2RouteTable3" {
    vpc_id = "${aws_vpc.EC2VPC.id}"
    tags = {}
}

resource "aws_route_table" "EC2RouteTable4" {
    vpc_id = "${aws_vpc.EC2VPC.id}"
    tags = {
        Name = "TP4 Public Routes"
    }
}

resource "aws_route_table_association" "EC2SubnetRouteTableAssociation" {
    route_table_id = "rtb-02668c575fd23057e"
    subnet_id = "subnet-042489294abff71c4"
}

resource "aws_route_table_association" "EC2SubnetRouteTableAssociation2" {
    route_table_id = "rtb-069915c96b9fb1a71"
    subnet_id = "subnet-0186303d3a419ead8"
}

resource "aws_route_table_association" "EC2SubnetRouteTableAssociation3" {
    route_table_id = "rtb-0b365a756b1c12d1b"
    subnet_id = "subnet-08f31a838f10604e5"
}

resource "aws_route_table_association" "EC2SubnetRouteTableAssociation4" {
    route_table_id = "rtb-0b365a756b1c12d1b"
    subnet_id = "subnet-057e64d27a7ecc595"
}
