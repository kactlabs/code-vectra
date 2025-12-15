from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import uvicorn
from pathlib import Path

# Import business logic
from business import (
    search_code, 
    paginate_results, 
    parse_query_with_extensions,
    is_text_file,
    get_debug_info,
    SEARCH_ROOT,
    MAX_FILE_SIZE
)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
    return get_debug_info()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host=host, port=port)
