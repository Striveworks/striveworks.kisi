import json
import requests
import time
import boto3
import tempfile
import zipfile
from datetime import datetime

# from botocore.config import Config
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: kisi_archive
short_description: Archive Kisi users data
description: Backs up last months kisi event data to AWS
author: "Will Albers (@walbers)"

"""


class AnsibleKisi:
    def __init__(self, module):
        self.url = "https://api.kisi.io"
        self.auth = {
            "Authorization": "KISI-LOGIN " + module.params["api_key"],
            "Content-Type": "application/json",
        }
        self.module = module
        self.exit_messages = []

        # Connect to s3 bucket
        session = boto3.Session(profile_name=module.params["aws_profile"])
        # config = Config(connect_timeout=30, retries={"max_attempts": 1})
        self.s3 = session.resource("s3") # , config=config

    def compress_and_upload_file(
        self, data, temp_fiie_dir, aws_bucket_name, aws_bucket_path
    ):
        # Write data to temp file and compress it
        tf = tempfile.NamedTemporaryFile(dir=temp_fiie_dir)
        tf.write(data)
        zipfile.ZipFile(tf.name + ".zip", "w", zipfile.ZIP_DEFLATED).write(tf.name)

        # Upload and clean up
        response = s3.Bucket(aws_bucket_name).upload_file(
            tf.name + ".zip",
            aws_bucket_path + (datetime.utcnow()).isoformat() + ".zip",
        )

        os.remove(tf.name + ".zip")
        tf.close()
        self.exit_messages("Uploaded data to s3 bucket and deleted temp file")

    def get_event_export(self, place_id):
        # Send create report request
        query = "/event_exports"
        current_date = (datetime.utcnow()).isoformat()
        body = {
            "event_export": {
                "around": f"P1M0D/{current_date}",
                "place_id": place_id,
                "reference_id": None,
                "reference_type": None,
            }
        }
        response = requests.post(
            self.url + query, headers=self.auth, data=json.dumps(body)
        )

        if response.status_code == 429:
            self.module.fail_json(
                msg=f"Already backed up within past 10 minutes. Kisi rate limits to one event export every 10 minutes\n"
            )
        elif response.status_code != 200:
            self.module.fail_json(
                msg=f"Failed with error code {response.status_code}\n"
            )

        event_export = response.json()

        # wait for report to generate
        time.sleep(60)

        # download report
        query = f"/event_exports/{event_export['id']}/download"
        response = requests.get(self.url + query, headers=self.auth)

        if response.status_code != 200:
            self.module.fail_json(
                msg=f"Failed with error code {response.status_code}\n"
            )

        event_export_download = response.json()

        response = requests.get(event_export_download["url"], allow_redirects=True)
        self.exit_messages.append(f"Downloaded event export for place id: {place_id}")
        return response.content


def main():

    argument_spec = {
        "api_key": {"type": "str", "required": True},
        "place_id": {"type": "str", "required": True},
        "temp_file_dir": {"type": "str", "default": "/tmp/"},
        "aws_profile": {"type": "str", "default": "default"},
        "aws_bucket_name": {"type": "str", "required": True},
        "aws_bucket_path": {"type": "str", "required": True},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        # required_if=[["state", "enabled", ["name"]]],
        supports_check_mode=True,
    )
    kisi = AnsibleKisi(module)

    data = kisi.get_event_export(module.params["place_id"])

    kisi.compress_and_upload_file(data, module.params["temp_fiie_dir"], module.params["aws_bucket_name"], module.params["aws_bucket_path"])

    module.params["api_key"] = ""
    module.exit_json(
        changed=bool(kisi.exit_messages), msg="\n".join(kisi.exit_messages)
    )


if __name__ == "__main__":
    main()
