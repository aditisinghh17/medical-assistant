import os
import re
import json
import base64
import pdfplumber
import io
import pandas as pd
import groq
from PIL import Image
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize Groq client only
groq_client = groq.Groq(api_key="GROQ_API_KEY")


# ---------------- 🧾 FILE TYPE DETECTION ----------------
def get_file_type(file_path):
    """Detect file type based on extension and content"""
    file_path = Path(file_path)
    extension = file_path.suffix.lower()
    
    if extension == '.pdf':
        return 'pdf'
    elif extension in ['.csv', '.txt', '.tsv']:
        return 'csv'
    elif extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        return 'image'
    else:
        # Try to detect by content
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header.startswith(b'%PDF'):
                    return 'pdf'
        except:
            pass
        return 'unknown'


# ---------------- 🧾 SIMPLIFIED PDF PROCESSING ----------------
def extract_lab_data_from_pdf(pdf_path, tables_dir, images_dir):
    """
    Simplified PDF processing using only pdfplumber
    """
    file_type = get_file_type(pdf_path)
    if file_type != 'pdf':
        print(f"Warning: File {pdf_path} is not a PDF (detected as {file_type})")
        if file_type == 'csv':
            return process_csv_file(pdf_path, tables_dir)
        else:
            return {"error": f"Unsupported file type: {file_type}"}
    
    return extract_text_with_pdfplumber(pdf_path, tables_dir, images_dir)


def process_csv_file(csv_path, tables_dir):
    """Process CSV files directly"""
    try:
        df = pd.read_csv(csv_path)
        
        # Save to tables directory
        output_path = os.path.join(tables_dir, f"processed_{os.path.basename(csv_path)}")
        df.to_csv(output_path, index=False)
        
        return {
            "text": f"CSV file processed: {os.path.basename(csv_path)}\n" + df.to_string(),
            "tables": [df.to_dict(orient="records")],
            "metadata": {
                "source_file": os.path.basename(csv_path),
                "type": "csv",
                "shape": df.shape
            }
        }
    except Exception as e:
        return {
            "text": f"Error processing CSV: {str(e)}",
            "tables": [],
            "metadata": {
                "source_file": os.path.basename(csv_path),
                "error": str(e)
            }
        }


def extract_text_with_pdfplumber(pdf_path, tables_dir, images_dir):
    """
    Extract text and tables from PDF using pdfplumber
    """
    try:
        all_text = []
        all_tables = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text
                text = page.extract_text()
                if text:
                    page_text = f"\n\nPage {page_num}\n{'=' * 40}\n{text}"
                    all_text.append(page_text)
                
                # Extract tables with improved settings
                tables = page.extract_tables(
                    table_settings={
                        "vertical_strategy": "lines_strict",
                        "horizontal_strategy": "lines_strict",
                        "min_words_vertical": 1,
                        "min_words_horizontal": 1,
                        "intersection_tolerance": 3,
                        "intersection_x_tolerance": 3,
                        "intersection_y_tolerance": 3
                    }
                )
                
                for table_num, table in enumerate(tables):
                    if table and len(table) > 1:  # Need at least header + 1 row
                        try:
                            # Clean table data
                            cleaned_table = []
                            for row in table:
                                cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                                if any(cleaned_row):  # Skip empty rows
                                    cleaned_table.append(cleaned_row)
                            
                            if len(cleaned_table) > 1:
                                # Create DataFrame with first row as headers
                                headers = cleaned_table[0]
                                data_rows = cleaned_table[1:]
                                
                                df = pd.DataFrame(data_rows, columns=headers)
                                
                                # Clean up DataFrame
                                df = df.dropna(axis=1, how="all")  # Remove completely empty columns
                                df = df.dropna(axis=0, how="all")  # Remove completely empty rows
                                
                                # Clean column names
                                df.columns = [str(col).strip() for col in df.columns]
                                
                                if not df.empty and len(df.columns) > 0:
                                    csv_name = os.path.join(
                                        tables_dir, 
                                        f"table_page{page_num}_table{table_num+1}.csv"
                                    )
                                    df.to_csv(csv_name, index=False)
                                    all_tables.append(df.to_dict(orient="records"))
                                    print(f"Saved table: {csv_name}")
                                    
                        except Exception as e:
                            print(f"Table extraction failed for page {page_num}, table {table_num}: {e}")
                
                # Extract images if any
                try:
                    if hasattr(page, 'images') and page.images:
                        for img_index, img in enumerate(page.images):
                            try:
                                # Extract image using pdfplumber's method
                                img_obj = page.crop(img['bbox']).to_image(resolution=150)
                                img_filename = f"page_{page_num}_img_{img_index+1}.png"
                                img_path = os.path.join(images_dir, img_filename)
                                img_obj.save(img_path)
                                print(f"Saved image: {img_path}")
                            except Exception as img_error:
                                print(f"Failed to extract image from page {page_num}: {img_error}")
                except Exception as img_page_error:
                    print(f"Image extraction failed for page {page_num}: {img_page_error}")
        
        full_text = "\n\n".join(all_text)
        
        return {
            "text": full_text,
            "tables": all_tables,
            "metadata": {
                "source_pdf": os.path.basename(pdf_path),
                "method": "pdfplumber",
                "pages_processed": len(all_text),
                "tables_extracted": len(all_tables)
            }
        }
    
    except Exception as e:
        print(f"PDF extraction failed: {e}")
        return {
            "text": f"Error: Could not extract text from PDF: {str(e)}",
            "tables": [],
            "metadata": {
                "source_pdf": os.path.basename(pdf_path),
                "error": str(e)
            }
        }


# ---------------- 🩻 X-RAY ANALYSIS ----------------
def encode_image(image_path):
    """Encode image to base64 with better error handling"""
    try:
        # Verify file exists and is readable
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Check file size (avoid very large files)
        file_size = os.path.getsize(image_path)
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            print(f"Warning: Large image file ({file_size / (1024*1024):.1f}MB): {image_path}")
        
        with open(image_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode("utf-8")
            return encoded
            
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None


def describe_xray_with_groq(image_path):
    """X-ray analysis using Groq vision model"""
    if not os.path.exists(image_path):
        return f"Error: Image file not found: {image_path}"
    
    try:
        image_base64 = encode_image(image_path)
        if not image_base64:
            return "Error: Could not encode image"

        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this medical image and provide a structured clinical description:

**OBJECTIVE ANALYSIS ONLY - NO DIAGNOSIS**

1. **Image Type & Quality**: What type of medical image is this? (X-ray, CT, MRI, etc.) Comment on technical quality.

2. **Anatomical Region**: What body part/region is shown?

3. **Image Orientation**: Describe the view/projection (AP, lateral, oblique, etc.)

4. **Visible Structures**: List the anatomical structures that are clearly visible.

5. **Observations**: Describe any notable findings, abnormalities, or normal variations you can see.

6. **Image Artifacts**: Note any technical issues, artifacts, or limitations.

IMPORTANT: 
- Provide ONLY objective descriptions of what is visible
- Do NOT provide diagnoses, interpretations, or medical advice
- Focus on structural and visual elements only
- Use appropriate medical terminology"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=1000
        )
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Groq Vision error: {e}")
        # Fallback: basic image info
        try:
            img = Image.open(image_path)
            return f"""Image Analysis Fallback:
- File: {os.path.basename(image_path)}
- Dimensions: {img.size[0]} x {img.size[1]} pixels
- Color Mode: {img.mode}
- File Size: {os.path.getsize(image_path) / 1024:.1f} KB
- Error: {str(e)}

Note: Unable to perform AI analysis due to technical error."""
        except Exception as img_error:
            return f"Complete image analysis failure: {str(img_error)}"


# ---------------- 🧠 SOAP NOTE GENERATION ----------------
def generate_soap_note(lab_data, xray_description, subjective_note=None):
    """Generate SOAP note with improved structure and error handling"""
    subjective_note = subjective_note or "Patient presents with chief complaint requiring clinical evaluation."
    
    # Process lab data more intelligently
    if isinstance(lab_data, dict):
        lab_str = json.dumps(lab_data, indent=2)
    elif isinstance(lab_data, list):
        lab_str = "\n".join(str(item) for item in lab_data)
    else:
        lab_str = str(lab_data)

    prompt = f"""You are a medical professional creating a SOAP note. Based on the provided information, generate a comprehensive but concise SOAP note.

**SUBJECTIVE:**
{subjective_note}

**OBJECTIVE DATA:**
Laboratory Results:
{lab_str}

Imaging Findings:
{xray_description}

**INSTRUCTIONS:**
- Create a properly structured SOAP note
- Be thorough but concise
- Use appropriate medical terminology
- Include relevant normal and abnormal findings
- Provide appropriate clinical reasoning
- Suggest appropriate follow-up when indicated

**OUTPUT FORMAT:** Return ONLY valid JSON with this exact structure:

{{
    "Subjective": "Patient presentation and chief complaint...",
    "Objective": {{
        "Vital_Signs": "Record if available, otherwise note not documented",
        "Physical_Examination": "Document examination findings",
        "Laboratory_Results": "Summarize key lab findings with values and interpretation",
        "Imaging_Studies": "Summarize imaging findings objectively"
    }},
    "Assessment": "Clinical impression based on subjective and objective data",
    "Plan": {{
        "Immediate": "Immediate interventions or treatments",
        "Follow_up": "Follow-up appointments and monitoring",
        "Patient_Education": "Education and counseling provided",
        "Additional_Studies": "Any additional tests or consultations needed"
    }}
}}"""

    try:
        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000
        )

        content = response.choices[0].message.content.strip()
        
        # Clean up JSON formatting
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as je:
            print(f"JSON parsing error: {je}")
            # Try to fix common JSON issues
            content = re.sub(r',(\s*[}\]])', r'\1', content)  # Remove trailing commas
            return json.loads(content)
            
    except Exception as e:
        print(f"SOAP generation error: {e}")
        return {
            "Subjective": subjective_note,
            "Objective": {
                "Vital_Signs": "Not documented",
                "Physical_Examination": "Not documented",
                "Laboratory_Results": str(lab_data) if lab_data else "No lab results provided",
                "Imaging_Studies": xray_description or "No imaging studies provided"
            },
            "Assessment": f"Unable to generate assessment due to processing error: {str(e)}",
            "Plan": {
                "Immediate": "Review all available data",
                "Follow_up": "Clinical correlation recommended",
                "Patient_Education": "Discuss findings with patient",
                "Additional_Studies": "Consider additional evaluation as clinically indicated"
            }
        }


# ---------------- 🚀 MAIN PIPELINE ----------------
def run_pipeline(text_input=None, text_file=None, lab_files=None, xray_files=None):
    """
    Main pipeline with simplified PDF processing using only pdfplumber
    """
    lab_files = lab_files or []
    xray_files = xray_files or []

    # Initialize results
    lab_analysis = []
    xray_findings = []
    combined_text = text_input or ""

    # Process text file
    if text_file and os.path.exists(text_file):
        try:
            with open(text_file, "r", encoding="utf-8") as f:
                file_content = f.read()
                combined_text += f"\n\n--- Content from {os.path.basename(text_file)} ---\n{file_content}"
        except Exception as e:
            print(f"Error reading text file {text_file}: {e}")

    # Create output directories
    os.makedirs("./tables", exist_ok=True)
    os.makedirs("./images", exist_ok=True)

    # Process lab files (PDFs and CSVs)
    for lab_path in lab_files:
        if not os.path.exists(lab_path):
            print(f"Warning: Lab file not found: {lab_path}")
            continue
            
        print(f"📄 Processing lab file: {lab_path}")
        file_type = get_file_type(lab_path)
        print(f"   Detected file type: {file_type}")
        
        try:
            if file_type == 'pdf':
                lab_result = extract_lab_data_from_pdf(lab_path, "./tables", "./images")
            elif file_type == 'csv':
                lab_result = process_csv_file(lab_path, "./tables")
            else:
                lab_result = {
                    "text": f"Unsupported file type: {file_type}",
                    "tables": [],
                    "metadata": {"error": f"Unsupported file type: {file_type}"}
                }
            
            lab_analysis.append(lab_result)
            print(f"   ✓ Processed successfully")
            
        except Exception as e:
            print(f"   ✗ Error processing {lab_path}: {e}")
            lab_analysis.append({
                "text": f"Error processing {os.path.basename(lab_path)}: {str(e)}",
                "tables": [],
                "metadata": {"error": str(e), "source_file": os.path.basename(lab_path)}
            })

    # Process X-ray files
    for xray_path in xray_files:
        if not os.path.exists(xray_path):
            print(f"Warning: X-ray file not found: {xray_path}")
            continue
            
        print(f"🩻 Processing X-ray: {xray_path}")
        try:
            xray_result = describe_xray_with_groq(xray_path)
            xray_findings.append({
                "file": os.path.basename(xray_path),
                "description": xray_result,
                "path": xray_path
            })
            print(f"   ✓ Analyzed successfully")
        except Exception as e:
            print(f"   ✗ Error processing {xray_path}: {e}")
            xray_findings.append({
                "file": os.path.basename(xray_path),
                "description": f"Error analyzing X-ray: {str(e)}",
                "path": xray_path,
                "error": str(e)
            })

    # Combine all findings for SOAP note generation
    all_lab_data = {}
    for lab in lab_analysis:
        if lab.get("tables"):
            for i, table in enumerate(lab["tables"]):
                all_lab_data[f"Table_{i+1}"] = table

    xray_text = "\n\n".join([
        f"=== {x['file']} ===\n{x['description']}" 
        for x in xray_findings
    ])

    # Generate SOAP note
    print("📝 Generating SOAP note...")
    try:
        soap_note = generate_soap_note(
            lab_data=all_lab_data,
            xray_description=xray_text,
            subjective_note=combined_text.strip() or None
        )
        print("   ✓ SOAP note generated successfully")
    except Exception as e:
        print(f"   ✗ SOAP note generation failed: {e}")
        soap_note = {"error": f"SOAP generation failed: {str(e)}"}

    # Compile results
    results = {
        "summary": {
            "processed_files": {
                "lab_files": len(lab_files),
                "xray_files": len(xray_files),
                "text_files": 1 if text_file else 0
            },
            "processing_method": "pdfplumber_only",
            "lab_analysis": lab_analysis,
            "xray_findings": xray_findings
        },
        "soap_note": soap_note
    }
    
    print("\n🎉 Pipeline completed!")
    print(f"   Lab files processed: {len(lab_analysis)}")
    print(f"   X-ray files processed: {len(xray_findings)}")
    print(f"   Tables extracted: {sum(len(lab.get('tables', [])) for lab in lab_analysis)}")
    
    return results


# ---------------- 🧪 EXAMPLE USAGE ----------------
if __name__ == "__main__":
    # Example usage
    result = run_pipeline(
        text_input="Patient presents with chest pain and shortness of breath.",
        lab_files=["path/to/lab_report.pdf", "path/to/blood_work.csv"],
        xray_files=["path/to/chest_xray.jpg"]
    )
    
    # Save results
    with open("medical_analysis_results.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print("Results saved to medical_analysis_results.json")