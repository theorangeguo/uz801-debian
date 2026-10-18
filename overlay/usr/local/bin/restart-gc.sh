#!/bin/bash
grep gadget /sys/class/udc/ci_hdrc.0/device/driver/ci_hdrc.0/role
if [ $? -eq 0 ]
then
logger "Hotplug event: remove,gc restart"
systemctl restart linux-adbd-utils
fi

exit 0
