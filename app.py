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
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configuration from environment variables
SEARCH_ROOT = os.getenv("SEARCH_ROOT", "/Users/csp/kact/")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "1048576"))  # Default 1MB
RESULTS_PER_PAGE = int(os.getenv("RESULTS_PER_PAGE", "25"))  # Default 25 results per page
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
        
        # Try to compile the regex pattern, if it fails, escape it and treat as literal
        try:
            regex = re.compile(pattern, flags)
        except re.error:
            # If regex compilation fails, escape the pattern and treat as literal search
            escaped_pattern = re.escape(pattern)
            regex = re.compile(escaped_pattern, flags)
        
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

def search_code(query: str, case_sensitive: bool = False, file_extensions: Optional[List[str]] = None, max_results: int = 1000) -> Tuple[List[Dict], float]:
    """Search for code patterns in the specified directory"""
    start_time = time.time()
    
    if not query.strip():
        return [], 0.0
    
    all_results = []
    file_count = 0
    files_searched = 0
    
    print(f"Searching for: '{query}' in extensions: {file_extensions}")
    
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
                
                # Filter by file extensions if specified
                if file_extensions:
                    file_ext = Path(file).suffix.lower()
                    if file_ext not in file_extensions:
                        continue
                    
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, SEARCH_ROOT)
                
                files_searched += 1
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
    
    print(f"Searched {files_searched} files, found {len(all_results)} results")
    
    return all_results[:max_results], search_time

def paginate_results(results: List[Dict], page: int, per_page: int = None) -> Tuple[List[Dict], Dict]:
    """Paginate search results"""
    if per_page is None:
        per_page = RESULTS_PER_PAGE
    
    total_results = len(results)
    total_pages = (total_results + per_page - 1) // per_page  # Ceiling division
    
    # Ensure page is within valid range
    page = max(1, min(page, total_pages if total_pages > 0 else 1))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated_results = results[start_idx:end_idx]
    
    pagination_info = {
        'current_page': page,
        'total_pages': total_pages,
        'total_results': total_results,
        'per_page': per_page,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
        'start_result': start_idx + 1 if total_results > 0 else 0,
        'end_result': min(end_idx, total_results)
    }
    
    return paginated_results, pagination_info

def parse_query_with_extensions(query: str) -> Tuple[str, Optional[List[str]]]:
    """Parse query to extract file extensions filter"""
    import re
    
    # Check for "+" separator syntax: "search_term + *.ext"
    if '+' in query:
        parts = query.split('+', 1)  # Split on first + only
        if len(parts) == 2:
            search_part = parts[0].strip()
            ext_part = parts[1].strip()
            
            # Find extension patterns in the second part
            ext_pattern = r'\*\.([a-zA-Z0-9]+)'
            extensions = re.findall(ext_pattern, ext_part)
            
            if extensions:
                ext_list = ['.' + ext.lower() for ext in extensions]
                return search_part, ext_list
    
    # Fallback to original logic for backward compatibility
    # Look for patterns like "*.py", "*.js", "*.ts" etc.
    ext_pattern = r'\*\.([a-zA-Z0-9]+)'
    extensions = re.findall(ext_pattern, query)
    
    if extensions:
        # Remove extension patterns from query
        clean_query = re.sub(r'\s*\*\.[a-zA-Z0-9]+\s*', ' ', query).strip()
        # Convert to lowercase and add dots
        ext_list = ['.' + ext.lower() for ext in extensions]
        return clean_query, ext_list
    
    return query, None

@app.get("/", response_class=HTMLResponse)
async def main(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "query": "", 
        "clean_query": "",
        "file_extensions": None,
        "results": [], 
        "search_performed": False,
        "search_time": 0.0,
        "total_results": 0,
        "pagination": {},
        "search_root": SEARCH_ROOT
    })

@app.get("/search", response_class=HTMLResponse)
async def search_get(request: Request, q: str = Query(""), case: bool = Query(False), page: int = Query(1)):
    results = []
    search_time = 0.0
    search_performed = bool(q.strip())
    clean_query = q
    file_extensions = None
    pagination_info = {}
    
    if search_performed:
        clean_query, file_extensions = parse_query_with_extensions(q)
        all_results, search_time = search_code(clean_query, case, file_extensions)
        results, pagination_info = paginate_results(all_results, page)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "query": q,
        "clean_query": clean_query,
        "file_extensions": file_extensions,
        "results": results,
        "search_performed": search_performed,
        "case_sensitive": case,
        "result_count": len(results),
        "total_results": pagination_info.get('total_results', 0),
        "pagination": pagination_info,
        "search_time": round(search_time, 2),
        "search_root": SEARCH_ROOT
    })

@app.post("/search", response_class=HTMLResponse)
async def search_post(request: Request, query: str = Form(""), case_sensitive: bool = Form(False)):
    results = []
    search_time = 0.0
    search_performed = bool(query.strip())
    clean_query = query
    file_extensions = None
    pagination_info = {}
    
    if search_performed:
        clean_query, file_extensions = parse_query_with_extensions(query)
        all_results, search_time = search_code(clean_query, case_sensitive, file_extensions)
        results, pagination_info = paginate_results(all_results, 1)  # Always start at page 1 for POST
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "query": query,
        "clean_query": clean_query,
        "file_extensions": file_extensions,
        "results": results,
        "search_performed": search_performed,
        "case_sensitive": case_sensitive,
        "result_count": len(results),
        "total_results": pagination_info.get('total_results', 0),
        "pagination": pagination_info,
        "search_time": round(search_time, 2),
        "search_root": SEARCH_ROOT
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

@app.get("/debug/files")
async def debug_files():
    """Debug endpoint to see what files are found"""
    py_files = []
    all_files = []
    
    for root, dirs, files in os.walk(SEARCH_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
            'node_modules', '__pycache__', 'venv', 'env', 'build', 'dist',
            'target', 'bin', 'obj', '.git', '.svn', '.hg'
        }]
        
        for file in files:
            if file.startswith('.'):
                continue
                
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, SEARCH_ROOT)
            all_files.append(relative_path)
            
            if file.endswith('.py'):
                py_files.append(relative_path)
    
    return {
        "search_root": SEARCH_ROOT,
        "total_files": len(all_files),
        "py_files_count": len(py_files),
        "py_files": py_files[:20],  # Show first 20 Python files
        "all_files_sample": all_files[:20]  # Show first 20 files
    }

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host=host, port=port)
