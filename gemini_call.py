import pandas as pd
import google.generativeai as genai
import time
import json
import os # ADDED IMPORT

# --- Constants ---
# Path to your input Excel file containing all papers (with columns: Article Title, Abstract, Concepts)
output_dir = "output_data" # Ensure this matches the directory name in openalex_call.py
INPUT_FILE = f"{output_dir}/Electromyostimulation_MotorLearning_OpenAlex.xlsx" # Relative input path
# Output file where classification results will be saved
OUTPUT_FILE = f"{output_dir}/Electromyostimulation_MotorLearning_Gemini.xlsx" # Relative output path
BATCH_SIZE = 10   # Process 10 papers per API call
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") # Get API key from environment variable
if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY environment variable not set. "
                         "Please set it as instructed in the README.")


# --- Configure Gemini API ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash") #alternatives: gemini-2.0-flash-lite-preview-02-05 / gemini-1.5-flash / gemini-1.5-pro

# --- Load the Excel file with all papers (approx 4k records) ---
df = pd.read_excel(INPUT_FILE)
total_rows = len(df)
print(f"Total rows found: {total_rows}")

# --- Helper Function to Clean JSON ---
def extract_json(text):
    """
    Remove markdown code fences (if any) from the text so that it becomes valid JSON.
    """
    text = text.strip()
    # Remove starting code fence if present (e.g., or
json)
    if text.startswith(""):
        parts = text.split("\n", 1)
        if len(parts) == 2:
            text = parts[1]
    # Remove ending code fence if present
    if text.endswith("
"):
        text = text[:-3]
    return text.strip()

# --- Function to Classify a Batch of Papers ---
def classify_papers(batch):
    """
    Constructs a prompt containing the title, abstract, and concepts for each paper in the batch,
    and sends it to Gemini to classify whether each paper fits the scoping review.
    The expected response is a JSON object with keys like "Paper 1", "Paper 2", etc.,
    and boolean values (true/false).
    """
    prompt = """
You are a strict classifier for academic papers.
Your task is to determine if each paper fits in a scoping review about using Electrical Muscle Stimulation (EMS) for proprioceptive or kinesthetic feedback in AR/VR haptic feedback.
Try to be strict and ONLY mark as True these that really posess all the necessary components (EMS & haptic feedback).
Avoid all these papers that have sth to do with the brain, or restoring functions from damaged people, since this is a completely different direction.
Respond ONLY in JSON format with True or False values.

### **Example Output:**json
{
  "Paper 1": true,
  "Paper 2": false,
  "Paper 3": true
}


Now, classify the following papers:
"""
    # Append each paper's details to the prompt.
    for count, (_, row) in enumerate(batch.iterrows(), start=1):
        title = row["Article Title"]
        abstract = row["Abstract"]
        concepts = row["Concepts"]
        prompt += f"""
Paper {count}:
**Title:** {title}
**Abstract:** {abstract}
**Concepts:** {concepts}
"""
    try:
        response = model.generate_content(prompt)
        return response.text  # Return the raw text response from Gemini
    except Exception as e:
        print(f"Error in API call: {e}")
        return None

# --- Process All Papers in Batches ---
results = []
# Process the papers in batches of 20.
for i in range(0, total_rows, BATCH_SIZE):
    batch = df.iloc[i: i+BATCH_SIZE]
    print(f"Processing batch {i+1} to {min(i+BATCH_SIZE, total_rows)}...")

    json_response = classify_papers(batch)

    if json_response:
        # Clean the response text to remove any markdown formatting if present.
        cleaned_json = extract_json(json_response)
        try:
            classification = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            classification = {}
        # For each paper in the batch, record the classification result.
        for count, (_, row) in enumerate(batch.iterrows(), start=1):
            result = {
                "Article Title": row["Article Title"],
                "Abstract": row["Abstract"],
                "Concepts": row["Concepts"],
                "Fits in scoping review": classification.get(f"Paper {count}", "Error")
            }
            results.append(result)
    else:
        # If no response was received, mark these papers accordingly.
        for count, (_, row) in enumerate(batch.iterrows(), start=1):
            result = {
                "Article Title": row["Article Title"],
                "Abstract": row["Abstract"],
                "Concepts": row["Concepts"],
                "Fits in scoping review": "No Response"
            }
            results.append(result)

    # Respect Gemini's rate limit: 15 requests per minute (i.e. one request every 4 seconds).
    time.sleep(4)  # Pause 4 seconds between API calls

print(f"Processed {len(results)} records in total.")
df_results = pd.DataFrame(results)
df_results.to_excel(OUTPUT_FILE, index=False)
print(f"Classification complete. Results saved to {OUTPUT_FILE}")
