#!/bin/bash

LANG_TARGET=en_US.UTF-8
PASSWORD=ChangeMe
NAME=uz801v3
PARTUUID=a7ab80e8-e9d1-e8cd-f157-93f69b1d141e

cat <<EOF > /etc/apt/sources.list
deb http://deb.debian.org/debian/ trixie main contrib non-free non-free-firmware
deb http://deb.debian.org/debian/ trixie-updates main contrib non-free non-free-firmware
deb http://deb.debian.org/debian/ trixie-backports main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
EOF

cat <<EOF > /etc/fstab
PARTUUID=$PARTUUID / ext4 defaults,noatime,commit=600,errors=remount-ro 0 1
tmpfs /tmp tmpfs defaults,nosuid 0 0
EOF

apt-get update
apt-get full-upgrade -y
apt-get install -y locales network-manager openssh-server systemd-timesyncd fake-hwclock zram-tools rmtfs qrtr-tools sudo curl wget htop modemmanager wireless-tools
apt-get install -y /tmp/*.deb

systemctl enable rmtfs.service ModemManager.service openstick-sim-changer.service openstick-expanddisk-startup.service

timedatectl set-ntp 1
sed -i -e "s/# $LANG_TARGET UTF-8/$LANG_TARGET UTF-8/" /etc/locale.gen
dpkg-reconfigure --frontend=noninteractive locales
update-locale LANG=$LANG_TARGET LC_ALL=$LANG_TARGET LANGUAGE=$LANG_TARGET

echo -e "$PASSWORD\n$PASSWORD" | passwd root
echo $NAME > /etc/hostname
sed -i "1a 127.0.0.1\t$NAME" /etc/hosts
sed -i "s/::1\t\tlocalhost/::1\t\tlocalhost $NAME/g" /etc/hosts
sed -i 's/^.\?PermitRootLogin.*$/PermitRootLogin yes/g' /etc/ssh/sshd_config
sed -i 's/^.\?ALGO=.*$/ALGO=lzo-rle/g' /etc/default/zramswap
sed -i 's/^.\?PERCENT=.*$/PERCENT=100/g' /etc/default/zramswap

cat <<EOF > /etc/rc.local
#!/bin/sh -e
exit 0
EOF
chmod +x /etc/rc.local

echo "## Default Configuration" > /tmp/info.md
vmlinuz_name=$(basename /boot/vmlinuz-*)
cat <<EOF >> /tmp/info.md
- Base OS: Debian 13 (Trixie) arm64
- Kernel: ${vmlinuz_name#*-}
- Root User: root / $PASSWORD
- USB Gadget: RNDIS + ADB enabled by default
EOF

rm -rf /etc/ssh/ssh_host_* /var/lib/apt/lists/*
apt clean
exit 0
