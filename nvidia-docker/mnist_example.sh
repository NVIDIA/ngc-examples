#!/bin/bash
#
# mnist_example.sh                             10/15/2017 
#
# Copyright (c) 2017, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
# Example code to show how to run a container with nvidia-docker.
# This example does an MNIST training run.

usage() {
    echo ""
    echo "Synopsis: Demonstrate running a framework from NGC to do a MNIST training run."
    echo ""
    echo "Usage: $0 <framework> [tag]"
    echo ""
    echo "   framework:        Deep Learning framework to launch from NGC."
    echo "                     Valid choices are:"
    echo "                      - pytorch"
    echo "                      - tensorflow"
    echo ""
    echo "   tag (optional):   Version of the framework in NGC."
    echo "                     Default value is 17.10."
    echo ""
    exit 1
}

# Get arguments
if [ $# -lt 1 ]; then
    usage
fi

FRAMEWORK=$1
TAG=$2
if [ -z ${TAG} ]; then
    TAG="17.10"
fi

# Launch framework
case ${FRAMEWORK} in

    "pytorch")
        nvidia-docker run --rm \
            -w /opt/pytorch/examples/mnist \
            nvcr.io/nvidia/pytorch:${TAG} \
            python main.py
        ;;

    "tensorflow")
        nvidia-docker run --rm \
            -w /opt/tensorflow/tensorflow/examples/tutorials/mnist \
            nvcr.io/nvidia/tensorflow:${TAG} \
            python mnist_with_summaries.py
        ;;

    *)
        usage
        ;;
esac

exit 0

