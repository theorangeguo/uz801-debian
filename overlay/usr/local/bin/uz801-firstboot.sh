#!/bin/bash
# ==============================================================================
# UZ801 First Boot Initialization
# ==============================================================================

FLAG="/etc/uz801_firstboot_done"
if [ -f "$FLAG" ]; then
    exit 0
fi

echo "[*] Initializing UZ801 system..."

# 1. Expand root filesystem
echo "[*] Resizing root partition..."
resize2fs /dev/disk/by-partlabel/rootfs 2>/dev/null || true

# 2. Re-generate SSH Host Keys if missing
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    echo "[*] Generating SSH host keys..."
    dpkg-reconfigure openssh-server 2>/dev/null || ssh-keygen -A
fi

# 3. NetworkManager WiFi default configuration: Client/Managed mode (Do not occupy AP)
echo "[*] Setting NetworkManager Wi-Fi configuration..."
cat << 'EOF' > /etc/NetworkManager/conf.d/10-wifi.conf
[device]
wifi.scan-rand-mac-address=no

[connection]
wifi.powersave=2
EOF

# 4. Setup USB Gadget RNDIS static IP
cat << 'EOF' > /etc/network/interfaces.d/usb0
auto usb0
iface usb0 inet static
    address 192.168.68.1
    netmask 255.255.255.0
EOF

# Mark firstboot as finished
touch "$FLAG"
echo "[OK] UZ801 First Boot Initialization completed."
