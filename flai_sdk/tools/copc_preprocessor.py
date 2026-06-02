"""
Local COPC preprocessing pipeline for the flai-sdk.

Converts LAS/LAZ files to COPC, generates overview.copc.laz, and computes stats
— all locally — so the upload can skip server-side preprocessing.

Requires: pdal CLI installed (brew install pdal / conda install -c conda-forge pdal)
Uses: laspy + numpy (already in SDK deps) for stats and overview subsampling.
"""

import os
import shutil
import json
import subprocess
import tempfile
import time
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import List, Optional, Tuple

import laspy
import numpy as np


def check_pdal_installed() -> bool:
    """Check if pdal CLI is available on the system."""
    try:
        result = subprocess.run(['pdal', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def is_copc_file(filepath: Path) -> bool:
    """Check if a file is already in COPC format."""
    if not str(filepath).lower().endswith('.copc.laz'):
        return False
    try:
        with laspy.open(str(filepath)) as f:
            header = f.header
            return (len(header.vlrs) > 1 and
                    'COPC' in header.vlrs[0].description)
    except Exception:
        return False


def _remove_copc_from_header(header):
    """Strip COPC VLRs/EVLRs so laspy can write the data as regular LAZ."""
    if len(header.vlrs) > 0 and 'COPC' in getattr(header.vlrs[0], 'description', ''):
        header.vlrs = header.vlrs[1:]
    if header.evlrs is not None and len(header.evlrs) > 0 and 'EPT' in getattr(header.evlrs[0], 'description', ''):
        header.evlrs = header.evlrs[1:]
    return header


def _pdal_translate_to_copc(input_path: Path, output_path: Path, retries: int = 3) -> bool:
    """Convert a LAS/LAZ file to COPC using pdal translate subprocess."""
    with laspy.open(str(input_path)) as f:
        header = f.header
        scales = header.scales
        offsets = header.offsets
        in_is_copc = (len(header.vlrs) > 1 and
                      'COPC' in header.vlrs[0].description and
                      str(input_path).lower().endswith('.copc.laz'))

    reader_type = 'copc' if in_is_copc else 'las'

    run_args = [
        'pdal', 'translate',
        str(input_path),
        str(output_path),
        f'--readers.{reader_type}.nosrs=true',
    ]

    if not in_is_copc:
        run_args.append(f'--readers.{reader_type}.use_eb_vlr=true')

    run_args.append('--writers.copc.forward=all')

    if scales is not None:
        run_args.append(f'--writers.copc.scale_x={np.format_float_positional(scales[0])}')
        run_args.append(f'--writers.copc.scale_y={np.format_float_positional(scales[1])}')
        run_args.append(f'--writers.copc.scale_z={np.format_float_positional(scales[2])}')
    if offsets is not None:
        run_args.append(f'--writers.copc.offset_x={np.format_float_positional(offsets[0])}')
        run_args.append(f'--writers.copc.offset_y={np.format_float_positional(offsets[1])}')
        run_args.append(f'--writers.copc.offset_z={np.format_float_positional(offsets[2])}')

    for attempt in range(1, retries + 1):
        result = subprocess.run(run_args, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        if attempt < retries:
            time.sleep(2)

    raise RuntimeError(
        f'pdal translate failed after {retries} attempts for {input_path}.\n'
        f'stderr: {result.stderr}\nstdout: {result.stdout}'
    )


def _compute_file_stats(filepath: Path, unit: str = 'm') -> dict:
    """Compute per-file statistics using chunked laspy reading."""
    unit_scale = {'m': 1.0, 'ft': 0.3048, 'us-ft': 0.3048006096012192, 'deg': 1.0}.get(unit, 1.0)
    area_round_precision = round(2 / unit_scale) if unit_scale != 0 else 2

    with laspy.open(str(filepath)) as f:
        header = f.header
        point_count = header.point_count

    intensity_bins = np.arange(0, 2 ** 16 + 10, 10, dtype=np.uint32)
    num_returns_bins = np.arange(20 + 1, dtype=np.uint32)
    return_num_bins = np.arange(20 + 1, dtype=np.uint32)
    classification_bins = np.arange(2 ** 8 + 1, dtype=np.uint32)

    intensity_hist = np.zeros(len(intensity_bins) - 1, dtype=np.uint32)
    num_returns_hist = np.zeros(20, dtype=np.uint32)
    return_num_hist = np.zeros(20, dtype=np.uint32)
    classification_hist = np.zeros(256, dtype=np.uint32)

    xy_rounded_unique_per_chunk = []
    chunk_size = int(min(point_count, 1_000_000))

    if chunk_size == 0:
        return {
            'point_count': 0, 'area': 0,
            'intensity_hist': intensity_hist,
            'num_returns_hist': num_returns_hist,
            'return_num_hist': return_num_hist,
            'classification_hist': classification_hist,
        }

    with laspy.open(str(filepath)) as reader:
        for points in reader.chunk_iterator(chunk_size):
            if hasattr(points, 'intensity'):
                h, _ = np.histogram(points.intensity, bins=intensity_bins)
                intensity_hist += np.uint32(h)

            if hasattr(points, 'number_of_returns'):
                h, _ = np.histogram(points.number_of_returns, bins=num_returns_bins)
                num_returns_hist += np.uint32(h)

            if hasattr(points, 'return_number'):
                h, _ = np.histogram(points.return_number, bins=return_num_bins)
                return_num_hist += np.uint32(h)

            if hasattr(points, 'classification'):
                h, _ = np.histogram(points.classification, bins=classification_bins)
                classification_hist += np.uint32(h)

            # Area computation: round to 2m grid cells
            xy_rounded = np.vstack((
                (np.array(points.x) / area_round_precision).astype(int),
                (np.array(points.y) / area_round_precision).astype(int)
            )).T
            xy_rounded_unique_per_chunk.append(np.unique(xy_rounded, axis=0))

    area = 0
    if len(xy_rounded_unique_per_chunk) > 0:
        area = np.unique(np.vstack(xy_rounded_unique_per_chunk), axis=0).shape[0] * area_round_precision ** 2

    return {
        'point_count': point_count,
        'area': area,
        'intensity_hist': intensity_hist,
        'num_returns_hist': num_returns_hist,
        'return_num_hist': return_num_hist,
        'classification_hist': classification_hist,
    }


def _normalize_hist_cumulative(hist: np.ndarray) -> list:
    """Cumulative normalize histogram to 0-100%, clip after first 100%."""
    if hist.shape[0] == 0 or np.max(hist) == 0:
        return hist.tolist()
    cumsum = np.cumsum(hist).astype(float)
    cumsum = np.round(100 * cumsum / np.max(cumsum), 2)
    idx_100 = np.min(np.where(cumsum >= 100)[0]) + 1
    return cumsum[:idx_100].tolist()


class CopcPreprocessor:
    """
    Local COPC preprocessing pipeline.

    Converts LAS/LAZ → COPC, generates overview, computes stats.
    Returns a zip file + stats ready for upload_precomputed_copc().
    """

    def __init__(self, input_files: List[Path], output_dir: Path, unit: str = 'm',
                 target_overview_density: float = 0.5, max_overview_points: int = 1_400_000_000,
                 log_fn=None):
        self.input_files = input_files
        self.output_dir = output_dir
        self.unit = unit
        self.target_overview_density = target_overview_density
        self.max_overview_points = max_overview_points
        self._log = log_fn or print

    def validate_files(self) -> List[dict]:
        """Validate input files and return their info."""
        file_infos = []
        for f in self.input_files:
            if not f.exists():
                raise FileNotFoundError(f'File not found: {f}')
            try:
                with laspy.open(str(f)) as reader:
                    header = reader.header
                    info = {
                        'path': f,
                        'point_count': header.point_count,
                        'is_copc': is_copc_file(f),
                        'scales': header.scales,
                        'offsets': header.offsets,
                    }
                    if header.point_count == 0:
                        self._log(f'Warning: {f.name} has 0 points, skipping')
                        continue
                    file_infos.append(info)
            except Exception as e:
                raise RuntimeError(f'Cannot read {f}: {e}')

        if not file_infos:
            raise RuntimeError('No valid point cloud files found')
        return file_infos

    def convert_to_copc(self, file_infos: List[dict]) -> List[Path]:
        """Convert all input files to COPC format."""
        copc_dir = self.output_dir / 'copc'
        copc_dir.mkdir(parents=True, exist_ok=True)
        copc_files = []

        for info in file_infos:
            src = info['path']
            stem = src.stem
            if stem.lower().endswith('.copc'):
                stem = stem[:-5]
            out_path = copc_dir / f'{stem}.copc.laz'

            if info['is_copc']:
                self._log(f'  {src.name} is already COPC, copying...')
                shutil.copy2(str(src), str(out_path))
            else:
                self._log(f'  Converting {src.name} to COPC...')
                _pdal_translate_to_copc(src, out_path)

            copc_files.append(out_path)

        return copc_files

    def generate_overview(self, copc_files: List[Path]) -> Path:
        """Generate overview.copc.laz by subsampling all files."""
        overview_dir = self.output_dir / 'overview'
        overview_dir.mkdir(parents=True, exist_ok=True)

        # Collect subsampled points from each file
        subset_files = []
        total_subset_points = 0

        for copc_file in copc_files:
            las_data = laspy.read(str(copc_file))
            n_p = las_data.header.point_count
            d_xy = las_data.header.maxs - las_data.header.mins

            if n_p == 0 or d_xy[0] * d_xy[1] == 0:
                continue

            d_p = n_p / (d_xy[0] * d_xy[1])

            try:
                n_p_sub = round(n_p / d_p * self.target_overview_density)
            except (ValueError, ZeroDivisionError):
                n_p_sub = min(n_p, 10000)

            n_p_sub = round(min(max(n_p_sub, 1), n_p))

            # Apply max_points cap proportionally
            if self.max_overview_points > 0 and total_subset_points + n_p_sub > self.max_overview_points:
                n_p_sub = max(1, self.max_overview_points - total_subset_points)

            self._log(f'  {copc_file.name}: subsample {n_p_sub}/{n_p} points ({n_p_sub / n_p * 100:.1f}%)')

            idx = np.random.choice(n_p, n_p_sub, replace=False)
            subset_data = las_data[idx]

            # Strip COPC VLRs so laspy can write as regular LAZ
            _remove_copc_from_header(subset_data.header)

            # Clear EVLRs to avoid laspy write error with plain list
            subset_data.evlrs = []

            # Use .stem twice to strip both .copc and .laz from .copc.laz names
            base_name = copc_file.stem
            if base_name.endswith('.copc'):
                base_name = base_name[:-5]
            subset_path = overview_dir / f'subset_{base_name}.laz'
            subset_data.write(str(subset_path))
            subset_files.append(subset_path)
            total_subset_points += n_p_sub

            del las_data, subset_data

        if not subset_files:
            raise RuntimeError('No points to create overview from')

        # Merge subsets and convert to COPC using PDAL (avoids laspy point format issues)
        overview_copc = overview_dir / 'overview.copc.laz'
        self._log(f'  Merging and converting overview to COPC ({total_subset_points} points)...')

        pdal_pipeline = {
            "pipeline": [str(f) for f in subset_files] + [
                {"type": "filters.merge"},
                {
                    "type": "writers.copc",
                    "filename": str(overview_copc)
                }
            ]
        }

        pipeline_json = json.dumps(pdal_pipeline)
        result = subprocess.run(
            ['pdal', 'pipeline', '--stdin'],
            input=pipeline_json,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f'PDAL merge failed: {result.stderr}')

        # Clean up subset files
        for sf in subset_files:
            sf.unlink()

        return overview_copc

    def compute_stats(self, copc_files: List[Path]) -> Tuple[dict, list]:
        """Compute dataset-level and per-file stats."""
        # Aggregate raw histograms across all files
        total_intensity = np.zeros(len(np.arange(0, 2 ** 16 + 10, 10)) - 1, dtype=np.uint32)
        total_num_returns = np.zeros(20, dtype=np.uint32)
        total_return_num = np.zeros(20, dtype=np.uint32)
        total_classification = np.zeros(256, dtype=np.uint32)
        total_points = 0
        total_area = 0

        file_stats_list = []

        for copc_file in copc_files:
            self._log(f'  Computing stats for {copc_file.name}...')
            raw = _compute_file_stats(copc_file, self.unit)

            total_intensity += raw['intensity_hist']
            total_num_returns += raw['num_returns_hist']
            total_return_num += raw['return_num_hist']
            total_classification += raw['classification_hist']
            total_points += raw['point_count']
            total_area += raw['area']

            # Per-file stats: cumulative normalize (except classification)
            file_stat = {
                'file_name': copc_file.name,
                'folder': 'copc',
                'point_count': int(raw['point_count']),
                'intensity_hist': _normalize_hist_cumulative(raw['intensity_hist']),
                'num_returns_hist': _normalize_hist_cumulative(raw['num_returns_hist']),
                'return_num_hist': _normalize_hist_cumulative(raw['return_num_hist']),
                'classification_hist': raw['classification_hist'].tolist(),
            }
            file_stats_list.append(file_stat)

        # Dataset-level stats
        mean_density = total_points / total_area if total_area > 0 else 0

        dataset_stats = {
            'point_count': int(total_points),
            'point_density': float(mean_density),
            'area': float(total_area),
            'intensity_hist': _normalize_hist_cumulative(total_intensity),
            'num_returns_hist': _normalize_hist_cumulative(total_num_returns),
            'return_num_hist': _normalize_hist_cumulative(total_return_num),
            'classification_hist': total_classification.tolist(),
        }

        return dataset_stats, file_stats_list

    def run(self) -> Tuple[Path, dict, list]:
        """
        Run the full preprocessing pipeline.

        Returns: (zip_path, dataset_stats, file_stats)
        """
        if not check_pdal_installed():
            raise RuntimeError(
                'pdal CLI not found. Install it:\n'
                '  macOS:  brew install pdal\n'
                '  conda:  conda install -c conda-forge pdal\n'
                '  Ubuntu: apt install pdal'
            )

        self._log('Validating input files...')
        file_infos = self.validate_files()
        self._log(f'  Found {len(file_infos)} valid file(s), '
                  f'{sum(i["point_count"] for i in file_infos):,} total points')

        self._log('Converting to COPC...')
        copc_files = self.convert_to_copc(file_infos)

        self._log('Generating overview...')
        overview_path = self.generate_overview(copc_files)

        self._log('Computing statistics...')
        dataset_stats, file_stats = self.compute_stats(copc_files)

        # Create zip with all COPC files + overview
        self._log('Creating upload archive...')
        zip_path = self.output_dir / 'precomputed_copc.zip'
        with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_STORED) as zf:
            for copc_file in copc_files:
                zf.write(str(copc_file), copc_file.name)
            zf.write(str(overview_path), overview_path.name)

        self._log('Preprocessing complete.')
        return zip_path, dataset_stats, file_stats
