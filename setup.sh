#!/bin/bash

# Update the package list
sudo yum update -y

# Install Python 3 and pip
sudo yum install -y python3 python3-pip

# Upgrade pip
pip3 install --upgrade pip

# Install required Python packages
pip3 install pyTelegramBotAPI requests phonenumbers pillow pytz aiohttp

# Install additional dependencies if needed
# For example, for PIL (Pillow), you might need to install some additional system packages
sudo yum install -y libjpeg-turbo-devel zlib-devel

# Clone or copy SmsChecker and DepositChecker scripts if they are hosted in a repository or a location
# Example:
# git clone <your-repository-url>

# Alternatively, if they are on your local machine, you can SCP them to the EC2 instance:
# scp SmsChecker.py ec2-user@<your-ec2-instance-ip>:/home/ec2-user/
# scp DepositChecker.py ec2-user@<your-ec2-instance-ip>:/home/ec2-user/
