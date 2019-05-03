#!/bin/bash

OPENVPNDIR="/etc/openvpn"
. $OPENVPNDIR/remote.env
CA_CONTENT=$(cat $OPENVPNDIR/easy-rsa/keys/ca.crt)

cat <<- EOF
remote $REMOTE_IP $REMOTE_PORT
client
dev tun
proto tcp
remote-random
resolv-retry infinite
cipher AES-128-CBC
auth SHA1
nobind
persist-key
persist-tun
comp-lzo
verb 6
auth-user-pass
auth-nocache
auth-retry interact
remote-cert-tls server
reneg-sec 0
<ca>
$CA_CONTENT
</ca>
EOF
