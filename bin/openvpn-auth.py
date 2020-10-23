#!/usr/bin/python

import os
import sys
import requests
import boto3
from requests.auth import HTTPBasicAuth
from requests.auth import HTTPDigestAuth


def auth_success(_username):
    """ Authentication success, simply exiting with no error """
    print "[INFO] OpenVPN Authentication success for " + _username
    return True


def auth_failure(reason, severity="INFO"):
    """ Authentication failure, rejecting login with a stderr reason """
    print >> sys.stderr, "[" + severity + "] OpenVPN Authentication failure : " + reason
    return False


def auth_http_basic(url, username, password):
    """
    How to test:
      Just test against github api url : https://api.github.com/user
    Example :
      AUTH_METHOD='httpbasic'
      AUTH_HTTPBASIC_URL='http[s]://hostname[:port][/uri]'
    """
    if requests.get(url, auth=HTTPBasicAuth(username, password)):
        return auth_success(username)
    else:
        return auth_failure("Invalid credentials for username " + username)


def auth_http_digest(url, username, password):
    """
    How to test:
      Just test against httpbin sandbox url : https://httpbin.org/digest-auth/auth/user/pass
    Example :
      AUTH_METHOD='httpdigest'
      AUTH_HTTPDIGEST_URL='http[s]://hostname[:port][/uri]'
    """
    if requests.get(url, auth=HTTPDigestAuth(username, password)):
        return auth_success(username)
    else:
        return auth_failure("Invalid credentials for username " + username)


def auth_rancher_local(url, username, password):
    if requests.post(
            url, data={"authProvider": "localauthconfig", "code": username + ":" + password},
            verify=False, timeout=10):
        return auth_success(username)
    else:
        return auth_failure("Invalid credentials for username " + username)


def auth_aws_iam(access_key_id, secret_access_key):
    try:
        sts = boto3.client('sts', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)
        my_user = sts.get_caller_identity()['Arn'].split('/')[-1]

        iam = boto3.client('iam', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)
        my_groups = iam.list_groups_for_user(UserName=my_user)['Groups']
        have_vpn_group = [True for v in my_groups if v['GroupName'] == 'vpn-access']

        if any(have_vpn_group):
            return auth_success(my_user)
        else:
            return auth_failure("Invalid credentials for AWS user " + my_user)

    except Exception:
        return auth_failure("Failed to verify AWS account " + access_key_id)


if all(k in os.environ for k in ("username", "password", "AUTH_METHOD")):
    username = os.environ.get('username')
    password = os.environ.get('password')

    # example is AUTH_METHOD="rancherlocal|awsiam", it will check Rancher auth first, second AWS IAM auth
    auth_methods = os.environ.get('AUTH_METHOD').split('|')

    is_success = False
    for auth_method in auth_methods:
        print "[INFO] Verifying Authentication method: " + auth_method

        if auth_method == 'rancherlocal':
            if "AUTH_RANCHERLOCAL_URL" in os.environ:
                url = os.environ.get('AUTH_RANCHERLOCAL_URL')
                is_success = auth_rancher_local(url, username, password)
            else:
                auth_failure(
                    'Missing mandatory environment variable for '
                    'authentication method "rancherlocal" : AUTH_RANCHERLOCAL_URL'
                )

        elif auth_method == 'awsiam':
            is_success = auth_aws_iam(username, password)

        elif auth_method == 'httpbasic':
            if "AUTH_HTTPBASIC_URL" in os.environ:
                url = os.environ.get('AUTH_HTTPBASIC_URL')
                is_success = auth_http_basic(url, username, password)
            else:
                auth_failure(
                    'Missing mandatory environment variable for authentication method "httpbasic" : AUTH_HTTPBASIC_URL'
                )

        elif auth_method == 'httpdigest':
            if "AUTH_HTTPDIGEST_URL" in os.environ:
                url = os.environ.get('AUTH_HTTPDIGEST_URL')
                is_success = auth_http_digest(url, username, password)
            else:
                auth_failure(
                    'Missing mandatory environment variable for authentication method "httpdigest" : AUTH_HTTPDIGEST_URL'
                )

        if is_success:
            exit(0)

    exit(1)

else:
    auth_failure("Missing one of following environment variables : username, password, or AUTH_METHOD")
