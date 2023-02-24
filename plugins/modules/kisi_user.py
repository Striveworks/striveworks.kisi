import json
import requests
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: kisi_user
short_description: Manage Kisi users
description: Manage Kisi users
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

    def get_user(self, email):
        query = f"/members?query={email}"
        response = requests.get(self.url + query, headers=self.auth)

        if response.status_code != 200:
            self.module.fail_json(
                msg=f"Received a {response.status_code} from the Kisi API instead of a 200"
            )

        users = response.json()
        if len(users) > 1:
            self.module.fail_json(
                msg=f"Received more than 1 user for the email: {email}"
            )

        return users

    def get_user_groups(self, id):
        query = f"/role_assignments?user_id={id}&scope=group"
        response = requests.get(self.url + query, headers=self.auth)

        if response.status_code != 200:
            self.module.fail_json(
                msg=f"Received a {response.status_code} from the Kisi API instead of a 200 for get_user_groups"
            )

        return response.json()

    def update_user_state(self, user):
        query = f"/members/{user['id']}"
        body = {
            "member": {
                "image": user["image"],
                "access_enabled": not user["access_enabled"],
                "password_flow_enabled": user["password_flow_enabled"],
                "card_activation_required": user["card_activation_required"],
                "notes": user["notes"],
            }
        }

        if not self.module.check_mode:
            response = requests.patch(
                self.url + query, headers=self.auth, data=json.dumps(body)
            )
        else:
            self.exit_messages.append(
                f"Updated {user['name']} state to {not user['access_enabled']}"
            )
            return

        if response.status_code != 204:
            self.module.fail_json(
                msg=f"Received a {response.status_code} from the Kisi API instead of a 204 for update_user_state\n{response.text}\n{body}\n{user['id']}"
            )
        else:
            self.exit_messages.append(
                f"Updated {user['name']} state to {not user['access_enabled']}"
            )

    def update_user_role(self, user, role):
        query = "/role_assignments"
        body = {
            "role_assignment": {
                "user_id": user["user_id"],
                "role_id": role,
                "organization_id": user["organization_id"],
                "notify": True,
            }
        }

        if not self.module.check_mode:
            response = requests.post(
                self.url + query, headers=self.auth, data=json.dumps(body)
            )
        else:
            self.exit_messages.append(f"Updated {user['name']} role to {role}")
            return

        if response.status_code != 200:
            self.module.fail_json(
                msg=f"Received a {response.status_code} from the Kisi API instead of a 200 for update_user_role"
            )
        else:
            self.exit_messages.append(f"Updated {user['name']} role to {role}")

    def update_user_access(self, user, all_groups, current_groups, desired_groups):
        query = "/role_assignments"
        groups_to_add = desired_groups - current_groups
        groups_to_delete = current_groups - desired_groups

        for group in groups_to_add:
            body = {
                "role_assignment": {
                    "user_id": user["user_id"],
                    "role_id": "group_basic",
                    "group_id": str(group),
                    "notify": True,
                }
            }
            if not self.module.check_mode:
                response = requests.post(
                    self.url + query, headers=self.auth, data=json.dumps(body)
                )
                if response.status_code != 200:
                    self.module.fail_json(
                        msg=f"Received a {response.status_code} from the Kisi API instead of a 200 for creating membership update_user_access\n{self.url}\n{self.auth}\n{body}\n{response.text}"
                    )
                else:
                    self.exit_messages.append(
                        f"Gave {user['name']} access to group {group}"
                    )
            else:
                self.exit_messages.append(
                    f"Gave {user['name']} access to group {group}"
                )

        if groups_to_delete:
            response = requests.get(
                f"{self.url}{query}?user_id={user['user_id']}", headers=self.auth
            )
            if response.status_code != 200:
                self.module.fail_json(
                    msg=f"Received a {response.status_code} from the Kisi API instead of a 200 for getting role assignment id for delete membership in update_user_access"
                )
            role_assignments = response.json()

        for group in groups_to_delete:
            if not self.module.check_mode:

                for role_assignment in role_assignments:
                    if role_assignment.get("group_id") == group:
                        role_assignment_id = role_assignment["id"]
                        break

                response = requests.delete(
                    f"{self.url}{query}/{role_assignment_id}", headers=self.auth
                )
                if response.status_code != 204:
                    self.module.fail_json(
                        msg=f"Received a {response.status_code} from the Kisi API instead of a 204 for deleting membership in update_user_access"
                    )
                else:
                    self.exit_messages.append(
                        f"Delete {user['name']} access to group {group}"
                    )
            else:
                self.exit_messages.append(
                    f"Delete {user['name']} access to group {group}"
                )

    def create_user(self, name, state, email):
        query = f"/members"
        body = {
            "member": {
                "name": name,
                "image": None,
                "send_emails": True,
                "confirm": True,
                "access_enabled": True if state == "enabled" else False,
                "password_flow_enabled": True,
                "card_activation_required": True,
                "notes": None,
                "email": email,
            }
        }

        if not self.module.check_mode:
            response = requests.post(
                self.url + query, headers=self.auth, data=json.dumps(body)
            )
        else:
            self.exit_messages.append(
                f"Created user for {name}. Since this is check mode no user was actually created and fake roles can't be assigned so we are done."
            )
            return

        if response.status_code != 200:
            self.module.fail_json(
                msg=f"Received a {response.status_code} from the Kisi API instead of a 200 for create_user"
            )
        else:
            self.exit_messages.append(f"Created user for {name}")

        return response.json()

    def delete_user(self, user):
        query = f"/members/{user['id']}"
        if not self.module.check_mode:
            response = requests.delete(self.url + query, headers=self.auth)
        else:
            self.exit_messages.append(f"Deleted {user['name']}")
            return

        if response.status_code != 204:
            self.module.fail_json(
                msg=f"Received a {response.status_code} from the Kisi API instead of a 204 for delete_user"
            )
        else:
            self.exit_messages.append(f"Deleted {user['name']}")

    def get_all_groups(self):
        query = "/groups"
        response = requests.get(self.url + query, headers=self.auth)

        if response.status_code != 200:
            self.module.fail_json(
                msg=f"Received a {response.status_code} from the Kisi API instead of a 200 for get_all_groups"
            )

        return response.json()


def main():

    argument_spec = {
        "api_key": {"type": "str", "required": True},
        "email": {"type": "str", "required": True},
        "name": {"type": "str", "default": ""},
        "role": {"type": "str", "default": "basic"},
        "groups": {"type": "list", "default": []},
        "state": {"type": "str", "default": "enabled"},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        # required_if=[["state", "enabled", ["name"]]],
        supports_check_mode=True,
    )
    kisi = AnsibleKisi(module)
    email = module.params["email"]
    state = module.params["state"]
    groups = module.params["groups"]
    role = module.params["role"]
    name = module.params["name"]
    role_ids = [
        "owner",
        "administrator",
        "manager",
        "user_manager",
        "observer",
        "basic",
    ]

    if email == "" or "@" not in email:
        module.fail_json(msg=f"Need valid email. Given: {email}")

    if role not in role_ids:
        module.fail_json(msg=f"Need valid role. Given: {role}")

    user = kisi.get_user(email)

    if state == "enabled" or state == "disabled":
        if not user:
            user = kisi.create_user(name, state, email)
            if module.check_mode:
                module.exit_json(
                    changed=bool(kisi.exit_messages), msg=kisi.exit_messages
                )
        else:
            user = user[0]

        user["state"] = "enabled" if user["access_enabled"] else "disabled"
        if user["state"] != state:
            kisi.update_user_state(user)

        if user["role_id"] != role:
            kisi.update_user_role(user, role)

        all_groups = kisi.get_all_groups()
        desired_groups_ids = {
            group["id"] for group in all_groups if group["name"] in groups
        }

        current_groups = kisi.get_user_groups(user["user_id"])
        current_groups_ids = {group["group"]["id"] for group in current_groups}

        if desired_groups_ids != current_groups_ids:
            kisi.update_user_access(
                user, all_groups, current_groups_ids, desired_groups_ids
            )

    elif state == "deleted":
        if user:
            kisi.delete_user(user)

    else:
        module.fail_json(msg=f"The state {state} is not a valid option")

    module.params["api_key"] = ""
    module.exit_json(
        changed=bool(kisi.exit_messages), msg="\n".join(kisi.exit_messages)
    )


if __name__ == "__main__":
    main()
