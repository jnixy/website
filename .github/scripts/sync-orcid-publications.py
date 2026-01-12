#!/usr/bin/env python3
"""
ORCID Publications Sync for Hugo Academic Theme
Fetches publications from ORCID API and generates Hugo markdown files
"""

import requests
import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import argparse
import yaml


class ORCIDPublicationSync:
    def __init__(self, orcid_id: str, content_dir: str = "content/publication"):
        self.orcid_id = orcid_id
        self.content_dir = Path(content_dir)
        self.base_url = "https://pub.orcid.org/v3.0"
        
    def fetch_works(self) -> List[Dict]:
        """Fetch all works from ORCID API"""
        url = f"{self.base_url}/{self.orcid_id}/works"
        headers = {"Accept": "application/json"}
        
        print(f"Fetching works from ORCID: {self.orcid_id}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        works = []
        
        # Extract work summaries
        if "group" in data:
            for group in data["group"]:
                if "work-summary" in group:
                    # Get the first work summary from each group
                    work_summary = group["work-summary"][0]
                    works.append(work_summary)
        
        print(f"Found {len(works)} works in ORCID profile")
        return works
    
    def fetch_work_details(self, put_code: str) -> Dict:
        """Fetch detailed information for a specific work"""
        url = f"{self.base_url}/{self.orcid_id}/work/{put_code}"
        headers = {"Accept": "application/json"}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    def extract_metadata(self, work_detail: Dict) -> Dict:
        """Extract relevant metadata from ORCID work detail"""
        metadata = {
            "title": "",
            "authors": [],
            "publication_date": "",
            "journal": "",
            "doi": "",
            "url": "",
            "abstract": "",
            "publication_type": "",
            "put_code": work_detail.get("put-code", "")
        }
        
        # Extract title
        if "title" in work_detail and work_detail["title"]:
            if "title" in work_detail["title"]:
                metadata["title"] = work_detail["title"]["title"]["value"]
        
        # Extract publication date
        if "publication-date" in work_detail and work_detail["publication-date"]:
            pub_date = work_detail["publication-date"]
            year = pub_date.get("year", {}).get("value", "")
            month = pub_date.get("month", {}).get("value", "01")
            day = pub_date.get("day", {}).get("value", "01")
            
            if year:
                # Ensure month and day are two digits
                month = str(month).zfill(2) if month else "01"
                day = str(day).zfill(2) if day else "01"
                metadata["publication_date"] = f"{year}-{month}-{day}"
        
        # Extract journal/publication name
        if "journal-title" in work_detail and work_detail["journal-title"]:
            metadata["journal"] = work_detail["journal-title"]["value"]
        
        # Extract DOI and URLs
        if "external-ids" in work_detail and work_detail["external-ids"]:
            if "external-id" in work_detail["external-ids"]:
                for ext_id in work_detail["external-ids"]["external-id"]:
                    if ext_id["external-id-type"] == "doi":
                        metadata["doi"] = ext_id["external-id-value"]
                        metadata["url"] = f"https://doi.org/{metadata['doi']}"
        
        # Extract publication type
        if "type" in work_detail:
            metadata["publication_type"] = work_detail["type"]
        
        # Extract contributors/authors
        if "contributors" in work_detail and work_detail["contributors"]:
            if "contributor" in work_detail["contributors"]:
                for contributor in work_detail["contributors"]["contributor"]:
                    if "credit-name" in contributor and contributor["credit-name"]:
                        author_name = contributor["credit-name"]["value"]
                        metadata["authors"].append(author_name)
        
        return metadata
    
    def create_slug(self, title: str, year: str = "") -> str:
        """Create a URL-friendly slug from title"""
        # Convert to lowercase and replace spaces with hyphens
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        
        # Limit length
        slug = slug[:60]
        
        # Add year prefix if available
        if year:
            slug = f"{year}-{slug}"
        
        return slug
    
    def work_exists(self, slug: str) -> bool:
        """Check if a publication already exists in Hugo content"""
        pub_dir = self.content_dir / slug
        return pub_dir.exists() and (pub_dir / "index.md").exists()
    
    def generate_hugo_frontmatter(self, metadata: Dict) -> str:
        """Generate Hugo Academic theme frontmatter for a publication"""
        # Extract year from date
        year = metadata["publication_date"].split("-")[0] if metadata["publication_date"] else ""
        
        # Map ORCID publication types to Hugo Academic types
        type_mapping = {
            "journal-article": "2",  # Journal article
            "book": "5",  # Book
            "book-chapter": "6",  # Book chapter
            "conference-paper": "1",  # Conference paper
            "preprint": "3",  # Preprint
            "report": "4",  # Report
        }
        
        pub_type = type_mapping.get(metadata["publication_type"].lower(), "0")
        
        # Build frontmatter dictionary
        frontmatter = {
            "title": metadata["title"],
            "authors": metadata["authors"],
            "date": metadata["publication_date"],
            "publishDate": metadata["publication_date"],
            "publication_types": [pub_type],
            "publication": metadata["journal"],
            "abstract": metadata["abstract"],
            "featured": False,
            "doi": metadata["doi"],
            "url_pdf": "",  # To be filled in manually
            "url_code": "",
            "url_dataset": "",
            "url_poster": "",
            "url_project": "",
            "url_slides": "",
            "url_source": "",
            "url_video": "",
        }
        
        # Add DOI link if available
        if metadata["doi"]:
            frontmatter["links"] = [
                {"name": "DOI", "url": f"https://doi.org/{metadata['doi']}"}
            ]
        
        # Convert to YAML
        yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        return f"---\n{yaml_str}---\n"
    
    def create_publication_file(self, metadata: Dict) -> str:
        """Create a new Hugo publication markdown file"""
        year = metadata["publication_date"].split("-")[0] if metadata["publication_date"] else ""
        slug = self.create_slug(metadata["title"], year)
        
        # Check if already exists
        if self.work_exists(slug):
            print(f"  ⏭️  Publication already exists: {slug}")
            return None
        
        # Create directory
        pub_dir = self.content_dir / slug
        pub_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate content
        frontmatter = self.generate_hugo_frontmatter(metadata)
        
        # Create index.md
        index_file = pub_dir / "index.md"
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(frontmatter)
            f.write("\n")
            if metadata["abstract"]:
                f.write(metadata["abstract"])
                f.write("\n")
        
        print(f"  ✅ Created: {slug}")
        return slug
    
    def sync(self, dry_run: bool = False) -> Dict:
        """Main sync function"""
        print("=" * 60)
        print("ORCID Publications Sync")
        print("=" * 60)
        
        results = {
            "total_works": 0,
            "new_publications": [],
            "existing_publications": [],
            "errors": []
        }
        
        try:
            # Fetch all works
            works = self.fetch_works()
            results["total_works"] = len(works)
            
            # Process each work
            for i, work_summary in enumerate(works, 1):
                try:
                    put_code = work_summary.get("put-code")
                    title = work_summary.get("title", {}).get("title", {}).get("value", "Unknown")
                    
                    print(f"\n[{i}/{len(works)}] Processing: {title[:60]}...")
                    
                    # Fetch detailed information
                    work_detail = self.fetch_work_details(put_code)
                    
                    # Extract metadata
                    metadata = self.extract_metadata(work_detail)
                    
                    if not metadata["title"]:
                        print("  ⚠️  Skipping: No title found")
                        continue
                    
                    # Create slug and check if exists
                    year = metadata["publication_date"].split("-")[0] if metadata["publication_date"] else ""
                    slug = self.create_slug(metadata["title"], year)
                    
                    if self.work_exists(slug):
                        results["existing_publications"].append(slug)
                        print(f"  ⏭️  Already exists: {slug}")
                        continue
                    
                    # Create new publication (unless dry run)
                    if not dry_run:
                        created_slug = self.create_publication_file(metadata)
                        if created_slug:
                            results["new_publications"].append(created_slug)
                    else:
                        print(f"  🔍 Would create: {slug}")
                        results["new_publications"].append(slug)
                    
                except Exception as e:
                    error_msg = f"Error processing work {put_code}: {str(e)}"
                    print(f"  ❌ {error_msg}")
                    results["errors"].append(error_msg)
            
        except Exception as e:
            error_msg = f"Fatal error during sync: {str(e)}"
            print(f"\n❌ {error_msg}")
            results["errors"].append(error_msg)
        
        # Print summary
        print("\n" + "=" * 60)
        print("SYNC SUMMARY")
        print("=" * 60)
        print(f"Total works in ORCID: {results['total_works']}")
        print(f"New publications created: {len(results['new_publications'])}")
        print(f"Existing publications: {len(results['existing_publications'])}")
        print(f"Errors: {len(results['errors'])}")
        
        if results["new_publications"]:
            print("\n📝 New publications:")
            for slug in results["new_publications"]:
                print(f"  - {slug}")
        
        if results["errors"]:
            print("\n⚠️  Errors encountered:")
            for error in results["errors"]:
                print(f"  - {error}")
        
        return results


def main():
    parser = argparse.ArgumentParser(
        description="Sync publications from ORCID to Hugo Academic site"
    )
    parser.add_argument(
        "--orcid-id",
        required=True,
        help="ORCID ID (e.g., 0000-0002-3812-8590)"
    )
    parser.add_argument(
        "--content-dir",
        default="content/publication",
        help="Path to Hugo publication content directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without actually creating files"
    )
    
    args = parser.parse_args()
    
    # Initialize syncer
    syncer = ORCIDPublicationSync(
        orcid_id=args.orcid_id,
        content_dir=args.content_dir
    )
    
    # Run sync
    results = syncer.sync(dry_run=args.dry_run)
    
    # Exit with error code if there were errors
    if results["errors"]:
        exit(1)


if __name__ == "__main__":
    main()
