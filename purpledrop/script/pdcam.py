import click
import cv2
import json
import matplotlib.pyplot as plt

from purpledrop.pdcam.image_registration import find_fiducials, find_grid_transform
from purpledrop.pdcam.plotting import mark_fiducial, plot_template
from purpledrop.electrode_board import Registration, load_board

ELECTRODE_LAYOUT_v3 = [
  [ None, None, None, None, None, None,  None,  None, None, 113, 113],
  [ None, None, None, None, None, 16,  14,  17, 110, 110, 113],
  [13, 18, 12, 19, 111, 112, 115, 108, None, 113, 113],
  [11, 20, 10, 21, 109, 114, 116, 106, None, None, None],
  [ 9, 22,  8, 23, 107, 117, 105, 119, None, 104, 118],
  [ 5, 26,  4, 27,   7,  24,   6,  25, 120, 102, 121],
  [ 3, 28,  2, 29, 103, 101, 122, 100, None, 123, 125],
  [ 1, 30,  0, 31,  99, 124,  98, 127, None, None, None],
  [63, 32, 62, 33,  97, 126,  96,  65, None,  92,  67],
  [61, 34, 60, 35,  95,  64,  94,  93,  66,  90,  69],
  [59, 36, 58, 37,  91,  68,  89,  70, None,  88,  71],
  [57, 38, 56, 39,  87,  72,  86,  73, None, None, None],
  [53, 42, 52, 43,  55,  40,  54,  41,  74,  84,  75],
  [51, 44, 50, 45,  78,  81,  85,  83,  76,  82,  77],
  [46, None, None, None, None,  47, None, None, None, None,  80],
  [49, None, None, None, None,  48, None, None, None, None,  79],
]

# The coordinates of electrodes to solicit user provided control points during
# `measure` command
CONTROL_ELECTRODES_v3 = [(0, 2), (0, 15), (5, 15), (10, 15), (8, 5)]

ELECTRODE_LAYOUT_v4 =  [
    [None, None, None, None, None, None, 28, 98, None, None, None, None, None, None],
    [None, None, None, None, None, None, 27, 99, None, None, None, None, None, None],
    [11, 14, 16, 18, 20, 23, 26, 100, 102, 105, 109, 111, 113, 114],
    [12, 13, 15, 17, 19, 22, 25, 101, 104, 107, 110, 112, 115, 116],
    [5, 6, 7, 4, 3, 21, 24, 103, 108, 126, 125, 122, 123, 124],
    [0, 63, 62, 1, 2, 55, 46, 68, 106, 127, 64, 67, 66, 65],
    [60, 61, 54, 49, 51, 48, 44, 69, 82, 81, 79, 77, 76, 75],
    [53, 50, 47, 45, 42, 41, 43, 87, 86, 85, 84, 83, 80, 78],
    [None, None, None, None, None, None, 40, 88, None, None, None, None, None, None],
    [None, None, None, None, None, None, 39, 89, None, None, None, None, None, None],
    [None, None, None, None, None, None, 38, 90, None, None, None, None, None, None],
]
CONTROL_ELECTRODES_v4 = [(0, 2), (0, 7), (7, 1), (7,10), (13, 2), (13, 7)]

ELECTRODE_LAYOUT_v4_1 = [
    [  1,  2,  3,  4,  5,  6,  7,  8,  9, 10],
    [ 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
    [ 21, 22, 23, 24, 25, 26, 27, 28, 29, 30],
    [ 31, 32, 33, 34, 35, 36, 37, 38, 39, 40],
    [ 41, 42, 43, 44, 45, 46, 47, 48, 49, 50],
    [ 51, 52, 53, 54, 55, 56, 57, 58, 59, 60],
    [ 61, 62, 63, 64, 65, 66, 67, 68, 69, 70],
    [ 71, 72, 73, 74, 75, 76, 77, 78, 79, 80],
    [ 81, 82, 83, 84, 85, 86, 87, 88, 89, 90],
    [ None, None, None, None, 91, 92, None, None, None, None],
    [ None, None, None, None, 93, 94, None, None, None, None],
    [ None, None, None, None, 95, 96, None, None, None, None],
    [ None, None, None, None, 97, 98, None, None, None, None]
]
CONTROL_ELECTRODES_v4_1 = [(0, 0), (0, 8), (9, 8), (9, 0)]

ELECTRODE_LAYOUT_v5 = [
    [ None,  7, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,120, None],
    [ None,  1, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,126, None],
    [ None,  0,  8,  9, 10, 11, 12, 13, 14, 15, 16,111,112,113,114,115,116,117,118,119,127, None],
    [ None, 63, 55, 54, 53, 52, 51, 50, 49, 48, 47, 80, 79, 78, 77, 76, 75, 74, 73, 72, 64, None],
    [ None, 62, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 65, None],
    [ None, 56, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 71, None]
]
CONTROL_ELECTRODES_v5 = [(1, 0), (1, 5), (20, 0), (20, 5)]

@click.group()
def main():
    pass

def load_registration(filepath):
    """Load a registration from a JSON file
     
    If the top level object contains a 'registration' attribute, this will
    be loaded. Othewise, the top-level attribute is assumed to contain the 
    registration data
    """
    with open(filepath, 'r') as f:
        data = json.loads(f.read())
        if 'registration' in data:
            data = data['registration']
        registration = Registration.from_dict(data)

@main.command()
@click.option('--registration', required=False, help="Provide a fiducial registration file to override board definition")
@click.option('--board', required=False, help="Force usage of a particular electrode board (overrides auto detection)")
@click.option('--flip', is_flag=True, default=False)
def server(registration, board, flip):
    """Runs camera server process used to provide gateway to captured images
    and fiducial locations.

    Serves HTTP API on port 5000, which can be used by `pdserver`.
    """
    from purpledrop.pdcam.server import create_app

    board_name = board
    if board_name is not None:
        board = load_board(board_name)
        if board is None:
            raise ValueError(f"No board found with name {board_name}")

    if registration is not None:
        registration = load_registration(registration)
    elif board is not None:
        registration = board.registration

    if board is None:
        layout = None
    else:
        layout = board.layout

    app = create_app(registration, layout, flip)
    app.run(host="0.0.0.0")

@main.command()
@click.option('--reference')
@click.argument('imagefile')
def overlay(reference, imagefile):
    img = cv2.cvtColor(cv2.imread(imagefile), cv2.COLOR_BGR2RGB)

    with open(reference) as f:
        refdata = json.loads(f.read())
    ref = GridReference.from_dict(refdata)
    transform, fiducials = find_grid_transform(ref, img)

    if transform is None:
        print("Failed to find a transform, displaying only QR codes found")

    for f in fiducials:
        mark_fiducial(img, f.corners)
    
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.imshow(img)
    if transform is not None:
        plot_template(ax, ELECTRODE_LAYOUT, transform=transform)

    plt.show()


@main.command()
@click.argument('imagefile')
@click.argument('outfile')
@click.option('--v4', is_flag=True, default=False)
@click.option('--v4_1', is_flag=True, default=False)
@click.option('--v5', is_flag=True, default=False)
@click.option('--layout', required=False, help="JSON file to read board layout from")
@click.option('--point', 'points', multiple=True, help="Control points in grid coordinates: 'x, y'")
@click.option('-v', '--verbose', is_flag=True, help='verbose output')
def measure(imagefile, outfile, v4, v4_1, v5, layout, points, verbose):
    """Launch UI to make calibration measurements from an image of an
    electrode board.
    """

    # TODO: Instead of hardcoding the layouts, load the electrode layout from
    # board definition files (e.g. with --board option), and auto compute a 
    # good set of control electrodes
    img = cv2.cvtColor(cv2.imread(imagefile), cv2.COLOR_BGR2RGB)

    def read_input_tuple(x):
        try:
            return tuple(int(n) for n in x.split(','))
        except ValueError as ex:
            raise ValueError(f"Failed parsing point {x}: {ex}")

    fiducials = find_fiducials(img)
    for f in fiducials:
        print(f)
        mark_fiducial(img, f.corners)
    
    electrode_layout = ELECTRODE_LAYOUT_v3
    control_electrodes = CONTROL_ELECTRODES_v3
    pitch = 1.0
    grid_origin = (0.0, 0.0)
    if layout:
        if points is None or len(points) < 4:
            raise ValueError("If providing a custom layout, you must provide at least 4 calibration points with --point")
        board = load_board(layout)
        electrode_layout = board.layout.grids[0]['pins']
        control_electrodes = [read_input_tuple(p) for p in points]
        pitch = board.layout.grids[0]['pitch']
        origin = board.layout.grids[0]['origin']
    if v4:
        electrode_layout = ELECTRODE_LAYOUT_v4
        control_electrodes = CONTROL_ELECTRODES_v4
    elif v4_1:
        electrode_layout = ELECTRODE_LAYOUT_v4_1
        control_electrodes = CONTROL_ELECTRODES_v4_1
    elif v5: 
        electrode_layout = ELECTRODE_LAYOUT_v5
        control_electrodes = CONTROL_ELECTRODES_v5


    if verbose:
        print(f"Using control points: {control_electrodes}")
        print(f"Using layout: {electrode_layout}")

    alignment_electrodes = control_electrodes
    fig = plt.figure()
    gs = fig.add_gridspec(4, 4)
    
    ax1 = fig.add_subplot(gs[:, :-1])
    plt.imshow(img)
    ax1.set_title('Click the top-left corner of the indicated electrode')

    ax2 = fig.add_subplot(gs[:1, -1])
    plot_template(ax2, electrode_layout, [alignment_electrodes[0]])
    ax2.invert_yaxis()
    
    alignment_points = []
    def onclick(event):
        ix, iy = event.xdata, event.ydata

        alignment_points.append((ix, iy))
        
        if len(alignment_points) == len(alignment_electrodes):
            fig.canvas.mpl_disconnect(cid)
            plt.close(1)
        else:
            ax2.clear()
            plot_template(ax2, electrode_layout, [alignment_electrodes[len(alignment_points)]])
            ax2.invert_yaxis()
            
            ax1.plot(alignment_points[-1][0], alignment_points[-1][1], 'ro')
            fig.canvas.draw()
    
    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    fig.tight_layout()
    plt.ion()
    plt.show(block=True)

    if len(alignment_points) != len(alignment_electrodes):
        print("Figure closed without collecting enough control points. No file will be saved")
        return

    for(n, p) in zip(alignment_electrodes, alignment_points):
        print("%s: (%d, %d)\n" % (n, p[0], p[1]))
    
    def map_fiducial(f):
        def to_tuple(point):
            return (point[0], point[1])
        return [to_tuple(p) for p in f.corners]

    data = {
        'fiducials': [f.to_dict() for f in fiducials],
        'control_points': [ {"grid": (n[0]*pitch + origin[0], n[1]*pitch + origin[1]), "image": p} for n,p in zip(alignment_electrodes, alignment_points) ]
    }

    print("Storing reference data to %s" % outfile)
    with open(outfile, 'w') as f:
        f.write(json.dumps(data))