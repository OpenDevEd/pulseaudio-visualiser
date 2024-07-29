#!/bin/bash

# Update package list and install system dependencies
sudo apt-get update

# Install Python 3 and pip if they are not already installed
sudo apt-get install -y python3 python3-pip

# Install required Python packages
pip3 install -r requirements.txt

chmod u+x audio_routing_visualiser.py

echo "All required packages have been installed."
