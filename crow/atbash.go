package main

import (
	"unicode"
)

func AtbashProcess(text string) string {
	var result []rune
	for _, char := range text {
		if unicode.IsLetter(char) {
			if unicode.IsUpper(char) {
				result = append(result, 'Z'-(char-'A'))
			} else {
				result = append(result, 'z'-(char-'a'))
			}
		} else {
			result = append(result, char)
		}
	}
	return string(result)
}

func AtbashCrack(text string) CrackResult {
	decryptedText := AtbashProcess(text)
	score := calculateChiSquared(decryptedText)

	return CrackResult{
		Algorithm:	"Atbash",
		Shift:		0,
		Text:		decryptedText,
		Score:		score,
	}
}
