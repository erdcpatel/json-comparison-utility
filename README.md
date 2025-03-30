# JSON Comparison Utility

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B)

A powerful tool for comparing JSON structures with a Streamlit-based web interface, supporting both file uploads and API endpoints.

## Features

- **Dual Comparison Modes**
  - File-to-File JSON comparison
  - API-to-API endpoint comparison
- **Advanced Handling**
  - Nested JSON structures
  - Arrays of objects with smart join keys
- **Interactive UI**
  - Real-time filtering of comparison results
  - Side-by-side difference visualization
  - CSV export capability


## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/json-comparison-utility.git
cd json-comparison-utility

# Install dependencies
pip install -r requirements.txt

# Run the Streamlit application
streamlit run app.py