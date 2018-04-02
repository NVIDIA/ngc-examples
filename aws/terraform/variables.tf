# NVIDIA Terraform config for NGC AWS Tutorial.
# Copyright (c) 2017, NVIDIA CORPORATION.  All rights reserved.

# Check that the variables are correct for your usage.
# The defaults follow those in the NGC AWS Tutorial.

variable "name" {
  default     = "My Volta 1GPU"
  description = "Name to tag the instance"
}

variable "key-name" {
  default     = "my-key-pair"
  description = "AWS keypair to use"
}

variable "ssh-key-dir" {
  default     = "~/.ssh/"
  description = "Path to SSH keys - include ending '/'"
}

variable "region" {
  default     = "us-west-2"
  description = "AWS Region"
}

variable "instance-type" {
  default     = "p3.2xlarge"
  description = "AWS Instance Type"
}

variable "security-group" {
  default     = "my-sg"
  description = "Predefined Security Group"
}

variable "ebs-size" {
  default     = 32
  description = "Size of Root EBF partition, 32 GiB is default"
}
