# -*- coding: utf-8 -*-
from .constants import BASEDIR
import pytest
from maser.data import Data
from maser.data.rpw import RpwLfrSurvBp1
from astropy.time import Time
from astropy.units import Quantity, Unit
import xarray
from .fixtures import skip_if_spacepy_not_available

TEST_FILES = {
    "solo_L2_rpw-lfr-surv-bp1": [
        BASEDIR / "solo" / "rpw" / "solo_L2_rpw-lfr-surv-bp1_20201227_V02.cdf"
    ],
}

# create a decorator to test each file in the list
for_each_test_file = pytest.mark.parametrize(
    "filepath", TEST_FILES["solo_L2_rpw-lfr-surv-bp1"]
)


@pytest.mark.test_data_required
@skip_if_spacepy_not_available
@for_each_test_file
def test_rpw_lfr_surv_bp1_dataset(filepath):
    data = Data(filepath=filepath)
    assert isinstance(data, RpwLfrSurvBp1)


@pytest.mark.test_data_required
@skip_if_spacepy_not_available
@for_each_test_file
def test_rpw_lfr_surv_bp1_dataset__times(filepath):
    with Data(filepath=filepath) as data:
        assert list(data.times.keys()) == ["N_F2", "B_F1", "N_F1", "B_F0", "N_F0"]
        assert isinstance(data.times["B_F0"], Time)
        assert len(data.times["B_F0"]) == 86380
        assert data.times["B_F0"][0] == Time("2020-12-27 00:00:45.209203")
        assert data.times["B_F0"][-1] == Time("2020-12-28 00:00:44.618985")


@pytest.mark.test_data_required
@skip_if_spacepy_not_available
@for_each_test_file
def test_rpw_lfr_surv_bp1_datase__frequencies(filepath):
    with Data(filepath=filepath) as data:
        assert list(data.frequencies.keys()) == ["N_F2", "B_F1", "N_F1", "B_F0", "N_F0"]
        assert isinstance(data.frequencies["B_F0"], Quantity)
        assert len(data.frequencies["B_F0"]) == 22
        assert data.frequencies["B_F0"][0].to(Unit("Hz")).value == pytest.approx(1776)
        assert data.frequencies["B_F0"][-1].to(Unit("Hz")).value == pytest.approx(9840)


@pytest.mark.test_data_required
@skip_if_spacepy_not_available
@for_each_test_file
def test_rpw_lfr_surv_bp1_data__sweeps(filepath):
    with Data(filepath=filepath) as data:
        # get only the first sweep
        sweep = next(data.sweeps)

        # check the sweep content
        assert len(sweep) == 3
        assert isinstance(sweep[0], dict)
        assert isinstance(sweep[1], Time)
        assert isinstance(sweep[2], Quantity)
        assert list(sweep[0].keys()) == ["PB", "PE", "DOP", "ELLIP", "SX_REA"]
        assert len(sweep[2]) == 26


@pytest.mark.test_data_required
@skip_if_spacepy_not_available
@for_each_test_file
def test_rpw_lfr_surv_bp1_data__as_xarray(filepath):
    with Data(filepath=filepath) as data:
        # get only the first sweep
        datasets = data.as_xarray()

        expected_keys = ["PB", "PE", "DOP", "ELLIP", "SX_REA"]
        expected_frequency_ranges = ["B_F1", "B_F0"]

        # check the sweep content
        assert len(expected_keys) == 5
        assert sorted(list(datasets.keys())) == sorted(expected_keys)
        assert list(datasets[expected_keys[0]].keys()) == expected_frequency_ranges

        test_array = datasets[expected_keys[0]][expected_frequency_ranges[0]]
        assert isinstance(test_array, xarray.DataArray)
        assert test_array.coords["frequency"][0] == pytest.approx(120)
        assert test_array.attrs["units"] == "nT^2/Hz"
        assert test_array.data[0][0] == pytest.approx(5.73584540e-08)
