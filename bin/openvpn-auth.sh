#!/bin/bash

OPENVPNDIR="/etc/openvpn"
. $OPENVPNDIR/auth.env

if [[ $AUTH_METHOD == 'openshift' ]]; then
  curl -u $username:$password -kIsS "${AUTH_HTTPBASIC_URL}/oauth/authorize?client_id=openshift-challenging-client&response_type=token" | grep -q "Set-Cookie"
else
  /usr/local/bin/openvpn-auth.py $@
fi
