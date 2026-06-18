package main

import (
	"fmt"
	"net"
	"sort"
	"time"
	"os"
	"sync"
	"flag"

	"github.com/pterm/pterm"
)

func worker(ports, results chan int, target string, wg *sync.WaitGroup) {
	defer wg.Done()
	for p := range ports {
		fmt.Printf("Checked port: %d\n", p) //QA

		address := fmt.Sprintf("%s:%d", target, p)
		conn, err := net.DialTimeout("tcp", address, 1*time.Second)
		if err != nil {
			continue
		}
		conn.Close()
		results <- p
	}
}

func main() {
	var wg sync.WaitGroup

	fastScan := flag.Bool("f", false, "Scan the top 100 most common ports")
	flag.Parse()

	if len(os.Args) < 1 {
		pterm.FgRed.Printf("Usage: ./mantis <IP or Domain>")
		return
	}

	target := flag.Args()[0]

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
		wg.Add(1)
		go worker(ports, results, target, &wg)
	}

	go func() {
		wg.Wait()
		close(results)
	}()

	go func() {
		if *fastScan {
			topPorts := []int{
				7, 9, 13, 21, 22, 23, 25, 26, 37, 53, 79, 80, 81, 88, 106, 110, 111, 113, 119, 135, 139, 143, 144, 179, 199, 389, 427, 443, 444, 445, 465, 513, 514, 515, 543, 544, 548, 554, 587, 631, 646, 873, 990, 993, 995, 1025, 1026, 1027, 1028, 1029, 1110, 1433, 1720, 1723, 1755, 1900, 2000, 2001, 2049, 2121, 2717, 3000, 3128, 3306, 3389, 3986, 4899, 5000, 5009, 5051, 5060, 5101, 5190, 5357, 5432, 5631, 5666, 5800, 5900, 6000, 6001, 6646, 7070, 8000, 8008, 8009, 8080, 8081, 8443, 8888, 9100, 9999, 10000, 32768, 49152, 49153, 49154, 49155, 49156, 49157,
			}
			for _, port := range topPorts {
				ports <- port
			}
		} else {
			for i := 1; i <= 65535; i++ {
				ports <- i
			}
		}
		close(ports)
	}()

	for port := range results {
		openports = append(openports, port)
	}

	fmt.Println("--------------------------------")

	if len(openports) == 0 {
		fmt.Println("No open ports available")
	} else {
		sort.Ints(openports)
		for _, port := range openports {
			coloredPort := pterm.FgCyan.Sprintf("%d", port)
			fmt.Printf("%s open\n", coloredPort)
		}
	}
}
