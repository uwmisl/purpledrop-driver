import os
import cv2
import numpy as np
from numpy.testing import assert_allclose

from purpledrop.pdcam.image_registration import find_grid_transform
from purpledrop.electrode_board import load_board


def get_data_file(filename):
    path = os.path.join(os.path.dirname(__file__), "data", filename)
    return path

def load_image(filename):
    raw = cv2.imread(get_data_file(filename))
    if raw is None:
        raise RuntimeError(f"Failed to load test image {filename}")
    return cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)

# The expected transform for image 'electrode_board_v4.1_sample1.jpg'
TRANSFORM_V4_1_SAMPLE1 = [
    [ 2.83835912e+01, -5.22110003e-01,  3.83931818e+02],
    [-9.26488213e-01,  2.92632645e+01,  2.38247148e+02],
    [-2.55359798e-03, -8.26237402e-04,  9.82660412e-01],
]

def test_find_grid_transform_v4_1_sample1():
    """Load a sample image and try to find the registration
    """
    img = load_image('electrode_board_v4.1_sample1.jpg')
    board = load_board('misl_v4.1')
    reference = board.registration

    transform, fiducials = find_grid_transform(img, reference)

    print(f"tranform: {transform}")
    print(f"fiducials: {fiducials}")
    # There should be 3 fiducials, and they should be labeled with integers 
    # 4, 5, 6 in no particular order
    assert len(fiducials) == 3
    assert sorted([f.label for f in fiducials]) == [4, 5, 6]

    assert np.allclose(TRANSFORM_V4_1_SAMPLE1, transform)

def test_find_grid_transform_v4_1_sample2():
    """Load a sample image and try to find the registration
    
    This sample is the same as sample1, but one of the fiducials
    is covered. We should still be able to find a transform with just two
    fiducials detected.
    """
    img = load_image('electrode_board_v4.1_sample2.jpg')
    board = load_board('misl_v4.1')
    reference = board.registration

    transform, fiducials = find_grid_transform(img, reference)

    print(f"tranform: {transform}")
    print(f"fiducials: {fiducials}")
    # Only 2 fiducials are visible, 5 and 6, and are returned in no particular 
    # order
    assert len(fiducials) == 2
    assert sorted([f.label for f in fiducials]) == [5, 6]
    
    # Allow some tolerance in transform; using a different set of fiducials will 
    # result in a similar but different result
    assert transform is not None
    assert_allclose(TRANSFORM_V4_1_SAMPLE1, transform, rtol=0.1, atol=0.6)

    