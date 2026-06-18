package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"net/http"
	"os"
	"regexp"
	"strings"
	"time"

	"github.com/pterm/pterm"
)

type Severity string

const (
	High   Severity = "high"
	Medium Severity = "medium"
	Low    Severity = "low"
)

type Status string

const (
	Ok      Status = "ok"
	Weak    Status = "weak"
	Missing Status = "missing"
)

var severityPoints = map[Severity]float64{
	High:   30.0,
	Medium: 15.0,
	Low:    5.0,
}

type HeaderRule struct {
	Header         string         `json:"header"`
	Severity       Severity       `json:"severity"`
	Description    string         `json:"description"`
	Recommendation string         `json:"recommendation"`
	MustMatch      string         `json:"must_match"`
	regex          *regexp.Regexp `json:"-"`
}

type HeaderFinding struct {
	Rule        HeaderRule `json:"rule"`
	Status      Status     `json:"status"`
	ActualValue string     `json:"actual_value"`
}

type ScanReport struct {
	URL        string
	FinalURL   string
	StatusCode int
	Findings   []HeaderFinding
}

var rules = []HeaderRule{
	{
		Header:         "Strict-Transport-Security",
		Severity:       High,
		Description:    "Tells the browser to ONLY connect over HTTPS for the next N seconds, defeating SSL-stripping attacks",
		Recommendation: "Add: Strict-Transport-Security: max-age=31536000; includeSubDomains",
		MustMatch:      `max-age\s*=\s*[1-9]`,
	},
	{
		Header:         "Content-Security-Policy",
		Severity:       High,
		Description:    "Controls which scripts, styles, frames, and connections the browser may load — the strongest XSS defense",
		Recommendation: "Add a Content-Security-Policy that disallows 'unsafe-inline' and limits sources to trusted origins",
		MustMatch:      "",
	},
	{
		Header:         "X-Content-Type-Options",
		Severity:       Medium,
		Description:    "Stops browsers from second-guessing the Content-Type and treating a .txt file as HTML — defeats MIME-sniffing",
		Recommendation: "Add: X-Content-Type-Options: nosniff",
		MustMatch:      `nosniff`,
	},
	{
		Header:         "X-Frame-Options",
		Severity:       Medium,
		Description:    "Prevents another site from embedding this page in an iframe, defeating clickjacking attacks",
		Recommendation: "Add: X-Frame-Options: DENY (or use Content-Security-Policy: frame-ancestors 'none')",
		MustMatch:      "",
	},
	{
		Header:         "Cross-Origin-Opener-Policy",
		Severity:       Medium,
		Description:    "Prevents the page from being interacted with by other origins via window.opener, mitigating cross-origin attacks like Spectre",
		Recommendation: "Add: Cross-Origin-Opener-Policy: same-origin",
		MustMatch:      `same-origin`,
	},
	{
		Header:         "Cross-Origin-Embedder-Policy",
		Severity:       Medium,
		Description:    "Controls which cross-origin resources can be loaded, working with COOP to enable cross-origin isolation",
		Recommendation: "Add: Cross-Origin-Embedder-Policy: require-corp",
		MustMatch:      `require-corp`,
	},
	{
		Header:         "Cross-Origin-Resource-Policy",
		Severity:       Medium,
		Description:    "Controls which other origins are allowed to embed this resource, preventing cross-origin information leaks",
		Recommendation: "Add: Cross-Origin-Resource-Policy: same-origin",
		MustMatch:      `same-origin`,
	},
	{
		Header:         "Referrer-Policy",
		Severity:       Low,
		Description:    "Limits how much of the current URL leaks to other sites when the user clicks an outbound link",
		Recommendation: "Add: Referrer-Policy: strict-origin-when-cross-origin",
		MustMatch:      "",
	},
	{
		Header:         "Permissions-Policy",
		Severity:       Low,
		Description:    "Disables browser features the page does not use (camera, microphone, geolocation, payments, etc.)",
		Recommendation: "Add: Permissions-Policy: camera=(), microphone=(), geolocation=()",
		MustMatch:      "",
	},
}

func init() {
	for i, r := range rules {
		if r.MustMatch != "" {
			rules[i].regex = regexp.MustCompile(`(?i)` + r.MustMatch)
		}
	}
}

func (r *ScanReport) Score() int {
	var total float64
	for _, rule := range rules {
		total += severityPoints[rule.Severity]
	}
	if total == 0 {
		return 0
	}

	var earned float64
	for _, finding := range r.Findings {
		full := severityPoints[finding.Rule.Severity]
		if finding.Status == Ok {
			earned += full
		} else if finding.Status == Weak {
			earned += full / 2.0
		}
	}

	return int(math.Floor((earned/total)*100 + 0.5))
}

func (r *ScanReport) Grade() string {
	score := r.Score()
	if score >= 90 {
		return "A"
	}
	if score >= 80 {
		return "B"
	}
	if score >= 70 {
		return "C"
	}
	if score >= 60 {
		return "D"
	}
	return "F"
}

func evaluateHeader(rule HeaderRule, headers http.Header) HeaderFinding {
	actualValue := headers.Get(rule.Header)

	if actualValue == "" {
		return HeaderFinding{
			Rule:        rule,
			Status:      Missing,
			ActualValue: "",
		}
	}

	if rule.regex == nil {
		return HeaderFinding{
			Rule:        rule,
			Status:      Ok,
			ActualValue: actualValue,
		}
	}

	if rule.regex.MatchString(actualValue) {
		return HeaderFinding{
			Rule:        rule,
			Status:      Ok,
			ActualValue: actualValue,
		}
	}

	return HeaderFinding{
		Rule:        rule,
		Status:      Weak,
		ActualValue: actualValue,
	}
}

func scan(targetURL string, timeout time.Duration) (*ScanReport, error) {
	client := &http.Client{
		Timeout: timeout,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return nil
		},
	}

	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "kiwi/1.0")

	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var findings []HeaderFinding
	for _, rule := range rules {
		findings = append(findings, evaluateHeader(rule, resp.Header))
	}

	return &ScanReport{
		URL:        targetURL,
		FinalURL:   resp.Request.URL.String(),
		StatusCode: resp.StatusCode,
		Findings:   findings,
	}, nil
}

func getStatusStyle(status Status) *pterm.Style {
	switch status {
	case Ok:
		return pterm.NewStyle(pterm.FgGreen)
	case Weak:
		return pterm.NewStyle(pterm.FgYellow)
	case Missing:
		return pterm.NewStyle(pterm.FgRed)
	default:
		return pterm.NewStyle(pterm.FgDefault)
	}
}

func getGradeStyle(grade string) *pterm.Style {
	switch grade {
	case "A", "B":
		return pterm.NewStyle(pterm.FgLightGreen, pterm.Bold)
	case "C":
		return pterm.NewStyle(pterm.FgYellow, pterm.Bold)
	case "D", "F":
		return pterm.NewStyle(pterm.FgLightRed, pterm.Bold)
	default:
		return pterm.NewStyle(pterm.FgDefault)
	}
}

func renderReport(report *ScanReport) {
	fmt.Println()
	pterm.FgCyan.Printf("Headers for %s (HTTP %d)\n\n", report.FinalURL, report.StatusCode)

	tableData := pterm.TableData{
		{"HEADER", "STATUS", "SEVERITY"},
	}

	for _, f := range report.Findings {
		tableData = append(tableData, []string{
			pterm.White(f.Rule.Header),
			getStatusStyle(f.Status).Sprint(strings.ToUpper(string(f.Status))),
			string(f.Rule.Severity),
		})
	}

	pterm.DefaultTable.WithHasHeader().WithHeaderRowSeparator("-").WithData(tableData).Render()
	fmt.Println()

	if strings.HasPrefix(report.FinalURL, "http://") {
		pterm.FgYellow.Println("This response was served over plain HTTP. Browsers IGNORE HSTS over HTTP,\nso any HSTS grade above is misleading until the site enforces HTTPS.")
		fmt.Println()
	}

	grade := report.Grade()
	gradeStyle := getGradeStyle(grade)

	panelContent := fmt.Sprintf("Grade: %s\nScore: %d / 100", gradeStyle.Sprint(grade), report.Score())

	pterm.DefaultBox.
		WithTitle("Result").
		WithTitleTopLeft().
		WithBoxStyle(gradeStyle).
		Println(panelContent)

	var listItems []pterm.BulletListItem
	for _, f := range report.Findings {
		if f.Status != Ok {
			text := fmt.Sprintf("%s — %s", pterm.Yellow(f.Rule.Header), f.Rule.Recommendation)
			listItems = append(listItems, pterm.BulletListItem{Level: 0, Text: text})
		}
	}

	if len(listItems) > 0 {
		fmt.Println()
		pterm.DefaultBasicText.WithStyle(pterm.NewStyle(pterm.Bold)).Println("Recommendations:")
		pterm.DefaultBulletList.WithItems(listItems).Render()
	}
	fmt.Println()
}

func main() {
	timeoutFlag := flag.Float64("timeout", 10.0, "Seconds to wait before giving up on the request")
	jsonFlag := flag.Bool("json", false, "Output machine-readable JSON instead of a table")

	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage: kiwi [flags] <url>\n\nFlags:\n")
		flag.PrintDefaults()
	}
	flag.Parse()

	args := flag.Args()
	if len(args) < 1 {
		flag.Usage()
		os.Exit(2)
	}
	targetURL := args[0]

	if !strings.HasPrefix(targetURL, "http://") && !strings.HasPrefix(targetURL, "https://") {
		pterm.FgRed.Println("Invalid URL: Must include http:// or https://")
		os.Exit(2)
	}

	timeout := time.Duration(*timeoutFlag * float64(time.Second))

	var spinner *pterm.SpinnerPrinter
	if !*jsonFlag {
		spinner, _ = pterm.DefaultSpinner.Start(fmt.Sprintf("Scanning %s...", targetURL))
	}

	report, err := scan(targetURL, timeout)

	if spinner != nil {
		spinner.Stop()
	}

	if err != nil {
		if *jsonFlag {
			fmt.Fprintf(os.Stderr, `{"error": "%v"}`+"\n", err)
		} else {
			pterm.FgRed.Printf("Request failed: %v\n", err)
		}
		os.Exit(2)
	}

	if *jsonFlag {
		out := struct {
			URL        string          `json:"url"`
			FinalURL   string          `json:"final_url"`
			StatusCode int             `json:"status_code"`
			Score      int             `json:"score"`
			Grade      string          `json:"grade"`
			Findings   []HeaderFinding `json:"findings"`
		}{
			URL:        report.URL,
			FinalURL:   report.FinalURL,
			StatusCode: report.StatusCode,
			Score:      report.Score(),
			Grade:      report.Grade(),
			Findings:   report.Findings,
		}

		encoder := json.NewEncoder(os.Stdout)
		encoder.SetIndent("", "  ")
		if err := encoder.Encode(out); err != nil {
			fmt.Fprintf(os.Stderr, "Failed to encode JSON: %v\n", err)
			os.Exit(2)
		}

		os.Exit(0)
	}

	pterm.FgGreen.Println("Scan complete")
	renderReport(report)

	grade := report.Grade()
	if grade == "A" || grade == "B" {
		os.Exit(0)
	} else if grade == "C" || grade == "D" {
		os.Exit(1)
	}
	os.Exit(2)
}
