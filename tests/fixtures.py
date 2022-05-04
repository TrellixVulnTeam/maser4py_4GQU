# -*- coding: utf-8 -*-
from pathlib import Path
import json
import pytest
import requests

# try importing nenupy
try:
    import nenupy
except ImportError:
    # if nenupy is not available, skip the corresponding tests
    nenupy = None


__all__ = ["load_test_data"]

# remote test data url
DATA_REPO_URL = "http://maser.obspm.fr/data/maser4py/tests/data"

# directory containing local test data
ROOT_DATA_DIRECTORY = Path(__file__).parent / "data"

# test data sample
TEST_COLLECTIONS_FILE = ROOT_DATA_DIRECTORY / "collections.json"
with open(TEST_COLLECTIONS_FILE, "r") as f:
    DATA_FILES = json.load(f)


def download_file(url: str, filepath: Path, chunk_size=8192):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
    return filepath


def test_filepaths():
    filepaths = []
    for database_name in DATA_FILES.keys():
        cur_db_name = Path(ROOT_DATA_DIRECTORY) / database_name
        for dataset_name in DATA_FILES[database_name].keys():
            cur_dir_name = cur_db_name / dataset_name
            for file_data in DATA_FILES[database_name][dataset_name]:
                file_name, file_dataset = file_data[0:2]
                if file_dataset == "srn_nenufar_bst":

                    pytest_param = pytest.param(
                        cur_dir_name / file_name,
                        file_dataset,
                        marks=pytest.mark.skipif(
                            nenupy is None,
                            reason="the nenupy package is required to run nenufar dataset tests",
                        ),
                    )
                else:
                    pytest_param = (cur_dir_name / file_name, file_dataset)

                filepaths.append(pytest_param)
    return filepaths


def download_data_sample(database_name: str, reload: bool = False):
    try:
        files = DATA_FILES[database_name]
    except KeyError as err:
        raise KeyError(
            f"database '{database_name}' is not in the test data sample"
        ) from err

    # set up local directory variable, and create directory if necessary
    test_data_path = Path(ROOT_DATA_DIRECTORY) / database_name
    test_data_url_path = f"{DATA_REPO_URL}/{database_name}"
    test_data_path.mkdir(exist_ok=True)

    # loop on subdirs and fix directory separator, depending on local platform:
    for cur_dir, file_items in files.items():

        # local path of current sub-directory (fix path separator for non unix os)
        cur_local_path = test_data_path / Path(cur_dir)

        # URL of current sub-directory
        cur_url_path = f"{test_data_url_path}/{cur_dir}"

        # create cur_local_path if it doesn't exist:
        if not cur_local_path.exists():
            cur_local_path.mkdir(parents=True)

        # loop on files to be downloaded
        for cur_file in file_items:

            # local path to file
            cur_file_path = cur_local_path / cur_file[0]

            # download is file doesn't exist or reload=True
            if not cur_file_path.exists() or reload:
                download_url = f"{cur_url_path}/{cur_file[0]}"
                print(f"Trying to download URL: {download_url}")
                print(f"into: {cur_file_path}")
                download_file(download_url, cur_file_path)
                print("Done.\n")


def check_pytest_marker(test_item_list, *, marker):
    return any([item.get_closest_marker(marker) for item in test_item_list])


@pytest.fixture(scope="session", autouse=True)
def load_test_data(request, pytestconfig):
    """Load test data for Maser4py.maser.data tests suite

    Use 'pytest -m "not test_data_required"' to skip tests that require test data (and to skip auto download).

    Args:
        database_name (str, optional): name of the database to be tested (cdpp, kronos, pds...). Defaults to 'all'.
        reload (bool, optional): set to True to reload data. Defaults to False.
    """
    # skip download if no tests are marked with the 'test_data_required' marker
    if not check_pytest_marker(request.session.items, marker="test_data_required"):
        print("Skipping test data download")
        return

    # loop on test_data_files first level entries
    for database in DATA_FILES:
        download_data_sample(database, reload=False)
