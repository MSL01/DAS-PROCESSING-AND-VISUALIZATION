"""
Web Application for DAS_NIDF
Interactive interface to upload HDF5 files and generate visualizations
"""

import os
import base64
import webbrowser
import glob
import json
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import numpy as np
import tempfile
import shutil
import threading

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.config['OUTPUT_FOLDER'] = tempfile.mkdtemp()

# Store processing status
processing_status = {
    'progress': 0,
    'message': '',
    'output_dir': None,
    'filepath': None
}


def list_available_analyses():
    """Lista todas las carpetas DAS_SIGNALS_* en el directorio actual"""
    analyses = []
    for folder in glob.glob('DAS_SIGNALS_*'):
        if os.path.isdir(folder):
            files = {
                'main': 'main.html' if os.path.exists(os.path.join(folder, 'main.html')) else None,
                'dashboard': 'dashboard.html' if os.path.exists(os.path.join(folder, 'dashboard.html')) else None,
                'figure1': '01_time_signals_fft.html' if os.path.exists(os.path.join(folder, '01_time_signals_fft.html')) else None,
                'figure2': '02_temporal_psd_map.html' if os.path.exists(os.path.join(folder, '02_temporal_psd_map.html')) else None,
                'figure3': '03_roi_phase_map.html' if os.path.exists(os.path.join(folder, '03_roi_phase_map.html')) else None,
                'figure4': '04_roi_psd_map.html' if os.path.exists(os.path.join(folder, '04_roi_psd_map.html')) else None,
                'figure5': '05_2dfft_kf_analysis.html' if os.path.exists(os.path.join(folder, '05_2dfft_kf_analysis.html')) else None,
            }
            metadata_file = os.path.join(folder, 'metadata.json')
            metadata = {}
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                except:
                    pass

            analyses.append({
                'name': folder,
                'path': folder,
                'files': files,
                'metadata': metadata,
                'created': os.path.getctime(folder)
            })

    analyses.sort(key=lambda x: x['created'], reverse=True)
    return analyses


# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DAS_NIDF - Web Interface</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }

        .nav {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            padding: 15px 30px;
            display: flex;
            gap: 30px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        .nav-btn {
            background: transparent;
            border: none;
            color: rgba(255,255,255,0.7);
            padding: 10px 20px;
            font-size: 1rem;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.3s ease;
        }

        .nav-btn.active {
            background: rgba(0, 210, 255, 0.2);
            color: #00d2ff;
            border-bottom: 2px solid #00d2ff;
        }

        .nav-btn:hover {
            background: rgba(255,255,255,0.1);
            color: white;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px;
        }

        .panel {
            display: none;
            animation: fadeIn 0.5s ease;
        }

        .panel.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .card h2 {
            margin-bottom: 20px;
            color: #00d2ff;
            font-weight: 500;
        }

        .card h3 {
            margin-bottom: 15px;
            color: rgba(255,255,255,0.8);
            font-weight: 400;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            color: rgba(255,255,255,0.7);
            font-size: 0.9rem;
        }

        input, select {
            width: 100%;
            padding: 12px 15px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            color: white;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }

        input:focus, select:focus {
            outline: none;
            border-color: #00d2ff;
            background: rgba(255,255,255,0.15);
        }

        input[type="file"] {
            padding: 10px;
            cursor: pointer;
        }

        input[type="file"]::file-selector-button {
            background: rgba(0, 210, 255, 0.2);
            border: 1px solid #00d2ff;
            border-radius: 8px;
            padding: 8px 16px;
            color: #00d2ff;
            cursor: pointer;
            margin-right: 15px;
        }

        .row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }

        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }

        .btn-primary {
            background: linear-gradient(135deg, #00d2ff, #3a7bd5);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0, 210, 255, 0.3);
        }

        .btn-success {
            background: linear-gradient(135deg, #00b09b, #96c93d);
            color: white;
        }

        .btn-success:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0, 176, 155, 0.3);
        }

        .progress-container {
            margin-top: 20px;
            display: none;
        }

        .progress-bar {
            width: 100%;
            height: 30px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d2ff, #3a7bd5);
            width: 0%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
        }

        .progress-message {
            margin-top: 10px;
            text-align: center;
            color: rgba(255,255,255,0.7);
        }

        .file-info {
            background: rgba(0, 210, 255, 0.1);
            border-radius: 10px;
            padding: 15px;
            margin-top: 15px;
            border-left: 3px solid #00d2ff;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .file-info:hover {
            background: rgba(0, 210, 255, 0.2);
            transform: translateX(5px);
        }

        .result-links {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-top: 20px;
        }

        .result-link {
            background: rgba(255,255,255,0.1);
            padding: 10px 20px;
            border-radius: 10px;
            text-decoration: none;
            color: #00d2ff;
            transition: all 0.3s ease;
        }

        .result-link:hover {
            background: rgba(0, 210, 255, 0.2);
            transform: translateY(-2px);
        }

        .alert-info {
            background: rgba(0, 210, 255, 0.1);
            border-left: 3px solid #00d2ff;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }

        .analyses-list {
            max-height: 500px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="nav">
    <button class="nav-btn active" onclick="showPanel('main', event)">📁 Main</button>
    <button class="nav-btn" onclick="showPanel('parameters', event)">⚙️ Parameters</button>
    <button class="nav-btn" onclick="showPanel('load', event)">📂 Load Analysis</button>
    <button class="nav-btn" onclick="showPanel('results', event)">📊 Results</button>
</div>

    <div class="container">
        <!-- Main Panel -->
        <div id="main-panel" class="panel active">
            <div class="card">
                <h2>📁 File Upload</h2>
                <div class="form-group">
                    <label>Select HDF5 File (.h5)</label>
                    <input type="file" id="h5file" accept=".h5">
                </div>
                <div id="file-info" class="file-info" style="display:none;"></div>
                <button class="btn btn-primary" onclick="uploadFile()" id="upload-btn">📤 Upload File</button>
            </div>

            <div class="card">
                <h2>📊 Quick Actions</h2>
                <p style="margin-bottom: 15px; color: rgba(255,255,255,0.6);">Configure parameters in the Parameters panel, then click Generate to create visualizations.</p>
                <button class="btn btn-success" onclick="generateAnalysis()" id="generate-btn" disabled>Generate Analysis</button>
            </div>

            <div id="progress-container" class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill">0%</div>
                </div>
                <div class="progress-message" id="progress-message"></div>
            </div>
        </div>

        <!-- Parameters Panel -->
        <div id="parameters-panel" class="panel">
            <div class="card">
                <h2>⚙️ Processing Parameters</h2>
                <div class="row">
                    <div class="form-group">
                        <label>t_start_cut (s)</label>
                        <input type="number" id="t_start_cut" value="5.0" step="0.1">
                    </div>
                    <div class="form-group">
                        <label>t_end_cut (s)</label>
                        <input type="number" id="t_end_cut" value="30.0" step="0.1">
                    </div>
                    <div class="form-group">
                        <label>hp_cut (Hz)</label>
                        <input type="number" id="hp_cut" value="0.1" step="0.1">
                    </div>
                    <div class="form-group">
                        <label>lp_cut (Hz)</label>
                        <input type="number" id="lp_cut" value="17000" step="100">
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>Visualization Parameters</h2>
                <div class="row">
                    <div class="form-group">
                        <label>startFiber (m)</label>
                        <input type="number" id="startFiber" value="420" step="1">
                    </div>
                    <div class="form-group">
                        <label>endFiber (m)</label>
                        <input type="number" id="endFiber" value="580" step="1">
                    </div>
                    <div class="form-group">
                        <label>startFiberProfile (m)</label>
                        <input type="number" id="startFiberProfile" value="430" step="1">
                    </div>
                    <div class="form-group">
                        <label>endFiberProfile (m)</label>
                        <input type="number" id="endFiberProfile" value="482" step="1">
                    </div>
                </div>
                <div class="row">
                    <div class="form-group">
                        <label>phase_min</label>
                        <input type="number" id="phase_min" value="-10.01" step="0.1">
                    </div>
                    <div class="form-group">
                        <label>phase_max</label>
                        <input type="number" id="phase_max" value="10.01" step="0.1">
                    </div>
                    <div class="form-group">
                        <label>scale_factor</label>
                        <input type="number" id="scale_factor" value="0.00373" step="0.0001">
                    </div>
                    <div class="form-group">
                        <label>output_name</label>
                        <input type="text" id="output_name" value="my_analysis">
                    </div>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="remove_dc" checked> Remove DC Mean
                    </label>
                </div>
            </div>
        </div>

        <!-- Load Analysis Panel -->
        <div id="load-panel" class="panel">
            <div class="card">
                <h2>📂 Load Existing Analysis</h2>
                <p style="margin-bottom: 15px; color: rgba(255,255,255,0.6);">Select a previously generated analysis to view results.</p>
                <div id="analyses-list" class="analyses-list">
                    <div style="text-align: center; padding: 20px;">Loading analyses...</div>
                </div>
            </div>
        </div>

        <!-- Results Panel -->
        <div id="results-panel" class="panel">
            <div class="card" id="results-card">
                <h2>📊 Analysis Results</h2>
                <div id="results-content">
                    <p style="color: rgba(255,255,255,0.6);">No analysis generated yet. Upload a file and click Generate, or load an existing analysis.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentFile = null;
        let outputDir = null;
        let currentAnalysisPath = null;

        function showPanel(panelName, evt) {
    document.querySelectorAll('.panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById(panelName + '-panel').classList.add('active');

    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Verificar si evt existe (viene de un click)
    if (evt && evt.target) {
        evt.target.classList.add('active');
    } else {
        // Si no hay evento, buscar el botón correspondiente
        const buttons = document.querySelectorAll('.nav-btn');
        for (let btn of buttons) {
            if (btn.textContent.includes(panelName === 'main' ? 'Main' : 
                panelName === 'parameters' ? 'Parameters' :
                panelName === 'load' ? 'Load' : 'Results')) {
                btn.classList.add('active');
                break;
            }
        }
    }
    
    if (panelName === 'load') {
        loadAnalyses();
    }
}

        function uploadFile() {
            const fileInput = document.getElementById('h5file');
            const file = fileInput.files[0];

            if (!file) {
                alert('Please select a file first');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            document.getElementById('upload-btn').disabled = true;
            document.getElementById('upload-btn').textContent = 'Uploading...';

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentFile = data.filename;
                    document.getElementById('file-info').style.display = 'block';
                    document.getElementById('file-info').innerHTML = `
                        <strong>✅ File uploaded:</strong> ${data.filename}<br>
                        <strong>Channels:</strong> ${data.num_locs}<br>
                        <strong>Duration:</strong> ${data.duration.toFixed(2)} s<br>
                        <strong>Sampling Rate:</strong> ${data.fs} Hz
                    `;
                    document.getElementById('generate-btn').disabled = false;
                } else {
                    alert('Upload failed: ' + data.error);
                }
            })
            .catch(error => {
                alert('Error uploading file: ' + error);
            })
            .finally(() => {
                document.getElementById('upload-btn').disabled = false;
                document.getElementById('upload-btn').textContent = '📤 Upload File';
            });
        }

        function loadAnalyses() {
            fetch('/list_analyses')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.analyses.length > 0) {
                    let html = '<div style="display: flex; flex-direction: column; gap: 15px;">';
                    data.analyses.forEach(analysis => {
                        const createdDate = new Date(analysis.created * 1000).toLocaleString();
                        const fileCount = Object.values(analysis.files).filter(f => f).length;
                        html += `
                            <div class="file-info" onclick="selectAnalysis('${analysis.path}')">
                                <strong>📁 ${analysis.name}</strong><br>
                                <small>Created: ${createdDate}</small><br>
                                <small>Files: ${fileCount}/6</small>
                            </div>
                        `;
                    });
                    html += '</div>';
                    document.getElementById('analyses-list').innerHTML = html;
                } else {
                    document.getElementById('analyses-list').innerHTML = '<div style="text-align: center; padding: 20px; color: rgba(255,255,255,0.6);">No analyses found. Generate one first!</div>';
                }
            })
            .catch(error => {
                document.getElementById('analyses-list').innerHTML = '<div style="text-align: center; padding: 20px; color: red;">Error loading analyses</div>';
            });
        }

        function selectAnalysis(analysisPath) {
    fetch('/load_analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: analysisPath })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let html = '<h3>✅ Analysis Loaded!</h3><div class="result-links">';
            if (data.files.dashboard) html += `<a href="/view_file/dashboard.html" class="result-link" target="_blank">📊 Dashboard</a>`;
            if (data.files.figure1) html += `<a href="/view_file/01_time_signals_fft.html" class="result-link" target="_blank">Figure 1</a>`;
            if (data.files.figure2) html += `<a href="/view_file/02_temporal_psd_map.html" class="result-link" target="_blank">Figure 2</a>`;
            if (data.files.figure3) html += `<a href="/view_file/03_roi_phase_map.html" class="result-link" target="_blank">Figure 3</a>`;
            if (data.files.figure4) html += `<a href="/view_file/04_roi_psd_map.html" class="result-link" target="_blank">Figure 4</a>`;
            if (data.files.figure5) html += `<a href="/view_file/05_2dfft_kf_analysis.html" class="result-link" target="_blank">Figure 5</a>`;
            html += '</div>';
            document.getElementById('results-content').innerHTML = html;
            showPanel('results');
        }
    });
}

function showResults() {
    fetch('/results')
    .then(response => response.json())
    .then(data => {
        if (data.success && data.output_dir) {
            let html = '<h3>✅ Analysis Complete!</h3><div class="result-links">';
            html += `<a href="/view_file/dashboard.html" class="result-link" target="_blank">📊 Dashboard</a>`;
            html += `<a href="/view_file/01_time_signals_fft.html" class="result-link" target="_blank">Figure 1</a>`;
            html += `<a href="/view_file/02_temporal_psd_map.html" class="result-link" target="_blank">Figure 2</a>`;
            html += `<a href="/view_file/03_roi_phase_map.html" class="result-link" target="_blank">Figure 3</a>`;
            html += `<a href="/view_file/04_roi_psd_map.html" class="result-link" target="_blank">Figure 4</a>`;
            html += `<a href="/view_file/05_2dfft_kf_analysis.html" class="result-link" target="_blank">Figure 5</a>`;
            html += '</div>';
            document.getElementById('results-content').innerHTML = html;
        }
    });
}

        function generateAnalysis() {
            if (!currentFile) {
                alert('Please upload a file first');
                return;
            }

            const params = {
                filename: currentFile,
                t_start_cut: parseFloat(document.getElementById('t_start_cut').value),
                t_end_cut: parseFloat(document.getElementById('t_end_cut').value),
                hp_cut: parseFloat(document.getElementById('hp_cut').value),
                lp_cut: parseFloat(document.getElementById('lp_cut').value),
                remove_dc: document.getElementById('remove_dc').checked,
                startFiber: parseFloat(document.getElementById('startFiber').value),
                endFiber: parseFloat(document.getElementById('endFiber').value),
                startFiberProfile: parseFloat(document.getElementById('startFiberProfile').value),
                endFiberProfile: parseFloat(document.getElementById('endFiberProfile').value),
                phase_min: parseFloat(document.getElementById('phase_min').value),
                phase_max: parseFloat(document.getElementById('phase_max').value),
                scale_factor: parseFloat(document.getElementById('scale_factor').value),
                output_name: document.getElementById('output_name').value
            };

            document.getElementById('generate-btn').disabled = true;
            document.getElementById('progress-container').style.display = 'block';
            document.getElementById('progress-fill').style.width = '0%';
            document.getElementById('progress-fill').textContent = '0%';
            document.getElementById('progress-message').textContent = 'Starting analysis...';

            fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(params)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    startProgressPolling();
                } else {
                    alert('Analysis failed: ' + data.error);
                    document.getElementById('generate-btn').disabled = false;
                }
            })
            .catch(error => {
                alert('Error starting analysis: ' + error);
                document.getElementById('generate-btn').disabled = false;
            });
        }

        function startProgressPolling() {
            const interval = setInterval(() => {
                fetch('/progress')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('progress-fill').style.width = data.progress + '%';
                    document.getElementById('progress-fill').textContent = data.progress + '%';
                    document.getElementById('progress-message').textContent = data.message;

                    if (data.progress >= 100) {
                        clearInterval(interval);
                        document.getElementById('generate-btn').disabled = false;
                        setTimeout(() => {
                            document.getElementById('progress-container').style.display = 'none';
                        }, 2000);
                        showResults();
                    }
                });
            }, 1000);
        }
    </script>
</body>
</html>
'''


@app.route('/files/<path:filepath>')
def serve_files(filepath):
    """Sirve archivos desde el directorio actual"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, filepath)

    if os.path.exists(full_path):
        return send_file(full_path, as_attachment=False)

    return jsonify({'error': f'File not found: {full_path}'}), 404
@app.route('/')
def index():
    return HTML_TEMPLATE


@app.route('/list_analyses')
def list_analyses():
    analyses = list_available_analyses()
    return jsonify({'success': True, 'analyses': analyses})


@app.route('/load_analysis', methods=['POST'])
def load_analysis():
    data = request.json
    analysis_path = data.get('path')

    if not analysis_path or not os.path.exists(analysis_path):
        return jsonify({'success': False, 'error': 'Analysis not found'})

    files = {
        'main': 'main.html' if os.path.exists(os.path.join(analysis_path, 'main.html')) else None,
        'dashboard': 'dashboard.html' if os.path.exists(os.path.join(analysis_path, 'dashboard.html')) else None,
        'figure1': '01_time_signals_fft.html' if os.path.exists(os.path.join(analysis_path, '01_time_signals_fft.html')) else None,
        'figure2': '02_temporal_psd_map.html' if os.path.exists(os.path.join(analysis_path, '02_temporal_psd_map.html')) else None,
        'figure3': '03_roi_phase_map.html' if os.path.exists(os.path.join(analysis_path, '03_roi_phase_map.html')) else None,
        'figure4': '04_roi_psd_map.html' if os.path.exists(os.path.join(analysis_path, '04_roi_psd_map.html')) else None,
        'figure5': '05_2dfft_kf_analysis.html' if os.path.exists(os.path.join(analysis_path, '05_2dfft_kf_analysis.html')) else None,
    }

    processing_status['output_dir'] = analysis_path

    return jsonify({'success': True, 'files': files, 'path': analysis_path})


from flask import send_from_directory


@app.route('/view_file/<path:filename>')
def view_file(filename):
    """Sirve archivos desde cualquier carpeta DAS_SIGNALS_* en la raíz del proyecto"""
    try:
        # Obtener la carpeta RAIZ del proyecto (un nivel arriba)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        print(f"Buscando en: {base_dir}")

        # Buscar en todas las carpetas DAS_SIGNALS_*
        for folder in os.listdir(base_dir):
            if folder.startswith('DAS_SIGNALS_') and os.path.isdir(os.path.join(base_dir, folder)):
                file_path = os.path.join(base_dir, folder, filename)
                print(f"Revisando: {file_path}")
                if os.path.exists(file_path):
                    print(f"✅ Archivo encontrado: {file_path}")
                    return send_file(file_path, as_attachment=False)

        return jsonify({'error': f'File {filename} not found'}), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        file = request.files['file']
        if not file:
            return jsonify({'success': False, 'error': 'No file provided'})

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        from DAS_NIDF import DASReader
        reader = DASReader(filepath)
        X, fs, dx, num_locs = reader.read_h5_file()

        return jsonify({
            'success': True,
            'filename': filename,
            'num_locs': int(num_locs),
            'duration': float(X.shape[1] / fs),
            'fs': float(fs),
            'dx': float(dx)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/generate', methods=['POST'])
def generate():
    global processing_status
    params = request.json

    processing_status = {
        'is_processing': True,
        'progress': 0,
        'message': 'Initializing...',
        'output_dir': None
    }

    def process():
        global processing_status
        try:
            processing_status['message'] = 'Reading file...'
            processing_status['progress'] = 10

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], params['filename'])
            from DAS_NIDF import DASReader, DASPreprocessor, DASVisualizer

            reader = DASReader(filepath)
            X, fs, dx, num_locs = reader.read_h5_file()

            processing_status['message'] = 'Creating time vectors...'
            processing_status['progress'] = 20

            num_tr = X.shape[0]
            t = np.arange(num_tr) / fs
            y = np.arange(num_locs).reshape(-1, 1) * dx
            X = X.T

            processing_status['message'] = 'Applying temporal cut...'
            processing_status['progress'] = 30

            preprocessor = DASPreprocessor()
            X, t = preprocessor.temporal_cut(X, t, params['t_start_cut'], params['t_end_cut'])
            num_locs, num_tr = X.shape

            if params['remove_dc']:
                processing_status['message'] = 'Removing DC mean...'
                processing_status['progress'] = 40
                X = X - np.mean(X, axis=1, keepdims=True)

            processing_status['message'] = 'Applying bandpass filter...'
            processing_status['progress'] = 50

            # Validar frecuencias del filtro - si falla, saltar
            try:
                X = preprocessor.bandpass_filter(X, fs, params['hp_cut'], params['lp_cut'])
            except Exception as e:
                processing_status['message'] = f'Warning: Filter skipped ({str(e)[:50]})...'
                print(f"Filter error: {e}. Skipping filter.")
                # Continua sem o filtro

            processing_status['message'] = 'Creating visualizer...'
            processing_status['progress'] = 60

            visualizer = DASVisualizer(
                X=X, t=t, y=y[:, 0], fs=fs, dx=dx,
                num_locs=num_locs, num_tr=len(t)
            )

            processing_status['message'] = 'Generating visualizations...'
            processing_status['progress'] = 70

            viz_params = {
                'startFiber': params['startFiber'],
                'endFiber': params['endFiber'],
                'startFiberProfile': params['startFiberProfile'],
                'endFiberProfile': params['endFiberProfile'],
                'phase_min': params['phase_min'],
                'phase_max': params['phase_max'],
                'hp_cut': params['hp_cut'],
                'lp_cut': params['lp_cut'],
                'scale_factor': params['scale_factor'],
                'output_name': params['output_name']
            }

            output_dir = visualizer.run_complete_visualization(viz_params)

            processing_status['message'] = 'Complete!'
            processing_status['progress'] = 100
            processing_status['is_processing'] = False
            processing_status['output_dir'] = output_dir

        except Exception as e:
            processing_status['is_processing'] = False
            processing_status['message'] = f'Error: {str(e)}'
            print(f"Process error: {e}")

    thread = threading.Thread(target=process)
    thread.start()

    return jsonify({'success': True})


@app.route('/progress')
def progress():
    return jsonify({
        'progress': processing_status['progress'],
        'message': processing_status['message']
    })


@app.route('/results')
def results():
    return jsonify({
        'success': processing_status['output_dir'] is not None,
        'output_dir': processing_status['output_dir']
    })


@app.route('/download/<file_type>')
def download(file_type):
    output_dir = processing_status['output_dir']
    if not output_dir:
        return jsonify({'error': 'No output directory'})

    file_map = {
        'main': 'main.html',
        'dashboard': 'dashboard.html',
        'figure1': '01_time_signals_fft.html',
        'figure2': '02_temporal_psd_map.html',
        'figure3': '03_roi_phase_map.html',
        'figure4': '04_roi_psd_map.html',
        'figure5': '05_2dfft_kf_analysis.html'
    }

    filename = file_map.get(file_type)
    if not filename:
        return jsonify({'error': 'Invalid file type'})

    filepath = os.path.join(output_dir, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'})

    return send_file(filepath, as_attachment=False)


def run_server(port=5000, open_browser=True):
    """Start the web server"""
    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(f'http://localhost:{port}')).start()
    app.run(debug=False, port=port, host='0.0.0.0')