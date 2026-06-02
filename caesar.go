package main

import (
	"sort"
	"unicode"
)

var englishFrequencies = map[rune]float64{
	'A': 0.08167,	'B': 0.01492,	'C': 0.02782,	'D': 0.04253,
	'E': 0.12702,	'F': 0.02228,	'G': 0.02015,	'H': 0.06094,
	'I': 0.06966,	'J': 0.00153,	'K': 0.00772,	'L': 0.04025,
	'M': 0.02406,	'N': 0.06749,	'O': 0.07507,	'P': 0.01929,
	'Q': 0.00095,	'R': 0.05987,	'S': 0.06327,	'T': 0.09056,
	'U': 0.02758,	'V': 0.00978,	'W': 0.02360,	'X': 0.00150,
	'Y': 0.01974,	'Z': 0.00074,
}

type CrackResult struct {
	Algorithm	string
	Shift		int
	Text		string
	Score		float64
}

func CaesarEncrypt(text string, shift int) string {
	shift = shift % 26
	if shift < 0 {
		shift += 26
	}

	var result []rune
	for _, char := range text {
		if unicode.IsLetter(char) {
			base := 'A'
			if unicode.IsLower(char) {
				base = 'a'
			}
			shifted := base + (char-base+rune(shift))%26
			result = append(result, shifted)
		} else {
			result = append(result, char)
		}
	}
	return string(result)
}

func CaesarDecrypt(text string, shift int) string {
	return CaesarEncrypt(text, -shift)
}

func calculateChiSquared(text string) float64 {
	counts := make(map[rune]int)
	totalLetters := 0

	for _, char := range text {
		if unicode.IsLetter(char) {
			counts[unicode.ToUpper(char)]++
			totalLetters++
		}
	}

	if totalLetters == 0 {
		return 0
	}

	chiSquared := 0.0
	for char, expectedFreq := range englishFrequencies {
		observed := float64(counts[char])
		expected := expectedFreq * float64(totalLetters)
		if expected > 0 {
			diff := observed - expected
			chiSquared += (diff * diff) / expected
		}
	}

	return chiSquared
}

func CaesarCrack(text string) []CrackResult {
	var results []CrackResult

	for shift := 0; shift < 26; shift++ {
		decryptedText := CaesarDecrypt(text, shift)
		score := calculateChiSquared(decryptedText)
		results = append(results, CrackResult{
			Algorithm: "Caesar",
			Shift:	shift,
			Text:	decryptedText,
			Score: score,
		})

	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Score < results[j].Score
	})

	return results
}
