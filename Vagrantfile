# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|

  config.vm.box = "centos65"
  config.vm.box_url = "http://puppet-vagrant-boxes.puppetlabs.com/centos-65-x64-virtualbox-puppet.box"

  # run provision.py on boot - not currently working
  # config.vm.provision "shell", path: "provision.py"

  # port forwarding
  config.vm.network :forwarded_port, guest: 80, host: 8080
  config.vm.network :forwarded_port, guest: 9200, host: 9200

  # up memory (elasticsearch is a memory hog)
  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--memory", "1024"]
  end

  # check if vagrant cachier is installed
  if Vagrant.has_plugin?("vagrant-cachier")
    config.cache.auto_detect = true
  end
end
