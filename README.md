# How to Use the PDF Catalog Generator

This is a Streamlit-based web tool that generates a branded PDF product catalog from any JSON API that returns a list of products. It supports grouping by categories/departments, HTML descriptions (including bullet lists), product images, custom brand colors, and optional additional columns.

The tool is fully configurable through a simple web form — no code changes needed.

## Features

- Fetches product data from any public JSON API
- Groups products by a configurable key (e.g., "category" for departments)
- Supports HTML descriptions with bullet points
- Downloads and embeds product images directly in the PDF
- Customizable title, subtitle, brand colors, column headers, and filename
- Optional extra columns (e.g., price, code, stock)
- Generates a clean, professional PDF with tables, headers, and footer
- Download the PDF directly from the browser

## Requirements

- Python 3.8 or higher
- Virtual environment (recommended)

## Installation

1. Clone or download the repository:
   ```bash
   git clone https://github.com/yourusername/PDG-EXTRACTION-TOOL-FROM-API.git
   cd PDG-EXTRACTION-TOOL-FROM-API