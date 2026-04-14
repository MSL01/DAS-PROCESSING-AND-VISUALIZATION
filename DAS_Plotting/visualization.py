"""
Module for DAS data visualization using Holoviews + Datashader
Preserves exact original code without modifications
"""

import os
import numpy as np
import holoviews as hv
import datashader as ds
from holoviews.operation.datashader import rasterize
from skimage.measure import block_reduce
import webbrowser
from typing import  Optional, Dict
import warnings

hv.extension('bokeh')
warnings.filterwarnings('ignore')


class DASVisualizer:
    def __init__(self, X: np.ndarray, t: np.ndarray, y: np.ndarray,
                 fs: float, dx: float, num_locs: int, num_tr: int,
                 metadata: Optional[Dict] = None):
        """
        Initialize with DAS data.
        """
        self.X = X
        self.t = t
        self.y = y
        self.fs = fs
        self.dx = dx
        self.num_locs = num_locs
        self.num_tr = num_tr
        self.metadata = metadata or {}
        self.generated_files = []

    def smooth(self, x, window):
        window = int(window)
        return np.convolve(x, np.ones(window)/window, mode='same')

    def clean_and_downsample(self, x, y, max_points=None):
        x = np.asarray(x).ravel()
        y = np.asarray(y).ravel()
        mask = np.isfinite(x) & np.isfinite(y)
        x, y = x[mask], y[mask]
        if len(x) > max_points:
            step = len(x) // max_points
            x, y = x[::step], y[::step]
        return x, y

    def clean_array(self, arr):
        arr = np.asarray(arr).astype(np.float64)
        mask = ~np.isfinite(arr)
        if mask.any():
            arr = arr.copy()
            arr[mask] = 0.0
        return arr

    def validate_coords(self, x, y, data):
        if x.size == 0 or y.size == 0:
            raise ValueError("Empty coordinate array")
        if data.shape != (y.size, x.size):
            raise ValueError(f"Shape mismatch: data {data.shape} vs (y={y.size}, x={x.size})")
        return x, y, data

    '''
    Figure 1: Signal
    '''

    def signal_fft_plot(self, chan_view, chan_view2, phase_min, phase_max,
                     hp_cut, lp_cut, scale_factor, output_dir):
        print('Generating phase map with time signals...')

        nshow = min(self.num_tr, int(10 * self.fs))
        phase_data = self.X[:, :nshow].T

        left = float(self.y[0].item() if hasattr(self.y[0], 'item') else self.y[0])
        right = float(self.y[-1].item() if hasattr(self.y[-1], 'item') else self.y[-1])
        bottom = float(self.t[0].item() if hasattr(self.t[0], 'item') else self.t[0])
        top = float(self.t[-1].item() if hasattr(self.t[-1], 'item') else self.t[-1])
        bounds = (left, bottom, right, top)

        phase_img = hv.Image(phase_data, bounds=bounds, kdims=['Distance (m)', 'Time (s)'])
        phase_raster = rasterize(phase_img, aggregator=ds.mean(), width=800, height=400)
        phase_map = phase_raster.opts(
            cmap='viridis', colorbar=True, clabel='Phase (rad)',
            title=f'Band-pass filter {hp_cut}-{lp_cut} Hz',
            xlabel='Distance (m)', ylabel='Time (s)'
        )
        if self.y.ndim == 0 or self.y.size == 1:
            pos1 = float(self.y)
            pos2 = float(self.y)
        elif self.y.ndim == 1:
            pos1 = float(self.y[chan_view].item()) if hasattr(self.y[chan_view], 'item') else self.y[chan_view]
            pos2 = float(self.y[chan_view2].item()) if hasattr(self.y[chan_view2], 'item') else self.y[chan_view2]
        else:
            pos1 = self.y.flat[chan_view]
            pos2 = self.y.flat[chan_view2]

        t_clean = self.t[:nshow].ravel()
        signal1 = self.X[chan_view, :nshow].ravel()
        signal2 = self.X[chan_view2, :nshow].ravel()
        t_ds, signal1_ds = self.clean_and_downsample(t_clean, signal1, max_points=10000)
        t_ds, signal2_ds = self.clean_and_downsample(t_clean, signal2, max_points=10000)
        curve1 = hv.Curve((t_ds, signal1_ds),
                          kdims=['Time (s)'], vdims=['Phase (rad)'],
                          label=f'Ch {chan_view} ({pos1:.1f} m)').opts(line_width=1.5, color='blue')
        curve2 = hv.Curve((t_ds, signal2_ds),
                          kdims=['Time (s)'], vdims=['Phase (rad)'],
                          label=f'Ch {chan_view2} ({pos2:.1f} m)').opts(line_width=1.5, color='orange')
        time_plot = (curve1 * curve2).opts(
            title=f'Time signals - Channel {chan_view} vs {chan_view2}',
            xlabel='Time (s)', ylabel='Phase (rad)',
            width=1200, height=850, legend_position='top_right', show_grid=True,
            xlim=(t_clean[0], min(t_clean[0]+5, t_clean[-1])),
            tools=['hover', 'box_zoom', 'reset', 'pan', 'save']
        )
        L = len(signal1)
        f = self.fs * np.arange(0, L//2 + 1) / L
        Y1 = np.fft.fft(signal1)
        P1_1 = np.abs(Y1 / L)[:L//2+1]
        P1_1[1:-1] = 2 * P1_1[1:-1]
        Y2 = np.fft.fft(signal2)
        P1_2 = np.abs(Y2 / L)[:L//2+1]
        P1_2[1:-1] = 2 * P1_2[1:-1]
        P1_1_smooth = self.smooth(P1_1, 10)
        P1_2_smooth = self.smooth(P1_2, 10)
        f_ds, P1_1_ds = self.clean_and_downsample(f, P1_1_smooth, max_points=5000)
        _, P1_2_ds = self.clean_and_downsample(f, P1_2_smooth, max_points=5000)
        fft_curve1 = hv.Curve((f_ds, P1_1_ds),
                              kdims=['Frequency (Hz)'], vdims=['Amplitude'],
                              label=f'Ch {chan_view}').opts(line_width=1.5, color='blue')
        fft_curve2 = hv.Curve((f_ds, P1_2_ds),
                              kdims=['Frequency (Hz)'], vdims=['Amplitude'],
                              label=f'Ch {chan_view2}').opts(line_width=1.5, color='orange')
        fft_plot = (fft_curve1 * fft_curve2).opts(
            title='Frequency Spectrum (smoothed)',
            xlabel='Frequency (Hz)', ylabel='Amplitude (linear)',
            width=1200, height=850, legend_position='top_right', show_grid=True,
            xlim=(0, min(10000, self.fs/2)),
            tools=['hover', 'box_zoom', 'reset', 'pan', 'save']
        )
        fig1_layout = (time_plot + fft_plot).cols(1)
        fig1_file = os.path.join(output_dir, "01_time_signals_fft.html")
        hv.save(fig1_layout, fig1_file)
        self.generated_files.append(fig1_file)
        print(f"  ✓ Saved: {os.path.basename(fig1_file)}")

    '''
        Figure 1: Temporal PSD map
    '''
    def phase_psd_plot(self, hp_cut, lp_cut, scale_factor, phase_min, phase_max, output_dir):
        """FIGURA 2: Temporal PSD map"""
        from DAS_Plotting.analysis import integrated_band_spectrogram

        print('Generating temporal PSD map...')

        nshow = min(self.num_tr, int(10 * self.fs))
        freq_band = [hp_cut, min(lp_cut, self.fs/2 - 1)]
        PSD_map, t_spec = integrated_band_spectrogram(self.X, self.fs, freq_band)

        y_clean = self.clean_array(self.y.ravel())
        t_clean = self.clean_array(self.t[:nshow].ravel())
        t_psd_clean = self.clean_array(t_spec.ravel())

        phase_data = self.X[:, :nshow].T
        phase_qmesh = hv.QuadMesh((y_clean, t_clean, phase_data),
                                  kdims=['Distance (m)', 'Time (s)'], vdims=['Phase (rad)'])
        phase_raster = rasterize(phase_qmesh, aggregator=ds.mean(), width=1200, height=850)
        phase_map = phase_raster.opts(
            cmap='viridis', colorbar=True, clabel='Phase (rad)',
            title=f'Band-pass filter {hp_cut}-{lp_cut} Hz | Scale factor: {scale_factor}',
            xlabel='Distance (m)', ylabel='Time (s)', clim=(phase_min, phase_max),
            width=1200, height=850,
            invert_yaxis=True, tools=['hover', 'box_zoom', 'reset', 'pan', 'save']
        ).redim.range(Time=(max(t_clean[0],5), min(10,t_clean[-1])))

        PSD_dB = 10 * np.log10(PSD_map + 1e-10)
        psd_data = PSD_dB.T
        psd_qmesh = hv.QuadMesh((y_clean, t_psd_clean, psd_data),
                                kdims=['Distance (m)', 'Time (s)'], vdims=['Band Intensity (dB)'])
        psd_raster = rasterize(psd_qmesh, aggregator=ds.mean(), width=1200, height=850)
        psd_map = psd_raster.opts(
            cmap='viridis', colorbar=True, clabel='Band Intensity (dB)',
            title=f'PSD {freq_band[0]}-{freq_band[1]} Hz',
            xlabel='Distance (m)', ylabel='Time (s)', invert_yaxis=True,
            width=1200, height=850,
            tools=['hover', 'box_zoom', 'reset', 'pan', 'save']
        )

        layout = (phase_map + psd_map).cols(1)
        fig2_file = os.path.join(output_dir, "02_temporal_psd_map.html")
        hv.save(layout, fig2_file)
        self.generated_files.append(fig2_file)
        print(f"  ✓ Saved: {os.path.basename(fig2_file)}")

    '''
        Figure 3: Phase ROI
    '''
    def phase_roi_plot(self, startFiber, endFiber, phase_min, phase_max, output_dir):
        print('Generating Phase ROI...')
        nshow = min(self.num_tr, int(10 * self.fs))
        y_full = self.y[:, 0] if self.y.ndim > 1 else self.y
        mask_roi = (y_full >= startFiber) & (y_full <= endFiber)
        y_roi = y_full[mask_roi]
        phase_roi = self.X[mask_roi, :nshow].T
        t_full = self.clean_array(self.t[:nshow].ravel())
        phase_roi_qmesh = hv.QuadMesh((y_roi, t_full, phase_roi),
                                      kdims=['Distance (m)', 'Time (s)'],
                                      vdims=['Phase (rad)'])
        phase_roi_raster = rasterize(phase_roi_qmesh, aggregator=ds.mean(), width=900, height=600)
        phase_roi_map = phase_roi_raster.opts(
            cmap='viridis', colorbar=True, clabel='Phase (rad)',
            title=f'Phase ROI {startFiber:.0f}-{endFiber:.0f} m',
            xlabel='Distance (m)', ylabel='Time (s)',
            width=1200, height=850,
            clim=(phase_min, phase_max), invert_yaxis=True,
            tools=['hover', 'box_zoom', 'reset', 'pan', 'save']
        ).redim.range(Time=(5, 10))
        layout = (phase_roi_map)
        fig3_file = os.path.join(output_dir, "03_roi_phase_map.html")
        hv.save(layout, fig3_file)
        self.generated_files.append(fig3_file)
        print(f"  ✓ Saved: {os.path.basename(fig3_file)}")

    '''
        Figure 4: PSD ROI
    '''

    def psd_roi_plot(self, startFiber, endFiber, hp_cut, lp_cut, output_dir):
        from DAS_Plotting.analysis import integrated_band_spectrogram
        print('Generating PSD ROI...')
        freq_band = [hp_cut, min(lp_cut, self.fs/2 - 1)]
        PSD_map, t_spec = integrated_band_spectrogram(self.X, self.fs, freq_band)
        PSD_dB = 10 * np.log10(PSD_map + 1e-10)
        y_full = self.y[:, 0] if self.y.ndim > 1 else self.y
        mask_roi = (y_full >= startFiber) & (y_full <= endFiber)
        y_roi = y_full[mask_roi]
        psd_data = PSD_dB.T
        psd_roi = psd_data[:, mask_roi]
        t_psd = self.clean_array(t_spec.ravel())
        psd_roi_qmesh = hv.QuadMesh((y_roi, t_psd, psd_roi),
                                    kdims=['Distance (m)', 'Time (s)'],
                                    vdims=['Band Intensity (dB)'])
        psd_roi_raster = rasterize(psd_roi_qmesh, aggregator=ds.mean(), width=1200, height=850)
        psd_roi_map = psd_roi_raster.opts(
            cmap='viridis', colorbar=True, clabel='Band Intensity (dB)',
            title=f'PSD ROI {startFiber:.0f}-{endFiber:.0f} m',
            xlabel='Distance (m)', ylabel='Time (s)',
            invert_yaxis=True,
            width=1200, height=850,
            tools=['hover', 'box_zoom', 'reset', 'pan', 'save']
        )
        layout = (psd_roi_map)
        fig4_file = os.path.join(output_dir, "04_roi_psd_map.html")
        hv.save(layout, fig4_file)
        self.generated_files.append(fig4_file)
        print(f"  ✓ Saved: {os.path.basename(fig4_file)}")

    '''
        Figure 5: K-F Analysis
    '''

    def k_f_plot(self, startFiber, endFiber, scale_factor, output_dir):
        from DAS_Plotting.analysis import fft_2d_analysis
        print('Generating 2D FFT (k‑f) of ROI...')
        y_full = self.y[:, 0] if self.y.ndim > 1 else self.y
        mask_roi = (y_full >= startFiber) & (y_full <= endFiber)
        X_roi = self.X[mask_roi, :]
        F_dB, f_vec, k_vec = fft_2d_analysis(X_roi, self.fs, self.dx, scale_factor)
        F_dB = np.nan_to_num(F_dB, nan=-100, posinf=-100, neginf=-100)
        if k_vec[0] > k_vec[-1]:
            k_vec = k_vec[::-1]
            F_dB = F_dB[::-1, :]
        if f_vec[0] > f_vec[-1]:
            f_vec = f_vec[::-1]
            F_dB = F_dB[:, ::-1]
        fft_qmesh = hv.QuadMesh((f_vec, k_vec, F_dB),
                                kdims=['Frequency (Hz)', 'Wavenumber (cycles/m)'],
                                vdims=['Spectral Amplitude (dB)'])
        fft_raster = rasterize(fft_qmesh, aggregator=ds.mean(), width=1200, height=850)
        f_max = min(5000, self.fs/2)
        k_max = 25
        vmin_fft = np.percentile(F_dB, 30)
        vmax_fft = np.percentile(F_dB, 99.9)
        fft_plot = fft_raster.opts(
            cmap='jet', colorbar=True, clabel='Spectral Amplitude (dB)',
            title=f'2D FFT - Region {startFiber:.0f}-{endFiber:.0f} m',
            xlabel='Frequency (Hz)', ylabel='Wavenumber (cycles/m)',
            clim=(vmin_fft, vmax_fft),
            width=1200, height=850,
            tools=['hover', 'box_zoom', 'reset', 'pan', 'save']
        ).redim.range(Frequency=(-f_max, f_max), Wavenumber=(-k_max, k_max))
        layout = (fft_plot)
        fig5_file = os.path.join(output_dir, "05_2dfft_kf_analysis.html")
        hv.save(layout, fig5_file)
        self.generated_files.append(fig5_file)
        print(f"  ✓ Saved: {os.path.basename(fig5_file)}")

    '''
        Dashboard
    '''
    def create_dashboard(self, output_dir):
        dashboard_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>DAS Data Analysis Dashboard</title>
    <style>
        body {{ background: white; font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; }}
        h1 {{ font-size: 32px; font-weight: 300; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; color: #2c3e50; }}
        .graph {{ margin: 40px 0; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.05); background: white; }}
        .graph-title {{ padding: 15px 25px; background: #f8f9fa; border-bottom: 1px solid #dee2e6; font-weight: 600; font-size: 18px; color: #495057; }}
        iframe {{ width: 100%; height: 850px; border: none; display: block; }}
    </style>
</head>
<body>
    <h1>📊 DAS Data – Interactive Dashboard</h1>
"""
        for i, filepath in enumerate(self.generated_files, 1):
            filename = os.path.basename(filepath)
            title = filename.replace(".html", "").replace("_", " ").replace(f"{i:02d} ", "")
            dashboard_html += f"""
    <div class="graph">
        <div class="graph-title">Figure {i}: {title}</div>
        <iframe src="{filename}"></iframe>
    </div>
    """
        dashboard_html += """
</body>
</html>
"""
        dashboard_path = os.path.join(output_dir, "dashboard.html")
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(dashboard_html)

        return dashboard_path

    def run_complete_visualization(self, params):
        """
        Run complete visualization pipeline - generates all figures and dashboard
        """
        startFiber = params['startFiber']
        endFiber = params['endFiber']
        startFiberProfile = params['startFiberProfile']
        endFiberProfile = params['endFiberProfile']
        phase_min = params['phase_min']
        phase_max = params['phase_max']
        hp_cut = params['hp_cut']
        lp_cut = params['lp_cut']
        scale_factor = params['scale_factor']
        output_name = params.get('output_name', 'das_analysis')
        output_dir = f"DAS_SIGNALS_{output_name}"
        os.makedirs(output_dir, exist_ok=True)
        self.generated_files = []
        y_flat = self.y[:, 0] if self.y.ndim > 1 else self.y
        chan_view = np.argmin(np.abs(y_flat - startFiberProfile))
        chan_view2 = np.argmin(np.abs(y_flat - endFiberProfile))
        print("GENERATING FIGURE 1: Phase Map with Time Signals")
        self.signal_fft_plot(chan_view, chan_view2, phase_min, phase_max,
                          hp_cut, lp_cut, scale_factor, output_dir)
        print("GENERATING FIGURE 2: PSD Maps")
        self.phase_psd_plot(hp_cut, lp_cut, scale_factor, phase_min, phase_max, output_dir)
        print("GENERATING FIGURE 3: ROI Phase Map")
        self.phase_roi_plot(startFiber, endFiber, phase_min, phase_max, output_dir)
        print("GENERATING FIGURE 4: ROI PSD Map")
        self.psd_roi_plot(startFiber, endFiber, hp_cut, lp_cut, output_dir)
        print("GENERATING FIGURE 5: F-K Analysis")
        self.k_f_plot(startFiber, endFiber, scale_factor, output_dir)
        dashboard_path = self.create_dashboard(output_dir)
        webbrowser.open('file://' + os.path.realpath(dashboard_path))

        return dashboard_path