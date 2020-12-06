"""Tests for the purpledrop.electrode_board module
"""

import purpledrop.electrode_board as electrode_board

def test_load_misl_v4_1():
    """Test loading `boards/misl_v4.1.json` definition
    """
    board = electrode_board.load_board('misl_v4.1')
    assert isinstance(board, electrode_board.Board)
    assert isinstance(board.layout, electrode_board.Layout)
    assert isinstance(board.registration, electrode_board.Registration)

    assert len(board.registration.fiducials) == 3
    assert len(board.registration.control_points) == 4

def test_load_misl_v4():
    """Test loading 'boards/misl_v4.json' definition
    """
    board = electrode_board.load_board('misl_v4')
    assert isinstance(board, electrode_board.Board)    
    assert isinstance(board.layout, electrode_board.Layout)
    assert board.registration is None

def test_load_misl_v5():
    """Test loading `board/misl_v5.json` definition
    """
    board = electrode_board.load_board('misl_v5')
    assert isinstance(board, electrode_board.Board)    
    assert isinstance(board.layout, electrode_board.Layout)
    assert board.registration is None

def test_list_boards():
    """Test list_boards method
    
    Should return *at least* the boards defined in the package. It may return
    more, because there may be local configuration on the test machine.
    """
    boards = electrode_board.list_boards()
    assert len(boards) >= 3
    assert 'misl_v4' in boards
    assert 'misl_v4.1' in boards
    assert 'misl_v5' in boards
