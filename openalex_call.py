import requests
import pandas as pd
import time
import re

def reconstruct_abstract(inverted_index):
    """
    Reconstruct an abstract string from OpenAlex's abstract_inverted_index.
    """
    position_to_token = {}
    for token, positions in inverted_index.items():
        for pos in positions:
            position_to_token[pos] = token
    if position_to_token:
        sorted_positions = sorted(position_to_token.keys())
        abstract_text = " ".join(position_to_token[pos] for pos in sorted_positions)
        return abstract_text
    else:
        return ""

def clean_text(text):
    """
    Remove non-printable and control characters from a string.
    """
    if isinstance(text, str):
        return re.sub(r'[\x00-\x1F\x7F]', '', text)
    else:
        return text

# Define the query for filtering OpenAlex works.
query = (
    "title.search:(electromyostimulat* OR electrostimulat* OR "
    "\"muscle stimul*\" OR \"muscle stimulation\" OR "
    "\"electric stimul*\" OR \"electric stimulation\" OR "
    "\"fiber stimul*\" OR \"fiber stimulation\"),"
    "default.search:("
    "\"motor learn*\" OR \"motor train*\" OR "
    "move* OR motion OR pose* OR posture* OR "
    "kinematic* OR kinetic* OR kinaesthetic* OR "
    "tactil* OR force* OR "
    "\"virtual reality\" OR \"augmented reality\" OR "
    "\"mixed reality\" OR hapt* OR kinesth*)"
)

# Base URL for OpenAlex works
url = "https://api.openalex.org/works"

# Set up initial parameters
params = {
    "filter": query,
    "per_page": 200  # Adjust as needed
}

# Initial API request to check total matches
response = requests.get(url, params=params)
data = response.json()
total_matches = data.get("meta", {}).get("count", 0)
print("Total matches for the query:", total_matches)

# Ask the user if they want to proceed
proceed = input("Do you want to proceed to retrieve all available records? (y/n): ")
if proceed.lower() != "y":
    print("Exiting without retrieving records.")
    exit()

# Retrieve records using pagination
per_page = 200
cursor = "*"
records_wide = []

print("Starting wide search using revised filter query...")
while True:
    params = {
        "filter": query,
        "per_page": per_page,
        "cursor": cursor
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print("Error fetching data:", response.status_code)
        break

    data = response.json()
    works = data.get("results", [])
    if not works:
        print("No more records available.")
        break

    for work in works:
        # Basic metadata extraction and cleaning of text fields
        title = clean_text(work.get("display_name", ""))
        
        # Abstract extraction with fallback for inverted index
        abstract = work.get("abstract", "")
        if not abstract or abstract.strip() == "":
            inverted = work.get("abstract_inverted_index", None)
            if inverted:
                abstract = reconstruct_abstract(inverted)
        if not abstract or abstract.strip() == "":
            abstract = "No abstract available"
        abstract = clean_text(abstract)
        
        # Extract concepts
        concepts_list = work.get("concepts", [])
        concepts = ", ".join([clean_text(c.get("display_name", "")) for c in concepts_list])
        
        # Metadata extraction
        openalex_id = work.get("id", "")
        doi = work.get("doi", "")
        
        primary_location = work.get("primary_location") or {}
        url_primary = primary_location.get("url", "")
        
        publication_date = work.get("publication_date", "")
        publication_year = work.get("publication_year", "")
        language = work.get("language", "")
        
        # Authors and affiliations extraction
        authorships = work.get("authorships", [])
        authors = []
        affiliations = []
        for authorship in authorships:
            author_obj = authorship.get("author", {})
            author_name = clean_text(author_obj.get("display_name", ""))
            if author_name:
                authors.append(author_name)
            inst_list = authorship.get("institutions", [])
            for inst in inst_list:
                inst_name = clean_text(inst.get("display_name", ""))
                if inst_name and inst_name not in affiliations:
                    affiliations.append(inst_name)
        authors_str = ", ".join(authors)
        affiliations_str = ", ".join(affiliations)
        
        # Venue, citation, and open access information extraction
        host_venue = work.get("host_venue", {})
        venue = clean_text(host_venue.get("display_name", ""))
        
        cited_by_count = work.get("cited_by_count", 0)
        reference_count = work.get("reference_count", len(work.get("referenced_works", [])))
        
        open_access = work.get("open_access", {})
        is_oa = open_access.get("is_oa", False)
        oa_status = open_access.get("oa_status", "")
        oa_url = open_access.get("url_for_landing_page", "")
        license_info = open_access.get("license", "")
        open_access_info = f"OA: {is_oa}, Status: {oa_status}, Landing: {oa_url}, License: {license_info}"
        
        records_wide.append({
            "Article Title": title,
            "Abstract": abstract,
            "Concepts": concepts,
            "OpenAlex ID": openalex_id,
            "DOI": doi,
            "URL": url_primary,
            "Publication Date": publication_date,
            "Publication Year": publication_year,
            "Language": language,
            "Authors": authors_str,
            "Affiliations": affiliations_str,
            "Venue": venue,
            "Cited By Count": cited_by_count,
            "Reference Count": reference_count,
            "Open Access Info": open_access_info
        })

    # Update the cursor for the next page
    meta = data.get("meta", {})
    new_cursor = meta.get("next_cursor", None)
    if not new_cursor or new_cursor == cursor:
        print("No further pages available.")
        break
    cursor = new_cursor
    print(f"Collected {len(records_wide)} records so far...")
    time.sleep(1)

print(f"Total records retrieved in wide search: {len(records_wide)}")
results_wide = pd.DataFrame(records_wide)

# Save the results to an Excel file (using a generic file name)
output_wide = "openalex_results.xlsx"
results_wide.to_excel(output_wide, index=False)
print(f"Wide results saved to '{output_wide}'")
