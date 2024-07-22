import json
import requests
import time
import boto3
import os
import tempfile
import zipfile
from datetime import datetime,timezone

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
        self.s3 = session.resource("s3")  # , config=config

    def compress_and_upload_file(
        self, data, place_id, temp_file_dir, aws_bucket_name, aws_bucket_path
    ):
        # Write data to temp file and compress it
        tf = tempfile.NamedTemporaryFile(dir=temp_file_dir, suffix='-' + place_id)
        tf.write(data)
        filename = tf.name + ".zip"
        zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED).write(tf.name)

        # Upload and clean up
        response = self.s3.Bucket(aws_bucket_name).upload_file(
            filename,
            aws_bucket_path + (datetime.now(timezone.utc)).isoformat() + ".zip",
        )

        os.remove(filename)
        tf.close()
        self.exit_messages.append("Uploaded data to s3 bucket and deleted temp file")

    def get_event_export(self, place_id, event_exporter_id):
        # Send create report request
        query = "/reports"
        current_date = (datetime.now(timezone.utc)).isoformat()
        body = {
            "name": f"Event Data Backup for { current_date } ({ place_id })",
            "reporter_id": event_exporter_id,
            "reporter_type": "EventExportReporter",
            "end_date": current_date,
            "place_id": place_id
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
                msg=f"Event export report creation failed with error code {response.status_code}\n"
            )

        event_export = response.json()

        # wait for report to generate
        time.sleep(60)

        # download report
        query = f"/reports/{event_export['id']}/download"
        response = requests.post(self.url + query, headers=self.auth)

        if response.status_code != 200:
            self.module.fail_json(
                msg=f"Downloading report failed with error code {response.status_code}. Event id {event_export['id']}\n"
            )

        event_export_download = response.json()
        response = requests.get(event_export_download["url"], allow_redirects=True)
        self.exit_messages.append(f"Downloaded event export for place id: {place_id}")
        return response.content


def main():

    argument_spec = {
        "api_key": {"type": "str", "required": True},
        "place_id": {"type": "str", "required": True},
        "event_exporter_id": {"type": "str", "required": True},
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

    data = kisi.get_event_export(module.params["place_id"], module.params["event_exporter_id"])

    kisi.compress_and_upload_file(
        data,
        module.params["place_id"],
        module.params["temp_file_dir"],
        module.params["aws_bucket_name"],
        module.params["aws_bucket_path"],
    )

    module.params["api_key"] = ""
    module.exit_json(
        changed=bool(kisi.exit_messages)
    )


if __name__ == "__main__":
    main()
