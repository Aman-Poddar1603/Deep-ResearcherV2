# MCP Tools Documentation

This document outlines the available tools in the Deep Researcher v2 MCP Tools Server. Each tool is exposed via the MCP (Model Context Protocol) and returns responses as JSON strings for easy parsing by clients.

## 1. web_search

**Description**: Searches the web for a given query, collects relevant URLs using SearXNG, and scrapes the pages using crawl4ai.

**Input**:
- `query` (str): The search query string.

**Input Example**:
```json
{
  "query": "latest AI news"
}
```

**Output**: A JSON string containing a dictionary with:
- `"results"`: A list of dictionaries, each representing a scraped page with keys like `success`, `url`, `content`, `scrape_duration`, `datetime_Scrape`, and metadata.

**Output Example**:
```json
{
  "results": [
    {
      "success": true,
      "url": "https://example.com/ai-news",
      "content": "Full scraped content here...",
      "scrape_duration": 1.5,
      "datetime_Scrape": "2023-10-01T12:00:00.000Z",
      "metadata": {
        "title": "Latest AI News",
        "description": "Breaking news on AI developments",
        "favicon": "https://example.com/favicon.ico",
        "banner_image": "https://example.com/banner.jpg",
        "status": "success",
        "crawling_time_sec": 1.5,
        "scraped_at": "2023-10-01T12:00:00.000Z"
      }
    }
  ]
}
```

**Behavior**: Performs a full pipeline of searching for URLs and then scraping them in parallel batches. Handles failures gracefully and returns all collected data at once.

## 2. read_webpages

**Description**: Scrapes a list of provided URLs directly without searching.

**Input**:
- `urls` (list[str]): A list of URL strings to scrape.

**Input Example**:
```json
{
  "urls": ["https://example.com/page1", "https://example.com/page2"]
}
```

**Output**: A JSON string containing a dictionary with:
- `"results"`: A list of dictionaries, each with page details including `success`, `url`, `content`, `scrape_duration`, and metadata.

**Output Example**:
```json
{
  "results": [
    {
      "success": true,
      "url": "https://example.com/page1",
      "content": "Scraped content of page1...",
      "scrape_duration": 1.2,
      "datetime_Scrape": "2023-10-01T12:00:00.000Z",
      "metadata": {
        "title": "Page 1 Title",
        "description": "Description of page1",
        "favicon": "https://example.com/favicon.ico",
        "banner_image": "https://example.com/banner.jpg",
        "status": "success",
        "crawling_time_sec": 1.2,
        "scraped_at": "2023-10-01T12:00:00.000Z"
      }
    }
  ]
}
```

**Behavior**: Directly scrapes the given URLs using crawl4ai in parallel. No searching involved; assumes URLs are provided.

## 3. youtube_search

**Description**: Searches YouTube for videos matching the query using yt-dlp.

**Input**:
- `query` (str): The search query for YouTube videos.

**Input Example**:
```json
{
  "query": "black hole mystery"
}
```

**Output**: A JSON string containing a dictionary with:
- `query`: The original query.
- `total_results`: Number of videos found.
- `scrape_time`: Time taken for the search.
- `videos`: A list of video dictionaries, each with `title`, `url`, `description`, `channel`, `duration`, `views`, `upload_date`, `thumbnail`.

**Output Example**:
```json
{
  "query": "black hole mystery",
  "total_results": 10,
  "scrape_time": 5.2,
  "videos": [
    {
      "title": "The Mystery of Black Holes",
      "url": "https://www.youtube.com/watch?v=example",
      "description": "Exploring black holes...",
      "channel": "Science Channel",
      "duration": 600,
      "views": 1000000,
      "upload_date": "20231001",
      "thumbnail": "https://img.youtube.com/vi/example/0.jpg"
    }
  ]
}
```

**Behavior**: Uses yt-dlp to search and extract video metadata. Processes up to 10 results by default and extracts detailed info for each.

## 4. image_search_tool

**Description**: Searches for images related to multiple queries using SearXNG.

**Input**:
- `queries` (list[tuple[str, int]]): A list of tuples, where each tuple is `(query, num_images)` specifying the search term and the number of images to fetch.

**Input Example**:
```json
{
  "queries": [["cats", 5], ["bali", 10]]
}
```

**Output**: A JSON string containing a dictionary mapping each query to a list of image URLs.

**Output Example**:
```json
{
  "cats": [
    "https://example.com/cat1.jpg",
    "https://example.com/cat2.jpg"
  ],
  "bali": [
    "https://example.com/bali1.jpg",
    "https://example.com/bali2.jpg"
  ]
}
```

**Behavior**: Performs parallel searches for each query using SearXNG. Fetches up to the specified number of images per query and returns them grouped by query.

## 5. understand_images_tool

**Description**: Analyzes a list of images (URLs or local paths) using Ollama AI model. Downloads and processes images, then generates titles and descriptions.

**Input**:
- `paths` (list[str]): A list of image URLs or local file paths.

**Input Example**:
```json
{
  "paths": ["https://example.com/image1.jpg", "/local/path/image2.png"]
}
```

**Output**: A JSON string containing a dictionary with:
- `total_files`: Total number of images processed.
- `succeed`: Number of successful analyses.
- `total_tokens_used`: Tokens consumed.
- `total_time_taken`: Time taken.
- `content`: A dictionary mapping filenames to analysis results, each with `title`, `desc`, `tokens`, `time`, `stored_at`.

**Output Example**:
```json
{
  "total_files": 2,
  "succeed": 2,
  "total_tokens_used": 150,
  "total_time_taken": 3.5,
  "content": {
    "1st_image_jpg_image_title.jpg": {
      "title": "Beautiful Sunset",
      "desc": "A vibrant sunset over the ocean.",
      "tokens": 75,
      "time": 1.8,
      "stored_at": "/temp/processed_image.jpg"
    }
  }
}
```

**Behavior**: Downloads images if URLs, resizes them, and uses Ollama to generate concise titles and descriptions. Handles multiple images in parallel.

## 6. process_docs

**Description**: Processes a list of document files (PDF, DOCX, PPTX, XLSX, TXT, MD) or URLs. Extracts text, cleans it, and summarizes using Ollama AI.

**Input**:
- `paths` (list[str]): A list of file paths or URLs to documents.

**Input Example**:
```json
{
  "paths": ["https://example.com/doc.pdf", "/local/path/doc.docx"]
}
```

**Output**: A JSON string containing a dictionary with:
- `total_files`: Total number of files.
- `succeed`: Number of successful processes.
- `total_tokens_used`: Tokens used.
- `total_time_taken`: Time taken.
- `content`: A dictionary mapping filenames to summaries.

**Output Example**:
```json
{
  "total_files": 2,
  "succeed": 2,
  "total_tokens_used": 200,
  "total_time_taken": 4.2,
  "content": {
    "1st_file_pdf_summary.pdf": "This document discusses AI advancements...",
    "2nd_file_docx_summary.docx": "An overview of machine learning techniques."
  }
}
```

**Behavior**: Downloads files if URLs, extracts text from various formats, cleans it, and summarizes using Ollama. Processes in parallel.

## 7. search_urls_tool

**Description**: Searches for URLs related to the query using SearXNG without scraping the pages.

**Input**:
- `query` (str): The search query.

**Input Example**:
```json
{
  "query": "latest AI news"
}
```

**Output**: A JSON string containing a list of unique URLs.

**Output Example**:
```json
[
  "https://example.com/ai-news1",
  "https://example.com/ai-news2",
  "https://example.com/ai-news3"
]
```

**Behavior**: Uses SearXNG to fetch search results and extracts URLs. Returns only the URLs, no content scraping.

## 8. scrape_single_url

**Description**: Scrapes a single URL and returns its details.

**Input**:
- `url` (str): The URL to scrape.

**Input Example**:
```json
{
  "url": "https://example.com/page"
}
```

**Output**: A JSON string containing a dictionary with:
- `"results"`: A list containing a single dictionary with `success`, `url`, `content`, `scrape_duration`, and metadata.

**Output Example**:
```json
{
  "results": [
    {
      "success": true,
      "url": "https://example.com/page",
      "content": "Scraped content here...",
      "scrape_duration": 1.0,
      "datetime_Scrape": "2023-10-01T12:00:00.000Z",
      "metadata": {
        "title": "Page Title",
        "description": "Page description",
        "favicon": "https://example.com/favicon.ico",
        "banner_image": "https://example.com/banner.jpg",
        "status": "success",
        "crawling_time_sec": 1.0,
        "scraped_at": "2023-10-01T12:00:00.000Z"
      }
    }
  ]
}
```

**Behavior**: Scrapes the provided URL using crawl4ai and returns the details in a structured format. Useful for single-page analysis.
