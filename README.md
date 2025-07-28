

---

````markdown
# 📘 PDF Outline Extractor

A Python-based utility that **extracts structured outlines (like headings and subheadings)** from any PDF, even if it lacks a built-in table of contents. It uses **font size analysis**, **regex patterns**, and **heuristic logic** to determine heading levels (H1, H2, H3), filter out headers/footers, and output a clean JSON representation.

---

## ✨ Features

- ✅ Automatically detects headings and subheadings (H1, H2, H3)
- ✅ Ignores repeated headers/footers
- ✅ Supports multiple heading styles (numbered, Roman, all caps, etc.)
- ✅ Extracts the document title based on font size
- ✅ Saves results as a structured JSON file
- ✅ Logs progress and potential issues

---

## 📂 Output Format

```json
{
  "title": "Document Title",
  "outline": [
    {
      "level": "H1",
      "text": "Introduction",
      "page": 1
    },
    {
      "level": "H2",
      "text": "Background and Motivation",
      "page": 2
    },
    ...
  ]
}
````

---

## 🚀 Getting Started

### 1. **Install Dependencies**

```bash
pip install pymupdf
```

> `pymupdf` is required for extracting text, fonts, and layout from PDFs.

---

### 2. **Place PDF Files**

Copy or move your PDF files into the **same directory** as the script.

---

### 3. **Run the Script**

```bash
python your_script_name.py
```

You will be prompted to select a PDF file:

```bash
📄 Available PDF files:
   1. sample.pdf
   2. report.pdf

Enter the number of the PDF to process:
```

After processing, the JSON file will be saved in an `output_json/` folder.

---

## 🧠 How It Works

* **Title Detection**: Finds the largest text on the first or second page.
* **Header/Footer Filtering**: Removes repeating content near top/bottom of pages.
* **Heading Classification**:

  * Font size hierarchy (largest = H1)
  * Numbered patterns (e.g., 1.1.1 = H3)
  * Regex-matched styles (e.g., "Chapter 1", ALL CAPS)
  * Explicit keywords (e.g., "Introduction", "References")

---

## 🛠 Project Structure

```
.
├── your_script_name.py      # Main extractor logic
├── sample.pdf               # Your input PDF
└── output_json/
    └── sample.json          # Output outline (auto-generated)
```

---

## 🧪 Tested On

* Research papers
* Academic reports
* Technical documentation
* Books without ToC

---

## 📌 Requirements

* Python 3.6+
* [PyMuPDF (`fitz`)](https://pymupdf.readthedocs.io/en/latest/)

---

## 🙌 Contributing

Found a bug or want to improve heading detection? PRs and suggestions are welcome!

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🧑‍💻 Author

**Prashant Singh**
[GitHub](https://github.com/Parshuram02)

---

```

---

Let me know if you want this README in PDF, DOCX, or with screenshots included.
```
