"""
Business logic for Code Vectra search functionality
"""
import os
import re
import mimetypes
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment variables
SEARCH_ROOT = os.getenv("SEARCH_ROOT", "/Users/csp/kact/")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "1048576"))  # Default 1MB
RESULTS_PER_PAGE = int(os.getenv("RESULTS_PER_PAGE", "25"))  # Default 25 results per page
SKIP_SENSITIVE_FILES = os.getenv("SKIP_SENSITIVE_FILES", "true").lower() == "true"

def load_supported_extensions():
    """Load supported extensions from extensions.txt file"""
    try:
        with open('extensions.txt', 'r') as f:
            extensions = set()
            for line in f:
                ext = line.strip()
                if ext and not ext.startswith('#'):  # Skip empty lines and comments
                    if not ext.startswith('.'):
                        ext = '.' + ext
                    extensions.add(ext.lower())
            return extensions
    except FileNotFoundError:
        # Fallback to default extensions if file not found
        return {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss', '.sass',
            '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php', '.rb', '.go',
            '.rs', '.swift', '.kt', '.scala', '.clj', '.hs', '.ml', '.fs',
            '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
            '.sql', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini',
            '.md', '.rst', '.txt', '.log', '.conf', '.config',
            '.dockerfile', '.makefile', '.cmake', '.gradle', '.maven'
        }

SUPPORTED_EXTENSIONS = load_supported_extensions()

def should_skip_file(filename: str) -> bool:
    """Check if a file should be skipped during search"""
    # Convert to lowercase for case-insensitive matching
    filename_lower = filename.lower()
    
    # Skip environment files
    if filename_lower in {'.env', '.env.local', '.env.development', '.env.production', 
                         '.env.staging', '.env.test', '.env.example', '.env.sample'}:
        return True
    
    # Skip other sensitive/config files
    sensitive_files = {
        # Credentials and keys
        '.aws', '.ssh', 'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
        'private.key', 'private.pem', 'certificate.pem',
        
        # Database files
        '*.db', '*.sqlite', '*.sqlite3',
        
        # Log files
        '*.log', 'npm-debug.log', 'yarn-error.log',
        
        # OS files
        '.ds_store', 'thumbs.db', 'desktop.ini',
        
        # IDE files
        '.vscode', '.idea', '*.swp', '*.swo', '*~',
        
        # Package manager files
        'package-lock.json', 'yarn.lock', 'composer.lock', 'pipfile.lock',
        
        # Build artifacts
        '*.min.js', '*.min.css', '*.bundle.js', '*.chunk.js',
        
        # Other config files that might contain sensitive data
        'docker-compose.override.yml', 'docker-compose.prod.yml',
        '.htpasswd', '.htaccess', 'web.config'
    }
    
    # Check exact filename matches
    if filename_lower in sensitive_files:
        return True
    
    # Check pattern matches (for wildcards)
    import fnmatch
    for pattern in sensitive_files:
        if '*' in pattern and fnmatch.fnmatch(filename_lower, pattern):
            return True
    
    # Skip files with sensitive extensions
    sensitive_extensions = {
        '.key', '.pem', '.p12', '.pfx', '.keystore', '.jks',
        '.crt', '.cer', '.der', '.csr',
        '.password', '.passwd', '.secret'
    }
    
    file_ext = Path(filename).suffix.lower()
    if file_ext in sensitive_extensions:
        return True
    
    return False

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

def search_code(query: str, case_sensitive: bool = False, file_extensions: Optional[List[str]] = None, path_filters: Optional[List[str]] = None, max_results: int = 1000) -> Tuple[List[Dict], float, set]:
    """Search for code patterns in the specified directory"""
    start_time = time.time()
    
    if not query.strip():
        return [], 0.0, set()
    
    all_results = []
    file_count = 0
    files_searched = 0
    folders_with_results = set()
    
    print(f"Searching for: '{query}' in extensions: {file_extensions}, paths: {path_filters}")
    
    try:
        for root, dirs, files in os.walk(SEARCH_ROOT):
            # Skip common directories that shouldn't be searched
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                'node_modules', '__pycache__', 'venv', 'env', 'build', 'dist',
                'target', 'bin', 'obj', '.git', '.svn', '.hg'
            }]
            
            # Filter by path if path filters are specified
            if path_filters:
                relative_root = os.path.relpath(root, SEARCH_ROOT)
                if relative_root == '.':  # We're in the root directory
                    # Only process if we're looking for files in root or if any path filter matches current dirs
                    if not any(path_filter in dirs for path_filter in path_filters):
                        continue
                else:
                    # Check if current path matches any of the path filters
                    path_parts = relative_root.split(os.sep)
                    if not any(path_filter in path_parts for path_filter in path_filters):
                        continue
            
            for file in files:
                if file.startswith('.'):
                    continue
                
                # Skip sensitive and configuration files
                if SKIP_SENSITIVE_FILES and should_skip_file(file):
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
                
                if file_results:  # If this file has results
                    # Get the top-level folder for this file
                    path_parts = relative_path.split(os.sep)
                    if len(path_parts) > 1:  # File is in a subdirectory
                        top_folder = path_parts[0]
                        folders_with_results.add(top_folder)
                    
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
    
    return all_results[:max_results], search_time, folders_with_results

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

def parse_query_with_extensions(query: str) -> Tuple[str, Optional[List[str]], Optional[List[str]]]:
    """Parse query to extract file extensions filter and path filters"""
    import re
    
    # Extract path filters first
    path_pattern = r'path:([^\s]+)'
    path_matches = re.findall(path_pattern, query)
    path_filters = path_matches if path_matches else None
    
    # Remove path filters from query
    clean_query = re.sub(r'\s*path:[^\s]+\s*', ' ', query).strip()
    
    # Check for "+" separator syntax: "search_term + ext" or "search_term + *.ext"
    if '+' in clean_query:
        parts = clean_query.split('+', 1)  # Split on first + only
        if len(parts) == 2:
            search_part = parts[0].strip()
            ext_part = parts[1].strip()
            
            # First try to find *.ext patterns
            ext_pattern = r'\*\.([a-zA-Z0-9]+)'
            extensions = re.findall(ext_pattern, ext_part)
            
            if extensions:
                ext_list = ['.' + ext.lower() for ext in extensions]
                return search_part, ext_list, path_filters
            
            # If no *.ext pattern found, treat the whole ext_part as extension names
            # Split by spaces and commas to handle multiple extensions
            ext_names = re.split(r'[,\s]+', ext_part)
            ext_list = []
            for ext in ext_names:
                ext = ext.strip()
                if ext:  # Skip empty strings
                    if not ext.startswith('.'):
                        ext = '.' + ext
                    ext_list.append(ext.lower())
            
            if ext_list:
                return search_part, ext_list, path_filters
    
    # Fallback to original logic for backward compatibility
    # Look for patterns like "*.py", "*.js", "*.ts" etc.
    ext_pattern = r'\*\.([a-zA-Z0-9]+)'
    extensions = re.findall(ext_pattern, clean_query)
    
    if extensions:
        # Remove extension patterns from query
        final_query = re.sub(r'\s*\*\.[a-zA-Z0-9]+\s*', ' ', clean_query).strip()
        # Convert to lowercase and add dots
        ext_list = ['.' + ext.lower() for ext in extensions]
        return final_query, ext_list, path_filters
    
    return clean_query, None, path_filters

def get_direct_folders() -> List[str]:
    """Get all direct folders in the search root directory"""
    try:
        folders = []
        for item in os.listdir(SEARCH_ROOT):
            item_path = os.path.join(SEARCH_ROOT, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                folders.append(item)
        return sorted(folders)
    except Exception as e:
        print(f"Error getting directories: {e}")
        return []

def get_folders_with_results(folders_with_results: set) -> List[str]:
    """Filter direct folders to only show those with search results"""
    all_folders = get_direct_folders()
    return [folder for folder in all_folders if folder in folders_with_results]

def get_debug_info() -> Dict:
    """Get debug information about files in the search directory"""
    py_files = []
    all_files = []
    skipped_files = []
    
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
            
            if SKIP_SENSITIVE_FILES and should_skip_file(file):
                skipped_files.append(relative_path)
                continue
                
            all_files.append(relative_path)
            
            if file.endswith('.py'):
                py_files.append(relative_path)
    
    return {
        "search_root": SEARCH_ROOT,
        "total_files": len(all_files),
        "skipped_files_count": len(skipped_files),
        "py_files_count": len(py_files),
        "py_files": py_files[:20],  # Show first 20 Python files
        "all_files_sample": all_files[:20],  # Show first 20 files
        "skipped_files_sample": skipped_files[:20]  # Show first 20 skipped files
    }