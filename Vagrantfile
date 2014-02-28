# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # vbox name
  config.vm.box = "centos_6_5_64"

  # vbox url
  config.vm.box_url = "https://github.com/2creatives/vagrant-centos/releases/download/v6.5.1/centos65-x86_64-20131205.box"

  # run provision.py on boot
  config.vm.provision "shell", path: "provision.py"

  # enable package caching
  config.cache.auto_detect = true

  # port forwarding
  config.vm.network :forwarded_port, guest: 80, host: 8080
  config.vm.network :forwarded_port, guest: 9200, host: 8081

  # up memory (elasticsearch is a memory hog)
  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--memory", "1024"]
  end
end
