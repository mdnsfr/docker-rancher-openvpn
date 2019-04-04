#!/bin/bash

OPENVPNDIR="/etc/openvpn"
. $OPENVPNDIR/auth.env

/usr/local/bin/openvpn-auth.py $@