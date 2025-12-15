# Code Vectra - Local Code Search Engine

A fast, web-based code search engine similar to grep.app that searches through your local codebase.

## Features

- 🔍 **Fast regex-based search** across all code files
- 🎨 **Clean, modern UI** with dark/light theme support
- 📁 **Smart file filtering** - automatically detects and searches text files
- 🔤 **Case-sensitive search** option
- 📱 **Responsive design** works on desktop and mobile
- ⚡ **Real-time search** with context highlighting
- 📋 **Click to copy** code lines
- 📄 **File viewer** - click on file paths to view complete file content
- 🎨 **Syntax highlighting** for popular programming languages
- ⬇️ **Download files** directly from the viewer

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Update the search path in `app.py`:
```python
SEARCH_ROOT = "/path/to/your/code/directory"
```

3. Run the application:
```bash
python app.py
```

4. Open your browser to `http://localhost:8001`

## Usage

- Enter search patterns using regex syntax
- Use the case-sensitive checkbox for exact matches
- Click on any code line to copy it to clipboard
- Use `Ctrl/Cmd + K` to quickly focus the search input
- **Click on file paths** in search results to view the complete file
- In file viewer:
  - Click line numbers to copy individual lines
  - Use "Copy All" to copy the entire file
  - Use "Download" to save the file locally
  - Press `Escape` to go back to search results

## Supported File Types

The search engine automatically detects and searches common code file types including:
- Python (.py)
- JavaScript/TypeScript (.js, .ts, .jsx, .tsx)
- HTML/CSS (.html, .css, .scss)
- Java (.java)
- C/C++ (.c, .cpp, .h, .hpp)
- And many more...

## Configuration

You can customize the search behavior by modifying these variables in `app.py`:

- `SEARCH_ROOT`: Directory to search in
- `MAX_FILE_SIZE`: Maximum file size to search (default: 1MB)
- `SUPPORTED_EXTENSIONS`: File extensions to include in search


### Screenshots
![1765808266623](image/README/1765808266623.png)

![1765808283556](image/README/1765808283556.png)
