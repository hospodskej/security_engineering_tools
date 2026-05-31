# mantis

A Go CLI tool to concurrently scan and identify open TCP ports. Created as part of my 30-Days-30-Tools challenge

## Features
- **Concurrent Scanning:** Utilizes a dynamic worker pool to rapidly scan targets, drastically reducing scan times.
- **Full Range Coverage:** Automatically analyzes all 65,535 possible TCP ports for a comprehensive sweep.
- **Adjustable Timeout:** Built-in network timeouts prevent the scanner from hanging on filtered ports or dropped packets.
- **Actionable Output:** Sorts and displays only the active, open ports with terminal colorization for clear readability.
