# Python Built-Ins:
import asyncio
from datetime import datetime
import json
import logging
import os
import re
import time
import uuid

# External Dependencies:
import boto3
import requests
import websocket

logger = logging.getLogger("main")
logger.setLevel(logging.INFO)
smclient = boto3.client("sagemaker")

ENV_DOMAIN_ID = os.environ.get("SAGEMAKER_DOMAIN_ID")
COMMAND_SCRIPT = [
    "git clone https://github.com/aws-samples/sagemaker-studio-auto-shutdown-extension.git",
    "pwd && ls",
    "cd sagemaker-studio-auto-shutdown-extension && ./install_tarball.sh",
]
PROMPT_REGEX = r"bash-[\d\.]+\$ $"

def get_domain_id():
    if ENV_DOMAIN_ID:
        return ENV_DOMAIN_ID

    domains_resp = smclient.list_domains()
    domains = domains_resp["Domains"]
    if len(domains) < 0:
        raise ValueError(f"No SageMaker Studio domains in this region!")
    elif len(domains) > 1:
        raise ValueError(
            f"Cannot automatically select SageMaker Studio domain: multiple ({len(domains)}) were found"
        )

    return domains[0]["DomainId"]


def lambda_handler(event, context):
    print(event)
    domain_id = event.get("DomainId", event.get("domainId"))
    if domain_id is None:
        domain_id = get_domain_id()

    user_profile_name = event.get("UserProfileName", event.get("userProfileName"))
    if user_profile_name is None:
        raise ValueError(
            f"Input event must include top-level property 'UserProfileName' (or 'userProfileName')"
        )

    logger.info(f"Processing request for {domain_id}/{user_profile_name}")
    run_commands(domain_id, user_profile_name)


def run_commands(domain_id, user_profile_name):
    logger.info(f"[{domain_id}/{user_profile_name}] Generating presigned URL")
    presigned_resp = smclient.create_presigned_domain_url(
        DomainId=domain_id,
        UserProfileName=user_profile_name,
    )
    sagemaker_login_url = presigned_resp["AuthorizedUrl"]

    # Login URL like https://d-....studio.{AWSRegion}.sagemaker.aws/auth?token=...
    # API relative to https://d-....studio.{AWSRegion}.sagemaker.aws/jupyter/default
    api_base_url = sagemaker_login_url.partition("?")[0].rpartition("/")[0] + "/jupyter/default"

    reqsess = requests.Session()
    logger.info(f"[{domain_id}/{user_profile_name}] Logging in")
    login_resp = reqsess.get(sagemaker_login_url)

    # Wait here if the JupyterServer to start up if it's not already ready
    if "_xsrf" not in reqsess.cookies:
        logger.info(f"[{domain_id}/{user_profile_name}] Waiting for JupyterServer start-up...")
        app_status = "Unknown"
        base_url = sagemaker_login_url.partition("?")[0].rpartition("/")[0]
        # Same polling logic as the SMStudio front-end at time of writing:
        while app_status not in {"InService", "Terminated"}:
            time.sleep(2)
            app_status = reqsess.get(f"{base_url}/app?appType=JupyterServer&appName=default").text
            logger.debug(f"Got app_status {app_status}")

        if app_status == "InService":
            logger.info(f"[{domain_id}/{user_profile_name}] JupyterServer app ready")
            ready_resp = reqsess.get(api_base_url)
        else:
            raise ValueError(f"JupyterServer app in unusable status '{app_status}'")


    logger.info(f"[{domain_id}/{user_profile_name}] Creating terminal")
    terminal_resp = reqsess.post(
        f"{api_base_url}/api/terminals",
        params={ "_xsrf": reqsess.cookies["_xsrf"] },  # Seems like this can be put in either header or query
    )
    terminal = terminal_resp.json()

    # Execution request/reply is done on websockets channels
    ws_base_url = "wss://" + api_base_url.partition("://")[2] + "/terminals/websocket"
    cookies = reqsess.cookies.get_dict()

    logger.info(f"[{domain_id}/{user_profile_name}] Connecting to:\n{ws_base_url}/{terminal['name']}")
    ws = websocket.create_connection(
        f"{ws_base_url}/{terminal['name']}",
        cookie="; ".join(["%s=%s" %(i, j) for i, j in cookies.items()]),
    )

    try:
        logger.info(f"[{domain_id}/{user_profile_name}] Waiting for setup message")
        setup = None
        while setup is not None:
            res = json.loads(ws.recv())
            if res[0] == "setup":
                setup = res[1]

        # Send commands one by one, waiting for each to complete and re-show prompt:
        prompt_exp = re.compile(PROMPT_REGEX, re.MULTILINE)
        for ix, c in enumerate(COMMAND_SCRIPT):
            ws.send(json.dumps(["stdin", c + "\n"]))
            # Assuming echo is on, stdin messages will be echoed to stdout anyway so no need to print

            while True:
                res = json.loads(ws.recv())
                # res[0] is the stream so will be e.g. 'stdout', 'stderr'
                # res[1] is the content
                logger.info(f"[{domain_id}/{user_profile_name}] {res[0]}: {res[1]}")
                if res[0] == "stdout" and prompt_exp.search(res[1]):
                    break

        logger.info(f"[{domain_id}/{user_profile_name}] Complete")
    finally:
        ws.close()
