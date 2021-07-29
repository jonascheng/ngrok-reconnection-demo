#!/bin/bash

# detect running environment
user=$USER

provision=/vagrant/Vagrantfile
if [ -e $provision ]
then
  echo "Vagrantfile found..."
  echo "Setting user to vagrant..."
  user=vagrant
fi

echo "APT::Acquire::Retries \"3\";" > /etc/apt/apt.conf.d/80-retries
echo "Acquire::https::packages.cloud.google.com::Verify-Peer \"false\";" > /etc/apt/apt.conf

apt-get update && apt-get install -y apt-transport-https
apt-get install -y curl git unzip python3-pip hddtemp

# download NGROK
wget https://aicsdata.blob.core.windows.net/public/ngrok/ngrok_setup.tgz
tar zxvf ngrok_setup.tgz
rm ngrok_setup.tgz

# install python package globally
cd /vagrant
sudo -H pip3 install -r requirements.txt