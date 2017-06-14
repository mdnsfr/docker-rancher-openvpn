#!/bin/bash

OPENVPNDIR="/etc/openvpn"
. $OPENVPNDIR/auth.env

if [[ $AUTH_METHOD == 'openshift' ]]; then
  curl -u $username:$password -kIsS "${AUTH_HTTPBASIC_URL}/oauth/authorize?client_id=openshift-challenging-client&response_type=token" | grep -q "Set-Cookie"
elif [[ $AUTH_METHOD == 'openshift-token' ]]; then
    curl -X GET -H "Authorization: Bearer $password" -kIsS "${AUTH_HTTPBASIC_URL}/oapi/v1/projects" | grep -q "200 OK"
else
  /usr/local/bin/openvpn-auth.py $@
fi
