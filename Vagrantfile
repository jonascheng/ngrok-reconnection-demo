# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.provider "virtualbox" do |v|
    v.memory = 16384
    v.cpus = 2
  end

  # Specify your hostname if you like
  # config.vm.hostname = "name"
  config.vm.box = "bento/ubuntu-18.04"
  config.vm.network "private_network", type: "dhcp"
  config.vm.provision "docker"
  # Specify the shared folder mounted from the host if you like
  # By default you get "." synced as "/vagrant"
  # config.vm.synced_folder ".", "/folder"
  config.vm.provision "shell", path: "vagrant.sh"
end
