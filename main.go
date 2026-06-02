package main

import (
	"flag"
	"os"
	"sort"

	"github.com/pterm/pterm"
)

func main() {
	encryptCmd := flag.NewFlagSet("encrypt", flag.ExitOnError)
	encryptAlgo := encryptCmd.String("algo", "caesar", "Cipher algorithm to use")
	encryptKey := encryptCmd.Int("key", 3, "Shift key (used for Caesar)")

	decryptCmd := flag.NewFlagSet("decrypt", flag.ExitOnError)
	decryptAlgo := decryptCmd.String("algo", "caesar", "Cipher algorithm to use")
	decryptKey := decryptCmd.Int("key", 3, "Shift key (used for Caesar)")

	crackCmd := flag.NewFlagSet("crack", flag.ExitOnError)

	if len(os.Args) < 2 {
		pterm.FgRed.Println("Expected 'encrypt', 'decrypt', or 'crack' subcommands")
		os.Exit(1)
	}

	switch os.Args[1] {
	case "encrypt":
		encryptCmd.Parse(os.Args[2:])
		if encryptCmd.NArg() == 0 {
			pterm.FgRed.Println("Please provide a text to encrypt")
			os.Exit(1)
		}
		text := encryptCmd.Arg(0)

		if *encryptAlgo == "caesar" {
			pterm.FgCyan.Println(CaesarEncrypt(text, *encryptKey))
		} else if *encryptAlgo == "atbash" {
			pterm.FgCyan.Println(AtbashProcess(text))
		} else {
			pterm.FgYellow.Printf("Algorithm '%s' is not supported yet.\n", *encryptAlgo)
		}

	case "decrypt":
		decryptCmd.Parse(os.Args[2:])
		if decryptCmd.NArg() == 0 {
			pterm.FgRed.Println("Please provide a text to decrypt")
			os.Exit(1)
		}

		text := decryptCmd.Arg(0)

		if *decryptAlgo == "caesar" {
			pterm.FgCyan.Println(CaesarDecrypt(text, *decryptKey))
		} else if *decryptAlgo == "atbash" {
			pterm.FgCyan.Println(AtbashProcess(text))
		} else {
			pterm.FgYellow.Printf("Algorithm '%s' is not supported yet. \n", *decryptAlgo)
		}

	case "crack":
		crackCmd.Parse(os.Args[2:])
		if crackCmd.NArg() == 0 {
			pterm.FgRed.Println("Please provide text to crack")
		}
		text := crackCmd.Arg(0)

		var allResults []CrackResult
		allResults = append(allResults, CaesarCrack(text)...)
		allResults = append(allResults, AtbashCrack(text))

		sort.Slice(allResults, func(i, j int) bool {
			return allResults[i].Score < allResults[j].Score
		})

		best := allResults[0]
		if best.Algorithm == "Caesar" {
			pterm.FgGreen.Println("Top Match [%s] (Shift %d): %s\n", best.Algorithm, best.Shift, best.Text)
		} else {
			pterm.FgGreen.Println("Top Match [%s]: %s\n", best.Algorithm, best.Text)
		}

	default:
		pterm.FgRed.Println("Expected 'encrypt', 'decrypt', or 'crack' subcommands")
		os.Exit(1)
	}
}
