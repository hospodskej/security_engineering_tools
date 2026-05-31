package main

import (
	"fmt"
	"net"
	"sort"
	"time"

	"github.com/pterm/pterm"
)

func worker(ports, results chan int) {
	for p := range ports {
		fmt.Printf("Checked port: %d\n", p) //QA
		address := fmt.Sprintf("scanme.nmap.org:%d", p)
		conn, err := net.DialTimeout("tcp", address, 1*time.Second)
		if err != nil {
			results <- 0
			continue
		}
		conn.Close()
		results <- p
	}
}

func main() {
	var workers int
	for {
		pterm.FgCyan.Printf("How many workers would you like to use?\n")
		_, err := fmt.Scanln(&workers)
		if err == nil {
			break
		} else {
			pterm.FgYellow.Printf("Please input a valid number")
		}
	}

	ports := make(chan int, workers)
	results := make(chan int)
	var openports []int

	for i := 0; i < cap(ports); i++ {
		go worker(ports, results)
	}

	go func() {
		for i := 1; i <= 1024; i++ {
			ports <- i
		}
	}()

	for i := 0; i < 1024; i++ {
		port := <- results
		if port != 0 {
			openports = append(openports, port)
		}
	}

	close(ports)
	close(results)
	fmt.Println("--------------------------------")

	if len(openports) == 0 {
		fmt.Println("No open ports available")
	} else {
		sort.Ints(openports)
		for _, port := range openports {
			fmt.Printf("%d open\n", port)
		}
	}
}
