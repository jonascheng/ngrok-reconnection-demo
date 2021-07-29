#!/usr/bin/env python3
import json
import os
import socket
import time

import requests
from applicationinsights import TelemetryClient

import psutil
from paramiko import AutoAddPolicy, RSAKey, SSHClient
from paramiko.ssh_exception import (AuthenticationException,
                                    NoValidConnectionsError)

# revise constant for testing in vagrant
# SSH_USER = "vagrant"
# NUM_TELEMETRY_COLL = 1
SSH_USER = "aics"
NUM_TELEMETRY_COLL = 60
APP_INSIGHTS_KEY = 'f0026a78-240d-4ca0-b58a-9ff411fb231c'  # FR
EVENT_TAG = 'smart-retail-sea-monitor'


def get_ngrok_host_port():
    '''
    an example would be
    {
    "tunnels": [
        {
        "name": "ssh",
        "uri": "/api/tunnels/ssh",
        "public_url": "tcp://0.tcp.ngrok.io:19277",
        "proto": "tcp",
        "config": {
            "addr": "localhost:22",
            "inspect": false
        },
        "metrics": {...}
        }
    ],
    "uri": "/api/tunnels"
    }
    '''
    tunnels = None
    host, port = None, None
    try:
        # check if localhost:4040 result is valid
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        if response.status_code != 200:
            print("unexpected status code {}".format(response.status_code))
            return tunnels, host, port
        tunnels = json.loads(response.text)
        print(tunnels)

        # expect public_url to be "tcp://0.tcp.ngrok.io:19277"
        # parse port forcefully and get None if failed
        host = tunnels['tunnels'][0]['public_url'].split(':')[1].lstrip("/")
        port = tunnels['tunnels'][0]['public_url'].split(':')[-1]
    except Exception as e:
        print("exception was caught {} while quering 127.0.0.1:4040".format(e))
    return tunnels, host, port


def restart_ngrok():
    print("restart ngrok")
    # current status
    os.system("systemctl status ngrok.service")
    os.system("systemctl restart ngrok.service")
    # the latest status
    os.system("systemctl status ngrok.service")
    exit()


def get_user_pk(user):
    user_home = os.path.expanduser("~" + user)
    id_rsa_pri = os.path.join(user_home, ".ssh/id_rsa")
    if not os.path.exists(id_rsa_pri):
        print("{} does not exist, please fix it first".format(id_rsa_pri))
        exit()
    return RSAKey.from_private_key_file(id_rsa_pri)


# append self public key to authorized_keys first time
def append_authorized_keys(user):
    user_home = os.path.expanduser("~" + user)
    id_rsa_pub = os.path.join(user_home, ".ssh/id_rsa.pub")
    authorized_keys = os.path.join(user_home, ".ssh/authorized_keys")

    if not os.path.exists(id_rsa_pub):
        print("{} does not exist, please fix it first".format(id_rsa_pub))
        exit()

    if not os.path.exists(authorized_keys):
        # create authorized_keys if it doesn't exist
        print("create empty {}".format(authorized_keys))
        f_authorized_keys = open(authorized_keys, "a+")
        f_authorized_keys.close()

    with open(id_rsa_pub, "r") as f_id_rsa_pub:
        text_id_rsa_pub = f_id_rsa_pub.read()
        text_authorized_keys = []
        # open for read
        with open(authorized_keys, "r") as f_authorized_keys:
            text_authorized_keys = f_authorized_keys.readlines()
        if text_id_rsa_pub not in text_authorized_keys:
            # open for append
            with open(authorized_keys, "a+") as f_authorized_keys:
                print("append public key to authorized_keys {}".format(
                    authorized_keys))
                f_authorized_keys.write(text_id_rsa_pub)


def get_device_of_mountpoint(mountpoint):
    partitions = psutil.disk_partitions()
    for p in partitions:
        if p.mountpoint == mountpoint:
            print("device of mountpoint {} is {}".format(mountpoint, p.device))
            return p.device
    return None


append_authorized_keys(SSH_USER)

tunnels, host, port = get_ngrok_host_port()

if not host or not port:
    print("host ({}) or port ({}) is None, skip collecting telemetry".format(
        host, port))
    exit()

pk = get_user_pk(SSH_USER)

client = SSHClient()
client.set_missing_host_key_policy(AutoAddPolicy())

# NGROK free tier: 40 connections / minute
try:
    print("try connect to {}:{} with user {}".format(host, port, SSH_USER))
    client.connect(host, port=port, username=SSH_USER, pkey=pk)
    print("ngrok is working, start telemetry collection")
except NoValidConnectionsError:
    print("restart ngrok due to NoValidConnectionsError exception")
    restart_ngrok()
except AuthenticationException:
    print("restart ngrok due to AuthenticationException exception")
    restart_ngrok()
except Exception as e:
    print("exception was caught {} while client.connect".format(e))
    print("network is probably disconnected, skip collecting telemetry")
    exit()

for x in range(NUM_TELEMETRY_COLL):
    # collect info
    hostname = socket.gethostname()
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_io_counters()
    sensors = psutil.sensors_temperatures()
    cpu_sensors = sensors.get('coretemp', {})
    cpu_temperature = 0
    if len(cpu_sensors) > 0:
        cpu_temperature = cpu_sensors[0].current
    os_disk_temperature = 0
    data_disk_temperature = 0
    device = get_device_of_mountpoint("/")
    if device and os.path.exists(device):
        shell_cmd = "/usr/sbin/hddtemp {} | awk '{{print $NF}}' | sed 's/°C//g'".format(
            device)
        try:
            os_disk_temperature = int(os.popen(shell_cmd).read())
            data_disk_temperature = int(os.popen(shell_cmd).read())
        except Exception as e:
            print(
                "exception was caught {} while quering temperature with cmd {}"
                .format(e, shell_cmd))
    else:
        print("device {} does not exist, skip collecting temperature".format(
            device))

    # send data to app insights
    payload = {
        'hostname': hostname,
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'disk_read_count': disk.read_count,
        'disk_write_count': disk.write_count,
        'disk_read_bytes': disk.read_bytes,
        'disk_write_bytes': disk.write_bytes,
        'disk_read_time': disk.read_time,
        'disk_write_time': disk.write_time,
        'cpu_temperature': cpu_temperature,
        'os_disk_temperature': os_disk_temperature,
        'data_disk_temperature': data_disk_temperature,
        'ngrok_tunnels': tunnels,
        'ngrok_port': port
    }
    print(payload)

    tc_client = TelemetryClient(APP_INSIGHTS_KEY)
    tc_client.track_event(EVENT_TAG, payload)
    tc_client.flush()

    time.sleep(1)
