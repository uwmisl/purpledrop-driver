"""Utilities for locating the electrode grid in an image
"""
import cv2
import functools
import logging
import itertools
import numpy as np
import apriltag
from typing import Dict, List, Optional, Tuple
from purpledrop.electrode_board import Registration, Fiducial, load_board, list_boards

logger = logging.getLogger()

def sort_fiducials(qr_a, qr_b):
    """Sort 2d fiducial markers in a consistent ordering based on their relative positions. 

    In general, when we find fiducials in an image, we don't expect them to be 
    returned in a consistent order. Additionally, the image coordinate may be 
    rotated from image to image. Here we match fiducials by trying all permutations
    of matches and taking the best fit. We assume that the fiducials are all
    aligned in similar directions; this is a constraint on fiducials placement.
    """

    qr_a = np.array(qr_a)
    qr_b = np.array(qr_b)

    # Get unit vectors defining our common coordinate system in each image
    ux_a = np.array([0.0, 0.0])
    ux_b = np.array([0.0, 0.0])
    for qr in qr_a:
        ux_a += qr[1] - qr[0]
    for qr in qr_b:
        ux_b += qr[1] - qr[0]
    ux_a /= np.linalg.norm(ux_a)
    ux_b /= np.linalg.norm(ux_b)

    def displacements(qrcodes, ux):
        uy = np.array([ux[1], ux[0]])
        #uy_b = np.array([ux_b[1], ux_b[0]])
        displacements = []
        for i in range(1, len(qrcodes)):
            d = qrcodes[i][0] - qrcodes[0][0]
            d2 = np.array([np.dot(ux, d), np.dot(uy, d)])
            displacements.append(d2)
        return np.array(displacements)

    best_error = float("inf")
    best_permutation = []
    d_a = displacements(qr_a, ux_a)
    for perm in itertools.permutations(qr_b):
        d_perm = displacements(perm, ux_b)
        error = np.sum(np.square(d_perm - d_a))
        if error < best_error:
            best_error = error
            best_permutation = perm

    return qr_a.tolist(), [p.tolist() for p in list(best_permutation)]

def enhance(image):
    image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, blockSize=55, C=5)
    return image

def find_fiducials(image):
    """Find april tag fiducials in an image and return them"

    Args:
        image: An image in numpy array

    Returns:
        A list of purpledrop.electrodeboard.Fiducial objects
    """
    detector = apriltag.Detector()
    result = detector.detect(enhance(image))

    fiducials = [
        Fiducial(tag.corners.tolist(), tag.tag_id) 
        for tag in result]
    return fiducials

@functools.lru_cache(maxsize=256)
def find_reference_from_fiducials(search_labels: Tuple[int]) -> Optional[Registration]:
    """Look for a board definition that matches the fiducial tags found

    A matching board definition must include all of the fiducial labels, and it
    must be unique. It's possible for multiple boards to match, in which case
    no reference is returned. Each of the provided fiducials must have a unique
    label, or no board can be matched.

    This function is memoized to prevent searching boards on repeated image.
    This means that the process must be restarted if the board definition files
    are changed for the new data to take effect.

    Args:
        search_labels: Tuple of integer labels for the fiducials to lookup
    Returns: 
        A Registration object if one is found, or None otherwise
    """
    board_names = list_boards()
    matched_boards = []
    for l in search_labels:
        if search_labels.count(l) != 1:
            logger.warn(f"Cannot lookup reference board because of repeated tag in {search_labels}")
            return None
            
    for name in board_names:
        board = load_board(name)
        if board is not None and board.registration is not None:
            board_labels = [f.label for f in board.registration.fiducials]
            if all([l in board_labels for l in search_labels]):
                matched_boards.append(board)
    
    if len(matched_boards) == 1:
        return matched_boards[0].registration
    if len(matched_boards) > 1:
        logger.warn(f"Found multiple boards matching fiducials {search_labels}")
    else:
        logger.warn(f"Found no matching board for fiducials {search_labels}")
    return None

@functools.lru_cache(maxsize=256)
def sort_fiducials_by_label(ref: Tuple[Fiducial], search: Tuple[Fiducial]):
    search_labels = [f.label for f in search]
    ref_labels = [f.label for f in ref]
    ref_return = []
    search_return = []
    for f in search:
        if search_labels.count(f.label) != 1:
            return None, None
        if ref_labels.count(f.label) != 1:
            return None, None
        for r in ref:
            if r.label == f.label:
                ref_return.append(r)
                break
        search_return.append(f)
    
    return ref_return, search_return

def find_grid_transform(image: np.array, reference: Optional[Registration]=None):
    """Provide transform to move from electrode grid coordinates to pixel 
    coordinates in a new image. 

    Args:
        image (numpy array): An image of the reference board with all fiducials visible
        reference: Control points and fiducials from a reference/calibration image
        of the electrode board. If not provided, an attempt will be made to 
        look it up in the database of boards.
    """

    fiducials = find_fiducials(image)

    if len(fiducials) < 2:
        logger.warn("Found %d fiducials, needed 2", len(fiducials))
        return None, fiducials

    if reference is None:
        reference = find_reference_from_fiducials(tuple([f.label for f in fiducials]))
    
    if reference is None:
        logger.warn(f"No reference provided, and no database board definition found for fiducials {[f.label for f in fiducials]}")
        return None, fiducials

    # If both the reference and the detected fiducials have unique labels, 
    # match by label. Otherwise, attempt to match by positions. The matching
    # by position only works when all fiducials are detected, but this is 
    # simply because a better algorithm hasn't been implemented. As long as the
    # fiducial locations are not co-linear, it is possible to support a subset 
    # of fiducials.
    
    sorted_ref, sorted_dst = sort_fiducials_by_label(tuple(reference.fiducials), tuple(fiducials))
    if sorted_ref is None:
        refqr, dstqr = sort_fiducials([f.corners for f in reference.fiducials], [f.corners for f in fiducials])
    else:
        refqr = [f.corners for f in sorted_ref]
        dstqr = [f.corners for f in sorted_dst]

    def flatten(l):
        return [item for sublist in l for item in sublist]

    # Get transform from grid to reference image coordinates
    src_points = np.array([cp.grid for cp in reference.control_points])
    dst_points = np.array([cp.image for cp in reference.control_points])
    H0, _ = cv2.findHomography(src_points, dst_points)

    # Get transform from reference image to current image
    src_points = np.array([flatten(refqr)])
    dst_points = np.array([flatten(dstqr)])
    H1, _ = cv2.findHomography(src_points, dst_points)

    xform = np.dot(H1, H0)
    
    return xform, fiducials
