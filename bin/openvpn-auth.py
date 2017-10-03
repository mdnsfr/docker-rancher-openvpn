#!/usr/bin/python

"""
Authentication handler for OpenVPN by Alexis Ducastel
"""

import os
import sys
import ldap
import kerberos
import requests
from requests.auth import HTTPBasicAuth
from requests.auth import HTTPDigestAuth
from auth0.v3.authentication import GetToken
from auth0.v3.exceptions import Auth0Error

def auth_success(username):
    """ Authentication success, simply exiting with no error """
    print "[INFO] OpenVPN Authentication success for " + username
    exit(0)
    

def auth_failure(reason, severity="INFO"):
    """ Authentication failure, rejecting login with a stderr reason """
    print >> sys.stderr, "["+severity+"] OpenVPN Authentication failure : " + reason
    exit(1)

def auth_ldap(address, basedn, binddn, bindpwd, search, username, password):
    """ Ldap authentication handler """
    
    # Initializing connection to ldap server
    try:
        conn = ldap.initialize(address)
    except:
        auth_failure("Cannot connect to url "+ address,'ERROR')
        
    conn.protocol_version = 3
    conn.set_option(ldap.OPT_REFERRALS, 0)
        
    # Trying authentication
    try:    
        # if server need authentication to be crawled
        if(binddn is not None and binddn!=''):
            conn.simple_bind_s(binddn, bindpwd)
        
        # Searching for user based on search pattern
        result = conn.search_s(basedn, ldap.SCOPE_SUBTREE, search.replace('$username',username), None, 1)
        
        # Nothing found => failure
        if not result or len(result) != 1:
            auth_failure('Cannot find username '+ username)
        else:
            userdn=result[0][0]
        
        try:
            # Trying to authenticate with user credentials
            conn.simple_bind_s(userdn, password)
            auth_success(username)
            
        except ldap.INVALID_CREDENTIALS:
            # authentication as user failed
            auth_failure("Invalid credentials for username "+ username)
            
    except ldap.INVALID_CREDENTIALS:
        # authentication for search failed
        auth_failure("Invalid credentials for initial bind "+ binddn,'ERROR')
        
    except ldap.SERVER_DOWN:
        # Server unreachable
        auth_failure("Server unreachable",'ERROR')
        
    except ldap.LDAPError, e:
        # Other ldap error
        if type(e.message) == dict and e.message.has_key('desc'):
            auth_failure("LDAP error: " + e.message['desc'])
        else: 
            auth_failure("LDAP error: " + e)
    finally:
        # Always disconnecting, with exception or not
        conn.unbind_s()
        
        
def auth_http_basic(url, username, password):
    if (requests.get(url, auth=HTTPBasicAuth(username, password))):
        auth_success(username)
    else:
        auth_failure("Invalid credentials for username "+ username)

def auth_http_digest(url, username, password):
    if (requests.get(url, auth=HTTPDigestAuth(username, password))):
        auth_success(username)
    else:
        auth_failure("Invalid credentials for username "+ username)

def auth_rancher_local(url, username, password):
    if (requests.post(url, data = { "authProvider": "localauthconfig", "code": username + ":" + password})):
        auth_success(username)
    else:
        auth_failure("Invalid credentials for username "+ username)

def auth_auth0(endpoint, client_id, client_secret, realm, username, password):
    client = GetToken(endpoint)
    try:
        client.login(client_id, client_secret, username, password, None, realm, None)
        auth_success(username)
    except Auth0Error, e:
        auth_failure('Auth0 error: ' + e.message)

if all (k in os.environ for k in ("username","password","AUTH_METHOD")):
    username = os.environ.get('username') 
    password = os.environ.get('password') 
    auth_method = os.environ.get('AUTH_METHOD') 

    #=====[ LDAP ]==============================================================
    # How to test:
    #   https://github.com/osixia/docker-openldap
    #   docker run -d --name=ldap --env LDAP_ORGANISATION="ACME" --env LDAP_DOMAIN="acme.tld" --env LDAP_ADMIN_PASSWORD="mypwd" osixia/openldap:1.1.1
    #   docker exec ldap ldapsearch -x -h localhost -b dc=acme,dc=tld -D "cn=admin,dc=acme,dc=tld" -w admin
    # Example :
    #   AUTH_METHOD='ldap'
    #   AUTH_LDAP_URL='ldap[s]://ldap.acme.tld[:port]'
    #   AUTH_LDAP_SEARCH='(uid=$username)'
    #   AUTH_LDAP_BASEDN='dc=acme,dc=com'
    #   AUTH_LDAP_BINDDN='cn=admin,dc=acme,dc=com'
    #   AUTH_LDAP_BINDPWD='myadminpwd'
    # 
    if auth_method=='ldap':
        if all (k in os.environ for k in ("AUTH_LDAP_URL","AUTH_LDAP_SEARCH","AUTH_LDAP_BASEDN")):
            address=os.environ.get('AUTH_LDAP_URL') 
            search=os.environ.get('AUTH_LDAP_SEARCH').replace('$username',username) 
            basedn=os.environ.get('AUTH_LDAP_BASEDN')
            binddn=os.environ.get('AUTH_LDAP_BINDDN')
            bindpwd=os.environ.get('AUTH_LDAP_BINDPWD')
            auth_ldap(address, basedn, binddn, bindpwd, search, username, password)
        else:
            auth_failure('Missing one of mandatory environment variables for authentication method "ldap" : AUTH_LDAP_URL or AUTH_LDAP_SEARCH or AUTH_LDAP_BASEDN')
            
    #=====[ HTTP Basic ]==============================================================
    # How to test:
    #   Just test against github api url : https://api.github.com/user
    # Example :
    #   AUTH_METHOD='httpbasic'
    #   AUTH_HTTPBASIC_URL='http[s]://hostname[:port][/uri]'
    # 
    elif auth_method=='httpbasic':
        if "AUTH_HTTPBASIC_URL" in os.environ:
            url=os.environ.get('AUTH_HTTPBASIC_URL')
            auth_http_basic(url, username, password)
        else:
            auth_failure('Missing mandatory environment variable for authentication method "httpbasic" : AUTH_HTTPBASIC_URL')
            
    #=====[ HTTP Digest ]==============================================================
    # How to test:
    #   Just test against httpbin sandbox url : https://httpbin.org/digest-auth/auth/user/pass
    # Example :
    #   AUTH_METHOD='httpdigest'
    #   AUTH_HTTPDIGEST_URL='http[s]://hostname[:port][/uri]'
    # 
    elif auth_method=='httpdigest':
        if "AUTH_HTTPDIGEST_URL" in os.environ:
            url=os.environ.get('AUTH_HTTPDIGEST_URL')
            auth_http_digest(url, username, password)
        else:
            auth_failure('Missing mandatory environment variable for authentication method "httpdigest" : AUTH_HTTPDIGEST_URL')

    #=====[ Rancher local ]==============================================================
    # How to test:
    #   @todo
    # Example :
    #   AUTH_METHOD='rancherlocal'
    elif auth_method=='rancherlocal':
        if "AUTH_RANCHERLOCAL_URL" in os.environ:
            url=os.environ.get('AUTH_RANCHERLOCAL_URL')
            auth_rancher_local(url, username, password)
        else:
            auth_failure('Missing mandatory environment variable for authentication method "rancherlocal" : AUTH_RANCHERLOCAL_URL')

            
    #=====[ Kerberos ]==============================================================
    # How to test:
    #   @todo
    # Example :
    #   AUTH_METHOD='kerberos'
    elif auth_method=='kerberos':
        auth_failure('Not implemented')

        #if all (k in os.environ for k in ("KERBEROS_REALM")):
        #    realm=os.environ.get('KERBEROS_REALM') 
        #    if not kerberos.checkPassword(username,password,realm):
        #        auth_failure("Invalid credentials for " + username)
        #    else:
        #        auth_success(username)
        #else:
        #    auth_failure("Missing mandatory environement variable KERBEROS_REALM")

    #=====[ Auth0 ]==============================================================
    # How to test:
    #   Create an account with Auth0 and add a new client with Grant Type password enabled. Tested only with Auth0 database realm.
    # Example :
    #   AUTH_AUTH0_ENDPOINT='yourorganization.auth0.com'
    #   AUTH_AUTH0_CLIENT_KEY='1111'
    #   AUTH_AUTH0_CLIENT_SECRET='11119999-1111'
    #   AUTH_AUTH0_REALM='Username-Password-Authentication'
    elif auth_method=='auth0':
        if all (k in os.environ for k in ("AUTH_AUTH0_ENDPOINT","AUTH_AUTH0_CLIENT_KEY","AUTH_AUTH0_CLIENT_SECRET")):
            endpoint=os.environ.get('AUTH_AUTH0_ENDPOINT')
            client_key=os.environ.get('AUTH_AUTH0_CLIENT_KEY')
            client_secret=os.environ.get('AUTH_AUTH0_CLIENT_SECRET')
            realm=os.getenv('AUTH_AUTH0_REALM', 'Username-Password-Authentication')
            auth_auth0(endpoint, client_key, client_secret, realm, username, password)
        else:
            auth_failure('Missing one of mandatory environment variables for authentication method "auth0" : AUTH_AUTH0_ENDPOINT or AUTH_AUTH0_CLIENT_KEY or AUTH_AUTH0_CLIENT_SECRET')

    # No method handler found
    else:
        auth_failure('No handler found for authentication method "'+ auth_method +'"')

else:
    auth_failure("Missing one of following environment variables : username, password, or AUTH_METHOD")

