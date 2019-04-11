#!/bin/bash

OPENVPNDIR="/etc/openvpn"
. $OPENVPNDIR/remote.env
CA_CONTENT=$(cat $OPENVPNDIR/easy-rsa/keys/ca.crt)

cat <<- EOF
remote $REMOTE_IP $REMOTE_PORT
client
dev tun
proto udp
remote-random
resolv-retry infinite
cipher AES-128-CBC
auth SHA1
nobind
link-mtu 1440
persist-key
persist-tun
comp-lzo
verb 6
auth-user-pass
auth-nocache
auth-retry interact
remote-cert-tls server
<ca>
$CA_CONTENT
</ca>
EOF
