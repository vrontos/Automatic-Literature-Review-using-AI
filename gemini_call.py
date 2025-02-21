import pandas as pd
import google.generativeai as genai
import time
import json
import os

# --- Constants ---
# Use environment variables for sensitive paths and API key
INPUT_FILE = os.environ.get("OPENALEX_INPUT_FILE", "results_openalex.xlsx")
OUTPUT_FILE = os.environ.get("GEMINI_OUTPUT_FILE", "results_gemini.xlsx")
BATCH_SIZE = 10   # Process 10 papers per API call
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")  # Must be set in environment

# --- Configure Gemini API ---
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")  # Alternatives: gemini-2.0-flash-lite-preview-02-05 / gemini-1.5-flash / gemini-1.5-pro

# --- Load the Excel file with all papers ---
df = pd.read_excel(INPUT_FILE)
total_rows = len(df)
print(f"Total rows found: {total_rows}")

# --- Helper Function to Clean JSON ---
def extract_json(text):
    """
    Remove markdown code fences (if any) from the text so that it becomes valid JSON.
    """
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("\n", 1)
        if len(parts) == 2:
            text = parts[1]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

# --- Function to Classify a Batch of Papers ---
def classify_papers(batch):
    """
    Constructs a prompt containing the title, abstract, and concepts for each paper in the batch,
    and sends it to Gemini to classify whether each paper fits the scoping review.
    """
    prompt = """
You are a strict classifier for academic papers. 
Your task is to determine if each paper fits in a scoping review about using Electrical Muscle Stimulation (EMS) for proprioceptive or kinesthetic feedback in AR/VR haptic feedback. 
Try to be strict and ONLY mark as True those that really possess all the necessary components (EMS & haptic feedback in AR/VR).
Avoid all papers that have something to do with the brain, or restoring functions for damaged people, since this is a completely different direction.

### **Review Scope:**
We are investigating **Electrical Muscle Stimulation (EMS)** used specifically for **proprioceptive or kinesthetic feedback** within **AR/VR haptic feedback systems**. Papers must:
- Explicitly involve **EMS** as a mechanism.
- Focus on **haptic feedback** (proprioceptive or kinesthetic) in **AR/VR contexts**.
- Target healthy individuals, not medical rehabilitation or neurological restoration.

### **Exclusion Criteria:**
- Studies focusing on **brain stimulation**, **neural interfaces**, or **cognitive effects**.
- Studies aimed at **restoring functions** in individuals with damage (e.g., stroke, spinal injury).
- Studies using EMS without a clear link to **AR/VR haptic feedback**.
- Studies lacking explicit mention of **proprioceptive or kinesthetic feedback**.

### **Your Task:**
Read the **Title, Abstract, and Concepts** of each paper and determine if it should be included in our scoping review. Respond ONLY in JSON format with True or False values. Only mark as **True** if the paper strongly aligns with all criteria.

### **Example Output:**
```json
{
  "Paper 1": true,
  "Paper 2": false,
  "Paper 3": true
}
