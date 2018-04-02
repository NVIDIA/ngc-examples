# NVIDIA Terraform config for NGC AWS Tutorial.
# Copyright (c) 2017, NVIDIA CORPORATION.  All rights reserved.

# Terraform outputs

output "id" {
  value = "${aws_instance.dl_instance.id}"
}

output "key-name" {
  value = "${aws_instance.dl_instance.key_name}"
}

output "public-dns" {
  value = "${aws_instance.dl_instance.public_dns}"
}

output "ssh-cmd" {
  value = "${format("ssh -i %s%s.pem ubuntu@%s", var.ssh-key-dir,
    aws_instance.dl_instance.key_name,
    aws_instance.dl_instance.public_dns)}"
}
