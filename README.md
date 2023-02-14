# Ansible Collection - striveworks.kisi

Ansible modules to interact with the Kisi API.

## Installation

```bash
ansible-galaxy collection install striveworks.kisi
```

## Example Tasks

```yml
- name: 'Create or update a kisi user'
  striveworks.kisi.kisi_user:
    api_key: "xxxxxxxxxxxxxx"
    email: "john@striveworks.us"
    name: "John Smith"
    role: "basic"
    groups: ["IT", "Facilities"]
    state: "enabled"

- name: 'Backup kisi data'
  striveworks.kisi.kisi_archive:
    api_key: "xxxxxxxxxxxxxx"
    place_id: "0000"
    temp_file_dir: "/tmp/kisi/"
    aws_profile: "default"
    aws_bucket_name: "kisi-data-archive"
```

## Author

* [William Albers](https://www.github.com/walbers)

## License

This project is under the GPLv3 License.

## Copyright

(c) 2023, Striveworks
