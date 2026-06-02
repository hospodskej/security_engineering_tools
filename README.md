# cuckoo

A CLI tool written in Python designed as a flexible netcat replacement for raw socket communication, file transfers, and remote shell execution. Built as part of my 30-Days-30-Tools challenge.

## Features

* **Dual Modes:** Operates seamlessly as both a multi-threaded TCP listener (server) and a versatile data streaming client.
* **Interactive Command Shells:** Instantiates remote command execution wrappers (`-c`) or fires off specific binary payloads upon connection (`-e`).
* **Arbitrary File Transfers:** Supports blind file upload and write capabilities (`-u`) directly over network sockets for easy exfiltration or payload dropping.
