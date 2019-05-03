#!/bin/bash

CONTINUE=1
function error { echo "Error : $@"; CONTINUE=0; }
function die { echo "$@" ; exit 1; }
function checkpoint { [ "$CONTINUE" = "0" ] && echo "Unrecoverable errors found, exiting ..." && exit 1; }

OPENVPNDIR="/etc/openvpn"

# Providing defaults values for missing env variables
[ "$CERT_COUNTRY" = "" ]    && export CERT_COUNTRY="US"
[ "$CERT_PROVINCE" = "" ]   && export CERT_PROVINCE="NY"
[ "$CERT_CITY" = "" ]       && export CERT_CITY="New York"
[ "$CERT_ORG" = "" ]        && export CERT_ORG="Bright Power"
[ "$CERT_EMAIL" = "" ]      && export CERT_EMAIL="admin@brightpower.com"
[ "$CERT_OU" = "" ]         && export CERT_OU="IT"
[ "$VPNPOOL_NETWORK" = "" ] && export VPNPOOL_NETWORK="10.98.0.0"
[ "$VPNPOOL_CIDR" = "" ]    && export VPNPOOL_CIDR="16"
[ "$REMOTE_IP" = "" ]       && export REMOTE_IP="18.234.35.4"
[ "$REMOTE_PORT" = "" ]     && export REMOTE_PORT="1194"
[ "$PUSHDNS" = "" ]         && export PUSHDNS="169.254.169.254"
[ "$PUSHSEARCH" = "" ]      && export PUSHSEARCH="rancher.internal"

[ "$ROUTE_NETWORKS" = "" ]   && export ROUTE_NETWORKS="10.20.0.0 10.30.0.0 10.100.0.0 10.200.0.0"
[ "$ROUTE_NETMASK" = "" ]   && export ROUTE_NETMASK="255.255.0.0"

export RANCHER_METADATA_API='push "route 169.254.169.250 255.255.255.255"'
[ "$NO_RANCHER_METADATA_API" != "" ] && export RANCHER_METADATA_API=""


# Checking mandatory variables
for i in AUTH_METHOD
do
    [ "${!i}" = "" ] && error "empty value for variable '$i'"
done

# Checks
[ "${#CERT_COUNTRY}" != "2" ] && error "Certificate Country must be a 2 characters long string only"

checkpoint

env | grep "REMOTE_"

# Saving environment variables

[ -e "$OPENVPNDIR/auth.env" ] && rm "$OPENVPNDIR/auth.env"
env | grep "AUTH_" | while read i
do
    var=$(echo "$i" | awk -F= '{print $1}')
    var_data=$( echo "${!var}" | sed "s/'/\\'/g" )
    echo "export $var='$var_data'" >> $OPENVPNDIR/auth.env
done

env | grep "REMOTE_" | while read i
do
    var=$(echo "$i" | awk -F= '{print $1}')
    var_data=$( echo "${!var}" | sed "s/'/\\'/g" )
    echo "export $var='$var_data'" >> $OPENVPNDIR/remote.env
done

#=====[ Generating server config ]==============================================
VPNPOOL_NETMASK=$(netmask -s $VPNPOOL_NETWORK/$VPNPOOL_CIDR | awk -F/ '{print $2}')

# Building `push route` config with given NETWORK IPS
PUSH_ROUTING_CMD=""
for ROUTE_NETWORK in ROUTE_NETWORKS
do
    PUSH_ROUTING_CMD+="push \"route ${ROUTE_NETWORK} ${ROUTE_NETMASK}\""$'\n'
done

cat > $OPENVPNDIR/server.conf <<- EOF
port 1194
proto tcp
dev tun
ca easy-rsa/keys/ca.crt
cert easy-rsa/keys/server.crt
key easy-rsa/keys/server.key
dh easy-rsa/keys/dh2048.pem
cipher AES-128-CBC
auth SHA1
server $VPNPOOL_NETWORK $VPNPOOL_NETMASK
$PUSH_ROUTING_CMD
$RANCHER_METADATA_API
keepalive 10 120
comp-lzo
persist-key
persist-tun
client-to-client
max-clients 50
username-as-common-name
client-cert-not-required
reneg-sec 1209600

script-security 3 system
auth-user-pass-verify /usr/local/bin/openvpn-auth.sh via-env

EOF

echo $OPENVPN_EXTRACONF |sed 's/\\n/\n/g' >> $OPENVPNDIR/server.conf

#=====[ Generating certificates ]===============================================
if [ ! -d $OPENVPNDIR/easy-rsa ]; then
   # Copy easy-rsa tools to /etc/openvpn
   rsync -avz /usr/share/easy-rsa $OPENVPNDIR/

    # Configure easy-rsa vars file
   sed -i "s/export KEY_COUNTRY=.*/export KEY_COUNTRY=\"$CERT_COUNTRY\"/g" $OPENVPNDIR/easy-rsa/vars
   sed -i "s/export KEY_PROVINCE=.*/export KEY_PROVINCE=\"$CERT_PROVINCE\"/g" $OPENVPNDIR/easy-rsa/vars
   sed -i "s/export KEY_CITY=.*/export KEY_CITY=\"$CERT_CITY\"/g" $OPENVPNDIR/easy-rsa/vars
   sed -i "s/export KEY_ORG=.*/export KEY_ORG=\"$CERT_ORG\"/g" $OPENVPNDIR/easy-rsa/vars
   sed -i "s/export KEY_EMAIL=.*/export KEY_EMAIL=\"$CERT_EMAIL\"/g" $OPENVPNDIR/easy-rsa/vars
   sed -i "s/export KEY_OU=.*/export KEY_OU=\"$CERT_OU\"/g" $OPENVPNDIR/easy-rsa/vars

   pushd $OPENVPNDIR/easy-rsa
   . ./vars
   ./clean-all || error "Cannot clean previous keys"
   checkpoint
   ./build-ca --batch || error "Cannot build certificate authority"
   checkpoint
   ./build-key-server --batch server || error "Cannot create server key"
   checkpoint
   ./build-dh || error "Cannot create dh file"
   checkpoint
   ./build-key --batch RancherVPNClient
   openvpn --genkey --secret keys/ta.key
   popd
fi

#=====[ Enable tcp forwarding and add iptables MASQUERADE rule ]================
echo 1 > /proc/sys/net/ipv4/ip_forward
iptables -t nat -F
iptables -t nat -A POSTROUTING -s $VPNPOOL_NETWORK/$VPNPOOL_NETMASK -j MASQUERADE


/usr/local/bin/openvpn-get-client-config.sh > $OPENVPNDIR/client.conf

echo "=====[ OpenVPN Server config ]============================================"
cat $OPENVPNDIR/server.conf
echo "=========================================================================="


#=====[ Display client config  ]================================================
echo ""
echo "=====[ OpenVPN Client config ]============================================"
echo " To regenerate client config, run the 'openvpn-get-client-config.sh' script "
echo "--------------------------------------------------------------------------"
cat $OPENVPNDIR/client.conf
echo ""
echo "=========================================================================="
#=====[ Starting OpenVPN server ]===============================================
/usr/sbin/openvpn --cd /etc/openvpn --config server.conf
