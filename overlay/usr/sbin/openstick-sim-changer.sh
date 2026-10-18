#!/bin/sh
sleep 10
LED_PATH=/sys/class/leds
SIM_ENABLED=${SIM_ENABLED:-sim0}

get_sims() {
  # shellcheck disable=SC2010
  ls /sys/class/leds | grep sim
}

disable_all_sim() {
  for sim in $(get_sims) ; do
    echo 0 > "$LED_PATH/$sim/brightness"
  done
}

enable_sim() {
  #echo 1 > "$LED_PATH/sim_enable/brightness"
  disable_all_sim
  sim="$(get_sims | grep -e "^$1")"
  echo 1 > "$LED_PATH/$sim/brightness"
  #echo 0 > "$LED_PATH/sim_enable/brightness"
modprobe -r qcom-q6v5-mss
modprobe qcom-q6v5-mss
systemctl restart rmtfs
systemctl restart dbus-org.freedesktop.ModemManager1.service
}

main() {
  enable_sim "$SIM_ENABLED"
}

main

