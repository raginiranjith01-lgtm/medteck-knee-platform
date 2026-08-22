# MedTech Knee Analysis Platform

AI-assisted platform for **medial meniscus thickness assessment**, **osteoarthritis analysis**, and **patient-specific knee implant sizing** — based on the problem statement in `medtech_ps.pdf`.

## Features

### Module 1 — Medial Meniscus & OA Assessment
- Detects femur, tibia, and medial meniscus regions
- Measures meniscus thickness at anterior, mid-body, and posterior horn
- Compares against sex-specific reference values
- Provides OA likelihood assessment (decision-support only)

### Module 2 — Implant Sizing (TKA)
- Extracts femoral and tibial width/AP dimensions
- Matches against structured implant sizing database
- Returns ranked femoral and tibial size recommendations

### Research Analytics
- Stores analyzed cases
- Compares meniscus thickness by sex and OA status

## Quick Start

```bash
cd develop/medtech-knee-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5001**

## Usage

1. Upload a knee image (MRI/X-ray coronal view — PNG, JPG, BMP, TIFF)
2. Enter patient demographics (age, sex, OA status)
3. Click **Run AI Analysis**
4. Review visualization, meniscus measurements, and implant recommendations
5. Use **Research** tab for population comparisons

## Important Notes

- This is a **clinical decision-support prototype**, not a diagnostic device
- Image analysis uses computer vision heuristics; production systems require trained ML segmentation models (U-Net, nnU-Net, etc.) validated on clinical data
- Implant database contains generic TKA dimensions for demonstration
- Final diagnosis and treatment decisions remain with qualified medical professionals

## Project Structure

```
medtech-knee-platform/
├── app.py                    # Flask web server
├── data/
│   ├── implant_database.json # Implant specs & reference values
│   └── cases.json            # Stored analysis cases
├── lib/
│   ├── image_processor.py    # Image loading & ROI detection
│   ├── meniscus_analyzer.py  # Module 1
│   ├── implant_sizer.py      # Module 2
│   ├── visualizer.py         # Overlay rendering
│   └── case_store.py         # Research analytics
├── templates/index.html
└── static/
```
