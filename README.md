# Start test environment and install ngrok service

```console
vagrant up
# only for first time
cd ngrok_setup/
sudo ./install.sh <ngrok-token>
```

# Generate ssh key without passphrase

```console
ssh-keygen -t rsa
```

# Cronjob to monitor NGROK

```console
sudo crontab -e
# copy & paste
* * * * *  /usr/bin/python3 /vagrant/resources_monitor.py >> /tmp/ngrok_probe.log 2>&1
```

# Simulate network disconnect and reconnect

Unplug your hostnetwork for a while and then plug it back on.