# kiwi

A Go CLI tool to scan and grade HTTP security headers.

## Features
* **Automated Scanning:** Quickly analyzes target URLs for critical security headers (CSP, HSTS, X-Frame-Options, etc.).
* **Grading System:** Scores the target's configuration on a weighted A-F scale based on the severity of missing or weak headers.
* **Actionable Output:** Provides specific remediation recommendations for failing checks.
* **Redirect Handling:** Automatically follows HTTP redirects to scan the final destination page.
