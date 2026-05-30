# hashdog

A fast, lightweight Python CLI tool to identify unknown password hashes, encodings, and tokens. Built as part of a 1 Tool-a-day challenge.

## Features
* Identifies hashes based on structural prefixes, character sets, and exact string lengths.
* Detects modern password hashes (Argon2, bcrypt, scrypt, yescrypt).
* Identifies legacy formats (Unix crypt, LDAP brackets, MD5, NTLM).
