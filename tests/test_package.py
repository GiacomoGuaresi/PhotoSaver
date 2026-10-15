import re

import photosaver


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", photosaver.__version__)
