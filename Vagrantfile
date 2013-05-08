Vagrant::Config.run do |config|
  config.vm.define :chefabulous, :primary => true do |vconfig|
    vconfig.vm.box = "ubuntu-12.04-omnibus-chef"
    vconfig.vm.box_url = "https://s3.amazonaws.com/gsc-vagrant-boxes/ubuntu-12.04-omnibus-chef.box"
    vconfig.vm.host_name = "chefabulous"
    vconfig.vm.network :hostonly, "10.10.10.10"
    #vconfig.vm.network :bridged,:bridge => 'en0: Wi-Fi (AirPort)'
    vconfig.vm.customize ["modifyvm", :id, "--memory", 512, "--cpus", 2, "--ioapic", "on", "--hwvirtex", "on", "--nestedpaging", "on", "--usbehci", "on", "--audio", "none"]
    vconfig.vm.forward_port(22, 2210, :auto => true)
    vconfig.vm.forward_port(443, 4430, :auto => true)
    vconfig.vm.forward_port(444, 4440, :auto => true)
    vconfig.vbguest.auto_update = true
  end
end
