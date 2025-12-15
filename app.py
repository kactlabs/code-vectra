from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import re
import mimetypes
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
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

def search_code(query: str, case_sensitive: bool = False, max_results: int = 100) -> Tuple[List[Dict], float]:
    """Search for code patterns in the specified directory"""
    start_time = time.time()
    
    if not query.strip():
        return [], 0.0
    
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
    
    end_time = time.time()
    search_time = end_time - start_time
    
    return all_results[:max_results], search_time

@app.get("/", response_class=HTMLResponse)
async def main(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "query": "", 
        "results": [], 
        "search_performed": False,
        "search_time": 0.0
    })

@app.get("/search", response_class=HTMLResponse)
async def search_get(request: Request, q: str = Query(""), case: bool = Query(False)):
    results = []
    search_time = 0.0
    search_performed = bool(q.strip())
    
    if search_performed:
        results, search_time = search_code(q, case)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "query": q,
        "results": results,
        "search_performed": search_performed,
        "case_sensitive": case,
        "result_count": len(results),
        "search_time": round(search_time, 2)
    })

@app.post("/search", response_class=HTMLResponse)
async def search_post(request: Request, query: str = Form(""), case_sensitive: bool = Form(False)):
    results = []
    search_time = 0.0
    search_performed = bool(query.strip())
    
    if search_performed:
        results, search_time = search_code(query, case_sensitive)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "query": query,
        "results": results,
        "search_performed": search_performed,
        "case_sensitive": case_sensitive,
        "result_count": len(results),
        "search_time": round(search_time, 2)
    })

@app.get("/file/{file_path:path}", response_class=HTMLResponse)
async def view_file(request: Request, file_path: str):
    """View the content of a specific file"""
    try:
        full_path = os.path.join(SEARCH_ROOT, file_path)
        
        # Security check - ensure the file is within the search root
        if not os.path.abspath(full_path).startswith(os.path.abspath(SEARCH_ROOT)):
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Access denied: File outside search directory"
            })
        
        if not os.path.exists(full_path):
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"File not found: {file_path}"
            })
        
        if not is_text_file(full_path):
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"Cannot display binary file: {file_path}"
            })
        
        if os.path.getsize(full_path) > MAX_FILE_SIZE:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"File too large to display: {file_path}"
            })
        
        # Read file content
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Split into lines for display
        lines = content.split('\n')
        
        # Detect file language for syntax highlighting
        file_ext = Path(file_path).suffix.lower()
        language_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.jsx': 'javascript', '.tsx': 'typescript', '.html': 'html',
            '.css': 'css', '.scss': 'scss', '.sass': 'sass',
            '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.h': 'c',
            '.cs': 'csharp', '.php': 'php', '.rb': 'ruby',
            '.go': 'go', '.rs': 'rust', '.swift': 'swift',
            '.kt': 'kotlin', '.scala': 'scala', '.sh': 'bash',
            '.sql': 'sql', '.json': 'json', '.xml': 'xml',
            '.yaml': 'yaml', '.yml': 'yaml', '.md': 'markdown'
        }
        
        language = language_map.get(file_ext, 'text')
        
        return templates.TemplateResponse("file_view.html", {
            "request": request,
            "file_path": file_path,
            "content": content,
            "lines": lines,
            "language": language,
            "line_count": len(lines)
        })
        
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Error reading file: {str(e)}"
        })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
