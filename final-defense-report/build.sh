#!/bin/bash
# Build the LaTeX defense report
# Requires: pdflatex, biber, makeglossaries
# Install on Ubuntu: sudo apt install texlive-full biber

set -e

echo "Building defense report..."

# First pass
pdflatex -interaction=nonstopmode -shell-escape main.tex

# Bibliography
biber main

# Glossary
makeglossaries main

# Second pass (resolve references)
pdflatex -interaction=nonstopmode -shell-escape main.tex

# Third pass (final)
pdflatex -interaction=nonstopmode -shell-escape main.tex

echo ""
echo "Build complete: main.pdf"
echo "Page count: $(pdfinfo main.pdf 2>/dev/null | grep Pages | awk '{print $2}' || echo 'unknown')"
