# -*- coding: utf-8 -*-
from maser.data.base import CdfData

from astropy.time import Time
from astropy.units import Unit
from maser.data.base.sweeps import Sweeps
import matplotlib.colorbar as cbar
from matplotlib import colors
from matplotlib import pyplot as plt


class RpwLfrSurvBp1Sweeps(Sweeps):
    @property
    def generator(self):
        """
        For each time, yield a frequency range and a dictionary with the following keys:
        - PB: power spectrum of the magnetic field (nT^2/Hz),
        - PE: the power spectrum of the electric field (V^2/Hz),
        - DOP: the degree of polarization of the waves (unitless),
        - ELLIP: the wave ellipticity (unitless),
        - SX_REA: the real part of the radial component of the Poynting flux (V nT/Hn, QF=1),

        """
        for frequency_band in self.data_reference.frequency_band_labels:
            for time, pb, pe, dop, ellip, sx_rea in zip(
                self.data_reference.times[frequency_band],
                self.file[f"PB_{frequency_band}"][...],
                self.file[f"PE_{frequency_band}"][...],
                self.file[f"DOP_{frequency_band}"][...],
                self.file[f"ELLIP_{frequency_band}"][...],
                self.file[f"SX_REA_{frequency_band}"][...],
            ):
                yield (
                    {"PB": pb, "PE": pe, "DOP": dop, "ELLIP": ellip, "SX_REA": sx_rea},
                    Time(time),
                    self.data_reference.frequencies[frequency_band],
                )


class RpwLfrSurvBp1(CdfData, dataset="solo_L2_rpw-lfr-surv-bp1"):
    _iter_sweep_class = RpwLfrSurvBp1Sweeps

    # keys used to loop over F0, F1, F2 frequency ranges and Burst/Normal modes
    frequency_band_labels = ["N_F2", "B_F1", "N_F1", "B_F0", "N_F0"]

    @property
    def frequencies(self):
        if self._frequencies is None:

            self._frequencies = {}

            with self.open(self.filepath) as cdf_file:
                for frequency_band in self.frequency_band_labels:
                    # if units are not specified, assume Hz
                    units = cdf_file[frequency_band].attrs["UNITS"].strip() or "Hz"
                    freq = cdf_file[frequency_band][...] * Unit(units)
                    self._frequencies[frequency_band] = freq

        return self._frequencies

    @property
    def times(self):
        if self._times is None:
            with self.open(self.filepath) as cdf_file:
                self._times = {}
                for frequency_band in self.frequency_band_labels:
                    self._times[frequency_band] = Time(
                        cdf_file[f"Epoch_{frequency_band}"][...]
                    )

        return self._times

    def as_xarray(self):
        import xarray

        dataset = {
            "PE": {},
            "PB": {},
            "DOP": {},
            "ELLIP": {},
            "SX_REA": {},
        }

        default_units = {"PB": "nT^2/Hz"}

        for frequency_band in self.frequency_band_labels:
            frequencies = self.file[frequency_band][...]
            if len(frequencies) == 0:
                continue
            times = self.file[f"Epoch_{frequency_band}"][...]

            # force lower keys for frequency and time attributes
            time_attrs = {
                k.lower(): v
                for k, v in self.file[f"Epoch_{frequency_band}"].attrs.items()
            }

            frequency_attrs = {
                k.lower(): v for k, v in self.file[frequency_band].attrs.items()
            }
            if not frequency_attrs["units"].strip():
                frequency_attrs["units"] = "Hz"

            for dataset_key in dataset:
                values = self.file[f"{dataset_key}_{frequency_band}"][...]

                attrs = {
                    k.lower(): v
                    for k, v in self.file[
                        f"{dataset_key}_{frequency_band}"
                    ].attrs.items()
                }

                # if units are not defined, use the default ones
                if not attrs["units"].strip():
                    attrs["units"] = default_units.get(dataset_key, "")

                dataset[dataset_key][frequency_band] = xarray.DataArray(
                    values,
                    coords=[
                        ("time", times, time_attrs),
                        ("frequency", frequencies, frequency_attrs),
                    ],
                    attrs=attrs,
                    name=f"{dataset_key}_{frequency_band}",
                )

        return dataset

    def plot_lfr_bp1_field(
        self, *, ax, cbar_ax=None, field, max_gap_in_sec=60, **kwargs
    ):
        """Plot a field of the LFR BP1 data using xarray datasets and matplotlib"""
        import numpy

        dataset = self.as_xarray()

        # prepare kwargs for each dataset/plot
        default_kwargs = {
            "PB": {"norm": colors.LogNorm()},
            "PE": {"norm": colors.LogNorm()},
            "DOP": {"vmin": 0, "vmax": 1},
            "ELLIP": {"vmin": 0, "vmax": 1},
            "SX_REA": {},
        }

        merge_kwargs = {**default_kwargs[field], **kwargs}

        # create a new norm object to display the colorbar in log scale
        if "norm" in merge_kwargs and merge_kwargs["norm"] == "log":
            merge_kwargs["norm"] = colors.LogNorm()

        # create the associated colorbar
        if cbar_ax is None:
            cbar_ax, kw = cbar.make_axes(ax)

        # compute vmin and vmax by taking the min and max of each dataset for each frequency range
        min_value = min([dataset[field][band].min() for band in dataset[field]])
        max_value = max([dataset[field][band].max() for band in dataset[field]])
        merge_kwargs.setdefault("vmin", min_value)
        merge_kwargs.setdefault("vmax", max_value)

        meshes = []

        # plot the data
        for band in dataset[field]:
            data_array = dataset[field][band]

            # handle data gaps by grouping data separated by more than `max_gap_in_sec`

            # use `cumsum` to index groups of values separated by a gap
            data_gaps_groups = (
                (
                    data_array.coords["time"].diff(dim="time")
                    > numpy.timedelta64(max_gap_in_sec, "s")
                )
                .cumsum(axis=0)
                .values
            )

            # and prepend a leading 0 to match the length of the dataset
            data_gaps_groups = numpy.concatenate([[0], data_gaps_groups])

            # add a new derived coordinate to the data array
            data_array = data_array.assign_coords(gaps=("time", data_gaps_groups))

            # and plot a new mesh for each group of data
            for gap, data in data_array.groupby("gaps"):

                # if there is only one value, skip this group
                if len(data.coords["time"]) < 2:
                    continue

                mesh = data.plot.pcolormesh(
                    ax=ax,
                    x="time",
                    y="frequency",
                    yscale="log",
                    add_colorbar=True,
                    **merge_kwargs,
                    cbar_ax=cbar_ax,
                )

                meshes.append(mesh)

        # set the color bar title
        if data_array.attrs.get("units"):
            cbar_label = f'{field} [${data_array.attrs["units"]}$]'
        else:
            cbar_label = field
        cbar_ax.set_ylabel(cbar_label)

        return {
            "ax": ax,
            "cbar_ax": cbar_ax,
            "vmin": merge_kwargs["vmin"],
            "vmax": merge_kwargs["vmax"],
            "meshes": meshes,
        }

    def plot_lfr_bp1_data(self, max_gap_in_sec=60):
        """Plot the LFR BP1 data using xarray datasets and matplotlib

        Args:
            datasets (dict): a dict containing LFR BP1 data as xarray datasets

        Returns:
            tuple: matplotlib figure and axes
        """
        dataset = self.as_xarray()

        # create figure and axes
        fig, axes = plt.subplots(len(dataset), 1, sharex=True)
        # loop over datasets
        for ax_idx, field in enumerate(dataset):

            # select the ax to plot on
            ax = axes[ax_idx]

            # create the associated colorbar
            cbar_ax, kw = cbar.make_axes(ax)

            self.plot_lfr_bp1_field(
                ax=ax, cbar_ax=cbar_ax, field=field, max_gap_in_sec=max_gap_in_sec
            )
        return fig, axes


if __name__ == "__main__":
    from maser.data import Data
    from pathlib import Path

    data_path = Path(__file__).parents[5] / "tests" / "data" / "solo" / "rpw"

    print(data_path)

    # lfr_file = "solo_L2_rpw-lfr-surv-bp1_20211127_V02.cdf"
    lfr_file = "solo_L2_rpw-lfr-surv-bp1_20220118_V02.cdf"
    lfr_filepath = data_path / lfr_file

    lfr_data = Data(filepath=lfr_filepath)
    # fig, ax = plt.subplots()
    lfr_data.plot_lfr_bp1_data()
    plt.show()
