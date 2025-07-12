import laspy
from pathlib import Path
import click
import numpy as np


def fileinfo(file: Path):
    las = laspy.read(file)

    click.echo('\n******')
    click.echo('Header')
    click.echo('******\n')
    click.echo(f'Generating software: {las.header.generating_software}')

    click.echo(f'VLRs -> LASF_Projection: {las.header._vlrs.get_by_id("LASF_Projection")}')
    click.echo(f'CRS: {las.header.parse_crs()}')
    click.echo(f'VLRs: {las.header.vlrs}')


def convertFeetToMeters(file_in: Path, file_out: Path):
    las = laspy.read(file_in)
    conversion = 0.3048006096012192

    # las.header.scales = np.array([0.0001, 0.0001, 0.0001])
    # las.header.offsets = np.array([np.min(las.points.x) * conversion, np.min(las.points.y) * conversion, np.min(las.points.y) * conversion])
    # las.points.x *= conversion
    # las.points.y *= conversion
    # las.points.z *= conversion
    # las.write(file_out)


    x = las.points.x * conversion
    y = las.points.y * conversion
    z = las.points.z * conversion
    header = laspy.LasHeader(point_format=6, version="1.4")
    header.offsets = np.array([np.min(x), np.min(y), np.min(z)])
    header.scales = np.array([0.001, 0.001, 0.001])

    las_new = laspy.LasData(header)

    las_new.x = x
    las_new.y = y
    las_new.z = z

    las_new.classification = las.classification
    las_new.intensity = las.intensity
    las_new.return_number = las.return_number
    las_new.number_of_returns = las.number_of_returns

    las_new.write(file_out)
