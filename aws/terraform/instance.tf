# NVIDIA Terraform config for NGC AWS Tutorial.
# Copyright (c) 2017, NVIDIA CORPORATION.  All rights reserved.

# AWS Provider
provider "aws" {
  region = "${var.region}"

  # Only uncomment and place keys here if do not have the AWS CLI.
  # If you put your keys here, do NOT share this file with anyone.
  #access_key = "XXXXXXXX"
  #secret_key = "XXXXXXXX"
}

# Select the latest AMI in Marketplace.
data "aws_ami" "nv_volta_dl_ami" {
  owners = ["679593333241"]

  filter {
    name   = "name"
    values = ["NVIDIA Volta Deep Learning AMI*"]
  }

  most_recent = true
}

# To us spot instances rather than on demand:
# 1) Update the resource below to start with the commented out code.
# 2) Set your max price.
# 3) Update the outputs from "aws_instance" to "aws_spot_instance_request".
# https://www.terraform.io/docs/providers/aws/r/spot_instance_request.html
#
#resource "aws_spot_instance_request" "dl_instance" {
#  spot_price = "x.xx"           # Max price
#  wait_for_fulfillment = true   # wait up to 10m to be fulfilled

resource "aws_instance" "dl_instance" {
  ami           = "${data.aws_ami.nv_volta_dl_ami.id}"
  instance_type = "${var.instance-type}"

  tags {
    Name = "${var.name}"
  }

  root_block_device {
    volume_size           = "${var.ebs-size}"
    volume_type           = "gp2"
    delete_on_termination = true
  }

  key_name        = "${var.key-name}"
  security_groups = ["${var.security-group}"]
}
