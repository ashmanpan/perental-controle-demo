# How to Generate DESIGN.pdf

## Option 1: Using Pandoc (Recommended)

### Install Pandoc
```bash
# On Ubuntu/Debian
sudo apt-get update
sudo apt-get install pandoc texlive-xetex

# On macOS
brew install pandoc basictex
```

### Generate PDF
```bash
cd /home/kpanse/wsl-myprojects/parental-control-demo
pandoc DESIGN.md -o DESIGN.pdf --pdf-engine=xelatex -V geometry:margin=1in
```

---

## Option 2: Using Visual Studio Code

1. Install "Markdown PDF" extension
2. Open DESIGN.md in VS Code
3. Right-click in editor → "Markdown PDF: Export (pdf)"
4. PDF will be generated in same folder

---

## Option 3: Using Online Converter

1. Visit https://www.markdowntopdf.com/
2. Upload DESIGN.md
3. Click "Convert"
4. Download DESIGN.pdf

---

## Option 4: Using Browser (Print to PDF)

1. Install a markdown viewer extension in Chrome/Firefox
2. Open DESIGN.md in browser
3. Press Ctrl+P (or Cmd+P on Mac)
4. Select "Save as PDF"
5. Save as DESIGN.pdf

---

## Option 5: Using Typora (If installed)

1. Open DESIGN.md in Typora
2. File → Export → PDF
3. Save as DESIGN.pdf

---

## Quick Command (if pandoc is available)

```bash
pandoc DESIGN.md -o DESIGN.pdf --pdf-engine=xelatex \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -V documentclass=article \
  --toc \
  --highlight-style=tango
```

This will create a nicely formatted PDF with:
- Table of contents
- 1-inch margins
- Syntax highlighted code blocks
- Professional formatting
