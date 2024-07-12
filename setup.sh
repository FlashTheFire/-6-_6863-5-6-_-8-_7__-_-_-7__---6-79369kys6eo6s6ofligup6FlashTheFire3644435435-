#!/bin/bash

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

# Update package list and upgrade all packages
apt-get update && apt-get upgrade -y

# Install necessary system dependencies
apt-get install -y python3 python3-pip python3-venv libjpeg-dev zlib1g-dev

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python packages
pip install flask telebot requests pillow phonenumbers pytz aiohttp

# Deactivate the virtual environment
deactivate

# Display a message indicating setup completion
echo "Setup complete. To activate the virtual environment, run 'source venv/bin/activate'."
