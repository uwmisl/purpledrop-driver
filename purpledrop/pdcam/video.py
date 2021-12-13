import cv2
import numpy as np
import threading
import time

from picamera import PiCamera

from purpledrop.pdcam.image_registration import find_grid_transform
from purpledrop.pdcam.plotting import mark_fiducial, mark_template

class AsyncGridLocate(object):
    def __init__(self, grid_registration=None, callback=None, timeout_frames=3):
        """A background thread for processing images to find fiducials, and
        transform to map pixel coordinates to electrode board grid coordinates

        Args:
            grid_registration: Optional `Registration` object. If provided,
            this overrides any registration found in the electrode board
            database
            callback: Function, taking two args (transform, fiducials) to be
            called on each processed image
        """
        self.callback = callback
        self.grid_registration = grid_registration
        self.timeout_frames = timeout_frames
        self.fail_count = 0
        self.pending_image = None
        self.latest_result = (None, [])
        self.cv = threading.Condition()
        self.thread = threading.Thread(target=self.thread_entry)
        self.thread.daemon = True
        self.thread.start()

    def push(self, image):
        """Push a new image to be processed

        Images aren't queued. If you push a new image before processing has
        begun on the previous image, the previous image will be dropped.
        """
        with self.cv:
            self.pending_image = image
            self.cv.notify()

    def latest(self):
        """Return latest completed results
        """
        with self.cv:
            transform, fiducials = self.latest_result

        return transform, fiducials

    def thread_entry(self):
        while True:
            with self.cv:
                self.cv.wait_for(lambda: self.pending_image is not None)
                img = self.pending_image
                self.pending_image = None

            # Now we've got the image, and cleared pending image,
            # we can release the lock and do the processing
            transform, fiducials = find_grid_transform(img, self.grid_registration)

            with self.cv:
                if transform is not None:
                    self.fail_count = 0
                    self.latest_result = (transform, fiducials)
                else:
                    self.fail_count += 1
                    if self.fail_count > self.timeout_frames:
                        self.latest_result = (transform, fiducials)

            if self.callback is not None:
                self.callback(transform, fiducials)


class Video(object):
    """Video capture process

    Launches background threads to continuously capture frames from raspberry PI
    camera (MMAL API) and process them to locate april tag fiducials
    """

    WIDTH = 1024
    HEIGHT = 768
    NBUFFER = 3
    PROCESS_PERIOD = 0.5
    def __init__(self, grid_registration, grid_layout, flip=False):
        self.frame_number = 0
        self.grid_layout = grid_layout
        self.frames = [np.empty((self.WIDTH * self.HEIGHT * 3,), dtype=np.uint8) for _ in range(self.NBUFFER)]
        self.frame_locks = [threading.RLock() for _ in range(self.NBUFFER)]
        self.lock = threading.RLock()
        self.frame_cv = threading.Condition(self.lock)
        self.active_buffer = 0
        self.last_process_time = 0.0
        self.flip = flip

        self.grid_finder = AsyncGridLocate(grid_registration)
        self.capture_thread = threading.Thread(target=self.capture_thread_entry)
        self.capture_thread.daemon = True
        self.capture_thread.start()

    def capture_thread_entry(self):
        print("Running capture thread")
        with PiCamera() as camera:
            camera.resolution = (self.WIDTH, self.HEIGHT)
            camera.framerate = 30
            camera.iso = 60
            camera.start_preview()

            time.sleep(2)
            gains = camera.awb_gains
            camera.awb_mode = 'off'
            camera.awb_gains = gains
            # print(f"AWB Gains: {gains} {camera.awb_gains}")
            # print(f"ISO: {camera.iso}")
            # print(f"exposure: {camera.shutter_speed}")
            while True:
                next_buffer = (self.active_buffer + 1) % self.NBUFFER
                with self.frame_locks[next_buffer]:
                    camera.capture(self.frames[next_buffer], 'bgr', use_video_port=True)
                    self.frames[next_buffer] = self.frames[next_buffer].reshape((self.HEIGHT, self.WIDTH, 3))
                    cur_time = time.monotonic()
                    if cur_time - self.last_process_time > self.PROCESS_PERIOD:
                        self.last_process_time = cur_time
                        self.grid_finder.push(self.get_buffer(next_buffer).copy())
                with self.frame_cv:
                    self.active_buffer = next_buffer
                    self.frame_number += 1
                    self.frame_cv.notify_all()

    def latest_transform(self):
        """Get the latest transform solution

        Transform is a 3x3 numpy array representing a homography.
        It may be None, if no transform is found.
        """
        transform, qrinfo = self.grid_finder.latest()

        # Convert from the decoded QR objects into list of lists of corners
        qr_corners = [[tuple(p) for p in qr.corners] for qr in qrinfo]
        return transform, qr_corners

    def latest_normalized_transform(self):
        """Get the latest transform solution normalized by image size

        Transform is a 3x3 numpy array representing a homography.
        It may be None, if no transform is found.
        """
        transform = self.latest_transform()
        if transform is None:
            return None

        scale = np.zeros((3, 3), dtype=np.float)
        scale[0, 0] = 1. / self.WIDTH
        scale[1, 1] = 1. / self.HEIGHT
        scale[2, 2] = 1.
        return np.dot(transform, scale)

    def markup(self, image):
        """Make a copy of image with fiducial and electrodes overlayed
        """
        # Make a copy so we don't modify the original np array
        image = image.copy()
        transform, fiducials = self.grid_finder.latest()
        for f in fiducials:
            mark_fiducial(image, f.corners)

        if transform is not None and self.grid_layout is not None:
            mark_template(image, self.grid_layout, transform)

        return image

    def get_buffer(self, index):
        image = self.frames[index]
        if self.flip:
            image = np.flip(image, axis=(0,1))
        return image

    def latest_jpeg(self, min_frame_num=0, markup=False):
        """Get the latest capture as a JPEG

        min_frame_num can be used for sequential calls to prevent receiving the
        same frame twice.
        """
        if min_frame_num is None:
            min_frame_num = 0
        # Hold the global lock just long enough to read self.active_buffer and get the frame lock
        self.frame_cv.acquire()
        self.frame_cv.wait_for(lambda: self.frame_number >= min_frame_num)
        frame_num = self.frame_number
        with self.frame_locks[self.active_buffer]:
            self.frame_cv.release()
            if markup:
                image = self.markup(self.get_buffer(self.active_buffer))
            else:
                image = self.get_buffer(self.active_buffer)
            (flag, encoded_image) = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not flag:
                print("Error encoding jpeg")

        return bytearray(encoded_image), frame_num

    def mjpeg_frame_generator(self, markup=False):
        """Return a generator which will yield JPEG encoded frames as they become available
        Bytes are preceded by a `--frame` separator, and a content header,
        is included so it can be returned as part of a HTTP multi-part response.
        """
        last_fn = 0
        while True:
            data = None
            with self.frame_cv:
                if self.frame_number > last_fn:
                    last_fn = self.frame_number
                    if markup:
                        image = self.markup(self.get_buffer(self.active_buffer))
                    else:
                        image = self.get_buffer(self.active_buffer)
                    # encode the frame in JPEG format
                    (flag, encoded_image) = cv2.imencode(".jpg", image)

                    if not flag:
                        print("Error encoding image %d" % self.frame_number)
                        continue

                    data = b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encoded_image) + b'\r\n'
                else:
                    self.frame_cv.wait()
            if data is not None:
                yield data