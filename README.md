# 🎯 Target Company Decision-Maker & LinkedIn Scout (`company-lead-scout`)

A standalone, lightweight tool and web application designed specifically to accept target company names/domains and discover their CEOs, Founders, COOs, Financial Controllers, and key decision-makers on LinkedIn—complete with automated, hyper-personalized outreach message generation and CSV export capabilities.

---

## 🌟 Key Features

- **Zero API Costs Out-of-the-Box**: Performs smart search queries targeting `site:linkedin.com/in/` via DuckDuckGo and Bing fallback scraping without requiring expensive paid LinkedIn or search API subscriptions.
- **Target Role Configuration**: Out-of-the-box pre-configured search lists targeting CEOs, Founders, Presidents, COOs, Operations Managers, Practice Managers, Controllers, and CPAs.
- **Outreach Generator**: Automatically generates customized LinkedIn connection request notes (<300 characters, compliant with LinkedIn connection limits) and structured InMail / Cold Email templates tailored to each decision-maker.
- **Dual Interface**:
  - **CLI Tool**: Batch process companies from a CSV file or query single companies straight from the terminal.
  - **Modern Glassmorphic Web Dashboard**: A visual interface for real-time target company entry, lead card browsing, one-click outreach copying, and CSV downloads.

---

## 📁 Repository Structure

```text
company-lead-scout/
├── app.py                      # FastAPI web server backend
├── cli.py                      # Terminal Command-Line Interface
├── requirements.txt            # Python dependencies
├── .env.example                # Environment configuration template
├── README.md                   # Repository documentation
├── config/
│   └── titles.json             # Target role criteria definitions
├── core/
│   ├── company_enricher.py     # Domain/Name normalization & query builder
│   ├── linkedin_finder.py      # Multi-engine search for LinkedIn profiles
│   ├── contact_parser.py       # Name/title/link snippet parser
│   └── outreach_generator.py   # Connection note & InMail generator
├── data/
│   └── target_companies.csv    # Sample input company list
└── web/
    ├── index.html              # Web dashboard markup
    ├── style.css               # Glassmorphic dark theme CSS
    └── app.js                  # Frontend client application logic
```

---

## 🚀 Quickstart & Installation

### 1. Install Dependencies
Make sure Python 3.9+ is installed, then run:
```bash
pip install -r requirements.txt
```

---

## 💻 CLI Usage

### Search a Single Company
```bash
python cli.py --company "Acme Corp"
```

### Search with Specific Target Job Titles
```bash
python cli.py --company "Stripe" --titles "CEO,Founder,COO"
```

### Batch Process Target Companies from CSV & Export Leads
```bash
python cli.py --file data/target_companies.csv --export leads.csv
```

---

## 🌐 Web Dashboard Usage

Launch the web backend server:
```bash
python app.py
```
Open your browser at `http://127.0.0.1:8000` to access the interactive lead scout interface.

---

## 📄 License
MIT License.
