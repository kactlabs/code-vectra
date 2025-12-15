from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import re
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configuration
SEARCH_ROOT = "/Users/csp/kact/"
MAX_FILE_SIZE = 1024 * 1024  # 1MB
SUPPORTED_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss', '.sass',
    '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php', '.rb', '.go',
    '.rs', '.swift', '.kt', '.scala', '.clj', '.hs', '.ml', '.fs',
    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
    '.sql', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini',
    '.md', '.rst', '.txt', '.log', '.conf', '.config',
    '.dockerfile', '.makefile', '.cmake', '.gradle', '.maven'
}

def is_text_file(file_path: str) -> bool:
    """Check if a file is likely to be a text file"""
    try:
        # Check by extension first
        ext = Path(file_path).suffix.lower()
        if ext in SUPPORTED_EXTENSIONS:
            return True
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith('text/'):
            return True
            
        # Try to read a small portion to detect binary files
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:  # Binary files often contain null bytes
                return False
        return True
    except:
        return False

def search_in_file(file_path: str, pattern: str, case_sensitive: bool = False) -> List[Dict]:
    """Search for pattern in a single file"""
    results = []
    try:
        if not is_text_file(file_path) or os.path.getsize(file_path) > MAX_FILE_SIZE:
            return results
            
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            matches = list(regex.finditer(line.rstrip('\n\r')))
            if matches:
                # Get context lines
                start_line = max(0, line_num - 3)
                end_line = min(len(lines), line_num + 2)
                context_lines = []
                
                for i in range(start_line, end_line):
                    context_lines.append({
                        'line_number': i + 1,
                        'content': lines[i].rstrip('\n\r'),
                        'is_match': i + 1 == line_num
                    })
                
                results.append({
                    'file_path': file_path,
                    'line_number': line_num,
                    'line_content': line.rstrip('\n\r'),
                    'matches': [(m.start(), m.end()) for m in matches],
                    'context': context_lines
                })
    except Exception as e:
        print(f"Error searching in {file_path}: {e}")
    
    return results

def search_code(query: str, case_sensitive: bool = False, max_results: int = 100) -> List[Dict]:
    """Search for code patterns in the specified directory"""
    if not query.strip():
        return []
    
    all_results = []
    file_count = 0
    
    try:
        for root, dirs, files in os.walk(SEARCH_ROOT):
            # Skip common directories that shouldn't be searched
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                'node_modules', '__pycache__', 'venv', 'env', 'build', 'dist',
                'target', 'bin', 'obj', '.git', '.svn', '.hg'
            }]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, SEARCH_ROOT)
                
                file_results = search_in_file(file_path, query, case_sensitive)
                for result in file_results:
                    result['relative_path'] = relative_path
                    all_results.append(result)
                    
                file_count += 1
                if len(all_results) >= max_results:
                    break
                    
            if len(all_results) >= max_results:
                break
                
    except Exception as e:
        print(f"Error during search: {e}")
    
    return all_results[:max_results]

@app.get("/", response_class=HTMLResponse)
async def main(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "query": "", 
        "results": [], 
        "search_performed": False
    })

@app.get("/search", response_class=HTMLResponse)
async def search_get(request: Request, q: str = Query(""), case: bool = Query(False)):
    results = []
    search_performed = bool(q.strip())
    
    if search_performed:
        results = search_code(q, case)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "query": q,
        "results": results,
        "search_performed": search_performed,
        "case_sensitive": case,
        "result_count": len(results)
    })

@app.post("/search", response_class=HTMLResponse)
async def search_post(request: Request, query: str = Form(""), case_sensitive: bool = Form(False)):
    results = []
    search_performed = bool(query.strip())
    
    if search_performed:
        results = search_code(query, case_sensitive)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "query": query,
        "results": results,
        "search_performed": search_performed,
        "case_sensitive": case_sensitive,
        "result_count": len(results)
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
