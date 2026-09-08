import argparse
import json
import os
import sys
import pandas as pd

# Reconfigure stdout for Windows console UTF-8 support
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.linkedin_finder import LinkedInFinder
from core.outreach_generator import OutreachGenerator
from core.company_enricher import CompanyEnricher
from core.company_intel import CompanyIntelScout
from core.vulnerability_analyzer import VulnerabilityAnalyzer

console = Console(force_terminal=False)



def run_cli():
    parser = argparse.ArgumentParser(description="Target Company Decision-Maker & LinkedIn Contact Finder")
    parser.add_argument("--company", "-c", type=str, help="Single target company name or domain (e.g. 'Acme Corp' or 'acme.com')")
    parser.add_argument("--file", "-f", type=str, help="Path to input CSV file containing target company names")
    parser.add_argument("--titles", "-t", type=str, help="Comma-separated target job titles (e.g. 'CEO,Founder,COO,Controller')")
    parser.add_argument("--max-results", "-m", type=int, default=5, help="Max LinkedIn contacts to find per company (default: 5)")
    parser.add_argument("--export", "-e", type=str, help="Path to export results CSV or JSON (e.g. 'leads.csv')")
    parser.add_argument("--intel", "-i", action="store_true", help="Fetch 360° company web presence, weak spots, and competitor intelligence")


    args = parser.parse_args()

    if not args.company and not args.file:
        console.print("[bold red]Error:[/bold red] You must specify either --company 'Name' or --file 'companies.csv'")
        parser.print_help()
        sys.exit(1)

    # Load custom titles or defaults
    target_titles = [t.strip() for t in args.titles.split(",")] if args.titles else None
    
    # Target companies list
    companies = []
    if args.company:
        companies.append(args.company)
    if args.file:
        if os.path.exists(args.file):
            df = pd.read_csv(args.file)
            # Find company column
            col = next((c for c in df.columns if any(k in c.lower() for k in ["company", "name", "domain", "firm"])), df.columns[0])
            companies.extend(df[col].dropna().astype(str).tolist())
        else:
            console.print(f"[bold red]File not found:[/bold red] {args.file}")
            sys.exit(1)

    finder = LinkedInFinder()
    intel_scout = CompanyIntelScout()
    all_leads = []

    console.print(Panel.fit("[bold blue]Target Company LinkedIn Lead Finder & Intel Scout[/bold blue]", subtitle="Scanning decision-makers & company vulnerabilities"))

    for comp in companies:
        if args.intel:
            console.print(f"\n[bold magenta][Intel Scout] Gathering intelligence & vulnerabilities for:[/bold magenta] [bold white]{comp}[/bold white]...")
            web_data = intel_scout.fetch_website_details(comp)
            rev_data = intel_scout.search_google_maps_reviews(comp)
            competitors = intel_scout.find_competitors(comp)
            analysis = VulnerabilityAnalyzer.analyze_vulnerabilities(web_data, rev_data, competitors)

            console.print(f"  [cyan]Website status:[/cyan] {web_data.get('status')}")
            if analysis['weak_spots']:
                console.print("  [bold red]Weak Spots / Vulnerabilities Identified:[/bold red]")
                for ws in analysis['weak_spots']:
                    console.print(f"   • [{ws['category']}] {ws['issue']} (Severity: {ws['severity']})")
            if competitors:
                console.print(f"  [bold yellow]Key Competitors:[/bold yellow] {', '.join([c['name'] for c in competitors])}")
            if analysis['pitch_hooks']:
                console.print(f"  [bold green]Suggested Outreach Angles:[/bold green] {analysis['pitch_hooks'][0]}")

        console.print(f"\n[bold yellow][Search] Decision makers for:[/bold yellow] [bold white]{comp}[/bold white]...")

        leads = finder.find_decision_makers(comp, target_titles=target_titles, max_results=args.max_results)

        if not leads:
            console.print(f"  [dim red]No LinkedIn profiles found for {comp}[/dim red]")
            continue

        table = Table(title=f"Decision-Makers: {comp}", show_lines=True)
        table.add_column("Name", style="bold cyan")
        table.add_column("Title / Role", style="green")
        table.add_column("Location", style="dim white")
        table.add_column("LinkedIn URL", style="blue")

        for lead in leads:
            lead = OutreachGenerator.enrich_lead_with_outreach(lead)
            all_leads.append(lead)
            table.add_row(
                lead.get("name", ""),
                lead.get("title", ""),
                lead.get("location", ""),
                lead.get("linkedin_url", "")
            )

        console.print(table)

    # Export results if requested
    if args.export and all_leads:
        export_path = args.export
        if export_path.endswith(".json"):
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(all_leads, f, indent=2)
            console.print(f"\n[bold green][Success] Exported {len(all_leads)} leads to JSON:[/bold green] {export_path}")
        else:
            df_out = pd.DataFrame(all_leads)
            df_out.to_csv(export_path, index=False)
            console.print(f"\n[bold green][Success] Exported {len(all_leads)} leads to CSV:[/bold green] {export_path}")


if __name__ == "__main__":
    run_cli()
