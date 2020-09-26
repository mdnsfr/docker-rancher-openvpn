FROM debian:jessie

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    easy-rsa \
    dnsutils \
    iptables \
    netmask \
    mawk \
    rsync \
    openssl \
    openvpn \
    python-kerberos \
    python-ldap \
    python-paramiko \
    python-pip \
    wget \
    && apt-get clean

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY bin/* /usr/local/bin/
RUN chmod 744 /usr/local/bin/entry.sh && \
    chown root:root /usr/local/bin/entry.sh && \
    chmod 744 /usr/local/bin/openvpn-* && \
    chown root:root /usr/local/bin/openvpn-*

CMD ["/usr/local/bin/entry.sh"]
