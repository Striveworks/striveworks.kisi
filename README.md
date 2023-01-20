# Ansible Collection - striveworks.kisi

An ansible module to interact with the Kisi API.

## Installation

```bash
ansible-galaxy install striveworks.kisi
```

## Example Role

```yml
- name: 'Create or update a kisi user'
  striveworks.kisi.user:
    api_key: "xxxxxxxxxxxxxx"
    email: "john@striveworks.us"
    name: "John Smith"
    role: "basic"
    groups: ["IT", "Facilities"]
    state: "enabled"
```

## Author

* [William Albers](https://www.github.com/walbers)

## License

This project is under the GPLv3 License.

## Copyright

(c) 2023, Striveworks
