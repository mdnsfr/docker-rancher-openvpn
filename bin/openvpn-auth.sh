#!/bin/bash

OPENVPNDIR="/etc/openvpn"
. $OPENVPNDIR/auth.env

echo "verifying user $@"
/usr/local/bin/openvpn-auth.py $@
