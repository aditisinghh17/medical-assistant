from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
import uuid
import tempfile
import shutil
from pathlib import Path

# Import the simplified pipeline
from ai_pipeline import run_pipeline

app = FastAPI(
    title="Medical SOAP Note Generator",
    description="Generate SOAP notes from lab reports and X-ray images",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # your React domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global temp directory for session management
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

def cleanup_temp_files(file_paths: List[str]):
    """Clean up temporary files after processing"""
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Warning: Could not remove temp file {file_path}: {e}")

def validate_file_size(file: UploadFile, max_size_mb: int = 50):
    """Validate file size"""
    if hasattr(file, 'size') and file.size:
        if file.size > max_size_mb * 1024 * 1024:
            return False, f"File {file.filename} exceeds {max_size_mb}MB limit"
    return True, ""

def validate_file_type(file: UploadFile, allowed_extensions: List[str]):
    """Validate file type based on extension"""
    if not file.filename:
        return False, "No filename provided"
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        return False, f"File type {file_ext} not supported. Allowed: {', '.join(allowed_extensions)}"
    return True, ""

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Medical SOAP Note Generator API",
        "status": "running",
        "version": "2.0.0 (Simplified - PDFPlumber Only)"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "processing_method": "pdfplumber_only",
        "supported_formats": {
            "lab_files": [".pdf", ".csv", ".txt"],
            "xray_files": [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
        }
    }

@app.post("/generate-soap")
async def generate_soap(
    text_input: Optional[str] = Form(None),
    text_file: Optional[UploadFile] = File(None),
    table_files: List[UploadFile] = File([]),
    xray_images: List[UploadFile] = File([]),
):
    """
    Generate SOAP note from uploaded files and text input
    
    - **text_input**: Optional text describing patient symptoms/presentation
    - **text_file**: Optional text file with patient information
    - **table_files**: Lab reports (PDF, CSV, TXT)
    - **xray_images**: X-ray images (JPG, PNG, etc.)
    """
    
    temp_files = []  # Track all temp files for cleanup
    
    try:
        # Validate input
        if not text_input and not text_file and not table_files and not xray_images:
            return JSONResponse(
                status_code=400,
                content={"error": "At least one input (text, file, or image) is required"}
            )

        # Process text file
        text_file_path = None
        if text_file:
            # Validate text file
            is_valid, error_msg = validate_file_size(text_file, 10)  # 10MB limit for text
            if not is_valid:
                return JSONResponse(status_code=400, content={"error": error_msg})
            
            is_valid, error_msg = validate_file_type(text_file, ['.txt', '.md', '.rtf'])
            if not is_valid:
                return JSONResponse(status_code=400, content={"error": error_msg})
            
            text_file_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_{text_file.filename}")
            temp_files.append(text_file_path)
            
            with open(text_file_path, "wb") as f:
                content = await text_file.read()
                f.write(content)

        # Process lab/table files
        table_paths = []
        lab_file_extensions = ['.pdf', '.csv', '.txt', '.tsv']
        
        for file in table_files:
            if not file.filename:
                continue
                
            # Validate lab file
            is_valid, error_msg = validate_file_size(file, 50)  # 50MB limit for PDFs
            if not is_valid:
                return JSONResponse(status_code=400, content={"error": error_msg})
            
            is_valid, error_msg = validate_file_type(file, lab_file_extensions)
            if not is_valid:
                return JSONResponse(status_code=400, content={"error": error_msg})
            
            path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_{file.filename}")
            temp_files.append(path)
            
            with open(path, "wb") as f:
                content = await file.read()
                f.write(content)
            table_paths.append(path)

        # Process X-ray images
        xray_paths = []
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
        
        for file in xray_images:
            if not file.filename:
                continue
                
            # Validate image file
            is_valid, error_msg = validate_file_size(file, 20)  # 20MB limit for images
            if not is_valid:
                return JSONResponse(status_code=400, content={"error": error_msg})
            
            is_valid, error_msg = validate_file_type(file, image_extensions)
            if not is_valid:
                return JSONResponse(status_code=400, content={"error": error_msg})
            
            path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_{file.filename}")
            temp_files.append(path)
            
            with open(path, "wb") as f:
                content = await file.read()
                f.write(content)
            xray_paths.append(path)

        # Log processing info
        print(f"Processing request:")
        print(f"  - Text input: {'Yes' if text_input else 'No'}")
        print(f"  - Text file: {'Yes' if text_file_path else 'No'}")
        print(f"  - Lab files: {len(table_paths)}")
        print(f"  - X-ray files: {len(xray_paths)}")

        # Run the simplified pipeline
        soap_result = run_pipeline(
            text_input=text_input,
            text_file=text_file_path,
            lab_files=table_paths,
            xray_files=xray_paths
        )

        # Add processing metadata
        soap_result["api_metadata"] = {
            "files_processed": {
                "text_files": 1 if text_file_path else 0,
                "lab_files": len(table_paths),
                "xray_files": len(xray_paths)
            },
            "processing_method": "pdfplumber_only",
            "temp_files_created": len(temp_files)
        }

        # Clean up temp files
        cleanup_temp_files(temp_files)

        return JSONResponse(content=soap_result)

    except Exception as e:
        # Clean up temp files in case of error
        cleanup_temp_files(temp_files)
        
        print(f"Error in generate_soap: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error during SOAP generation",
                "details": str(e),
                "processing_method": "pdfplumber_only"
            }
        )

@app.post("/upload-test")
async def upload_test(files: List[UploadFile] = File(...)):
    """Test endpoint for file uploads"""
    results = []
    for file in files:
        results.append({
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(await file.read()) if hasattr(file, 'read') else "unknown"
        })
        # Reset file pointer
        await file.seek(0)
    
    return {"uploaded_files": results}

@app.delete("/cleanup")
async def cleanup_temp_directory():
    """Cleanup endpoint to remove old temp files"""
    try:
        if os.path.exists(TEMP_DIR):
            # Remove files older than 1 hour
            import time
            current_time = time.time()
            cleaned_count = 0
            
            for filename in os.listdir(TEMP_DIR):
                file_path = os.path.join(TEMP_DIR, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    if file_age > 3600:  # 1 hour
                        os.remove(file_path)
                        cleaned_count += 1
            
            return {
                "message": f"Cleanup completed. Removed {cleaned_count} old files.",
                "temp_directory": TEMP_DIR
            }
        else:
            return {"message": "Temp directory does not exist"}
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Cleanup failed: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    
    print("Starting Medical SOAP Note Generator API...")
    print("Processing method: PDFPlumber only (No Mistral OCR)")
    print("Supported formats:")
    print("  - Lab files: PDF, CSV, TXT")
    print("  - Images: JPG, PNG, BMP, TIFF")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True
    )