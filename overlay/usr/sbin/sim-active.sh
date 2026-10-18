#!/bin/sh

MODEL_FILE="/sys/firmware/devicetree/base/model"
ResetEpsApnModelKeyWords="uz801|jz02v10|gexing-sp970"
ActiveSimModelKeyWords="gexing-sp970"

main() {
  sleep 25
  systemctl stop ModemManager
  if grep -Eq "$ResetEpsApnModelKeyWords" "$MODEL_FILE"; then
    qmicli -d /dev/wwan0qmi0 -p --wds-modify-profile="3gpp,3,apn='',pdp-type=IPV4V6,auth=NONE,username='',password=''"
  fi
  if grep -Eq "$ActiveSimModelKeyWords" "$MODEL_FILE"; then
    APPLICATION_ID=$(qmicli -d /dev/wwan0qmi0 -p --uim-get-card-status | awk '/Application ID:/ {getline; gsub(/[[:space:]]/, ""); print $0; exit}')
    qmicli -d /dev/wwan0qmi0 -p --uim-change-provisioning-session='activate=no,session-type=primary-gw-provisioning'
    qmicli -d /dev/wwan0qmi0 -p --uim-change-provisioning-session="slot=1,activate=yes,session-type=primary-gw-provisioning,aid=$APPLICATION_ID"
  fi
  systemctl start ModemManager
}

main
