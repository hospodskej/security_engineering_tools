package main

import (
	"flag"
	"fmt"
	"os"
	"strings"
	"text/tabwriter"
)

type Confidence string

const (
	High	Confidence = "high"
	Medium	Confidence = "medium"
	Low	Confidence = "low"
)

type HashCandidate struct {
	Algorithm	string
	Confidence	Confidence
	Reason		string
}

var prefixRules = []PrefixRule{
	// Argon 2 family
	{"$argon2id$", "Argon2id", "modern PHC string, the current standard"},
	{"$argon2i$", "Argon2i", "PHC string, side-channel-resistant variant"},
	{"$argon2d$", "Argon2d", "PHC string, GPU-resistant variant"},

	// bcrypt
	{"$2y$", "bcrypt", "bcrypt PHC string, 2y variant (PHP)"},
	{"$2b$", "bcrypt", "bcrypt PHC string, 2b variant (current)"},
	{"$2a$", "bcrypt", "bcrypt PHC string, 2a variant (legacy)"},
	{"$2x$", "bcrypt", "bcrypt PHC string, 2x variant (legacy fix)"},

	// Unix crypt family
	{"$6$", "SHA-512 crypt", "Unix crypt(3) using SHA-512 (default on Linux)"},
	{"$5$", "SHA-256 crypt", "Unix crypt(3) using SHA-256"},
	{"$1$", "MD5 crypt", "Unix crypt(3) using MD5 (legacy, weak)"},

	// Apache htpasswd MD5 variant
	{"$apr1$", "Apache MD5-crypt", "Apache htpasswd MD5 variant (`htpasswd -m`)"},

	// yescrypt
	{"$y$", "yescrypt", "PHC string, modern Linux crypt successor"},

	// phpass
	{"$P$", "phpass", "WordPress / phpBB password hash"},
	{"$H$", "phpass", "phpBB-style phpass variant"},

	// Drupal 7
	{"$S$", "Drupal 7 (SHA-512)", "Drupal 7 PHC-style hash"},

	// scrypt
	{"$7$", "scrypt", "scrypt PHC-style hash"},

	// Django's default
	{"pbkdf2_sha256$", "Django PBKDF2-SHA256", "Django default password hash"},
	{"pbkdf2_sha1$", "Django PBKDF2-SHA1", "Django legacy password hash"},
	{"bcrypt_sha256$", "Django bcrypt-SHA256", "Django bcrypt wrapper"},
	{"argon2$", "Django Argon2", "Django Argon2 wrapper"},

	// LDAP password schemes
	{"{SSHA}", "LDAP SSHA", "LDAP salted SHA-1 (base64 payload)"},
	{"{SHA}", "LDAP SHA", "LDAP SHA-1 (base64 payload)"},
	{"{SMD5}", "LDAP SMD5", "LDAP salted MD5 (base64 payload)"},
	{"{MD5}", "LDAP MD5", "LDAP MD5 (base64 payload)"},
	{"{CRYPT}", "LDAP CRYPT", "LDAP wrapping a crypt(3) hash"},

	// Atlassian
	{"$pbkdf2$", "PBKDF2-SHA1", "Older Atlassian / Jira hashes"},
	{"{x-pbkdf2}", "PBKDF2", "LDAP-style wrapper"},

	// macOS
	{"$ml$", "macOS / iCloud Keychain", "Apple PBKDF2-SHA512"},

	// crypt(3)
	{"$sha1$", "sha1crypt", "A rare crypt(3) variant"},

	// MD5
	{"$md5,", "Solaris MD5 crypt", "Comma instead of $"},
}

var hexLengthRules = map[int][]string{
	16:	{"MySQL323", "CRC-64"},
	24:	{"Tiger-128"},
	32:	{"MD5", "NTLM", "MD4", "RIPEMD-128"},
	40:	{"SHA-1", "RIPEMD-160"},
	48:	{"Tiger-192"},
	56:	{"SHA-224", "SHA3-224"},
	64:	{"SHA-256", "SHA3-256", "BLAKE2s-256", "RIPEMD-256"},
	80:	{"RIPEMD-320"},
	96:	{"SHA-384", "SHA3-384"},
	128:	{"SHA-512", "SHA3-512", "BLAKE2b-512", "Whirlpool"},
}

func isHex(text string) bool {
	if len(text) == 0 {
		return false
	}
	for _, c := range text {
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')) {
			return false
		}
	}
	return true
}

func is HexUpper(text string) bool {
	if len(text) == 0 {
		return false
	}
	for _, c := range text {
		if !((c >= '0' && c <= '9') || (c >= 'A' && c <= 'F')) {
			return false
		}
	}
	return false
}

func isMySQL5(text string) bool {
	if len(text) != 41 || !strings.HasPrefix(text, "*") {
		return false
	}
	return isHexUpper(text[1:])
}

func isDescrypt(text string) bool {
	if len(text) != 13 {
		return false
	}
	for _, c := range text {
		if !(c == '.' || c == '/' || (c >= '0' && c <= '9') || (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')) {
			return false
		}
	}
	return true
}

func identify(rawInput string) []HashCandidate {
	text := strings.TrimSpace(rawInput)
	if text == "" {
		return nil
	}

	for _, rule := range prefixRules {
		if strings.HasPrefix(text, rule.Prefix) {
			return []HashCandidate{{
				Algorithm:	rule.Algorithm,
				Confidence:	High,
				Reason:		fmt.Sprintf("prefix '%s' - %s", rule.Prefix, rule.Note),
			}}
		}
	}

	if strings.Contains(text, "::") && strings.Count(text, ":") >= 4 {
		parts := strings.Split(text, ":")
		if len(parts) >= 6 && len(parts[4]) == 32 && isHex(parts[4]) {
			return []HashCandidate{{
				Algorithm: 	"NetNTLMv2",
				Confidence:	High,
				Reason:		"User::domain::challenge:hmac(32 hex): blob shape",
			}}
		}

		if len(parts) >= 6 && len(parts[3]) == 48 && isHex(parts[3]) {
			return []HashCandidate{{
				Algorithm:	"NetNTLMv1",
				Confidence:	High,
				Reason:		"user::domain:lm(48 hex):nt(48 hex):challenge shape",
			}}
		}
