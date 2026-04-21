# DAS_NIDF - Distributed Acoustic Sensing Data Visualization

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)  
[![PyPI Version](https://img.shields.io/pypi/v/das-nidf.svg)](https://pypi.org/project/das-nidf/)  
[![Downloads](https://img.shields.io/pypi/dm/das-nidf.svg)](https://pypi.org/project/das-nidf/)  

---

## Overview

**DAS_NIDF** is a comprehensive Python library for visualizing and analyzing **Distributed Acoustic Sensing (DAS)** data. It provides interactive, high-performance visualization tools using **Holoviews + Datashader**, capable of handling billions of data points.

Developed exclusively for internal use by the **Núcleo Interdisciplinar de Dinâmica dos Fluidos (NIDF)**.

> **Restricted Use Notice:** This package was created specifically for research and technical activities within NIDF and is not intended for public or commercial use.

---

## Features

- **Interactive Waterfall Plots** - Real-time zoom, pan, and hover  
- **Spectrogram Analysis** - Integrated band power maps  
- **Frequency-Wavenumber (f-k) Analysis** - 2D FFT for wavefield analysis  
- **ROI Analysis** - Region of Interest extraction and visualization  
- **Customizable Colormaps** - Viridis, Plasma, and more  
- **High Performance** - Datashader rendering for large datasets  
- **Interactive Dashboard** - All plots combined in a single HTML page  
- **Complete Processing Pipeline** - From HDF5 to visualization  

---

## Installation

### From PyPI (authorized internal users only)

```bash
pip install das-nidf
```

---

## Dependencies

Automatically installed with the package:

- numpy >= 1.20.0  
- scipy >= 1.7.0  
- h5py >= 3.0.0  
- holoviews >= 1.15.0  
- datashader >= 0.14.0  
- bokeh >= 2.4.0  
- scikit-image >= 0.19.0  

---

## 🚀 Quick Start

```python
from DAS_NIDF import run_server
run_server()
```

---

## 📖 Detailed Usage

### 1. Complete Processing Pipeline

The `process_full_pipeline()` method handles:

- Reads HDF5 file  
- Extracts metadata (`fs`, `dx`, `num_locs`)  
- Applies temporal cutting  
- Removes DC mean  
- Applies bandpass filter  

---

## 🔒 License / Usage Policy

This software is intended solely for internal academic and technical use within **NIDF**. Redistribution, resale, external deployment, or unauthorized modification may be restricted.

For access requests or collaboration inquiries, please contact the maintainers.

---

## 🌟 Acknowledgments

- HoloViz team for Holoviews and Datashader  
- Bokeh team for interactive visualization  
- NIDF and LPS - UFRJ for research support  