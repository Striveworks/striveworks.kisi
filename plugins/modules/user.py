import requests
from ansible.module_utils.basic import AnsibleModule


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
        response = request.get(self.url + query, headers=self.auth)

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
        response = request.get(self.url + query, headers=self.auth)

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
            response = request.patch(self.url + query, headers=self.auth, data=body)
        else:
            self.exit_messages.append(f"Updated {user['name']} state")
            return

        if response.status_code != 204:
            self.module.fail_json(
                msg=f"Received a {response.status_code} from the Kisi API instead of a 204 for update_user_state"
            )
        else:
            self.exit_messages.append(f"Updated {user['name']} state")

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
            response = request.post(self.url + query, headers=self.auth, data=body)
        else:
            self.exit_messages.append(f"Updated {user['name']} role")
            return

        if response.status_code != 200:
            self.module.fail_json(
                msg=f"Received a {response.status_code} from the Kisi API instead of a 200 for update_user_role"
            )
        else:
            self.exit_messages.append(f"Updated {user['name']} role")

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
                response = request.post(self.url + query, headers=self.auth, data=body)
                if response.status_code != 200:
                    self.module.fail_json(
                        msg=f"Received a {response.status_code} from the Kisi API instead of a 200 for update_user_access"
                    )
                else:
                    self.exit_messages.append(
                        f"Gave {user['name']} access to group {group}"
                    )
            else:
                self.exit_messages.append(
                    f"Gave {user['name']} access to group {group}"
                )

        for group in groups_to_delete:
            if not self.module.check_mode:
                response = request.delete(
                    f"{self.url}{query}/{group}", headers=self.auth
                )
                if response.status_code != 204:
                    self.module.fail_json(
                        msg=f"Received a {response.status_code} from the Kisi API instead of a 204 for update_user_access"
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
            response = request.post(self.url + query, headers=self.auth, data=body)
        else:
            self.exit_messages.append(f"Updated {user['name']} state")
            return

        if response.status_code != 200:
            self.module.fail_json(
                msg=f"Received a {response.status_code} from the Kisi API instead of a 200 for create_user"
            )
        else:
            self.exit_messages.append(f"Updated {user['name']} state")

    def delete_user(self, user):
        query = f"/members/{user['id']}"
        if not self.module.check_mode:
            response = request.delete(self.url + query, headers=self.auth)
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
        response = request.get(self.url + query, headers=self.auth)

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

    module.exit_json(
        changed=bool(self.exit_messages), msg="\n".join(self.exit_messages)
    )

    # TODO: move to striveworks namespace, test, write tests?, publish, install


if __name__ == "__main__":
    main()
