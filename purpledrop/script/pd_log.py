"""Processing for recorded log files
"""

import click
import numpy as np

from purpledrop.playback import EventReader

def detect_framerate(logfile):
    reader = EventReader(logfile)
    frame_counter = 0
    FRAMES_TO_COUNT = 100
    start_time = None
    end_time = None
    frame_size = None
    for msg in reader:
        if msg.HasField('image_transform'):
            frame_size = (msg.image_transform.image_width, msg.image_transform.image_height)
        if msg.HasField('image'):
            if frame_counter == 0:
                start_time = float(msg.image.timestamp.seconds) + float(msg.image.timestamp.nanos) / 1e9
            else:
                end_time = float(msg.image.timestamp.seconds) + float(msg.image.timestamp.nanos) / 1e9
            frame_counter += 1
            if frame_counter == FRAMES_TO_COUNT:
                end_time = float(msg.image.timestamp.seconds) + float(msg.image.timestamp.nanos) / 1e9
                break

    if end_time is None:
        raise ValueError("No frames found in file")

    fps = (frame_counter-1) / (end_time - start_time)

    return fps, frame_size

def extract_video(logfile, outfile):
    import cv2
    frame_rate, frame_size = detect_framerate(logfile)
    print("Detected frame rate %.2f fps" % frame_rate)

    reader = EventReader(logfile)

    writer = cv2.VideoWriter(outfile, cv2.VideoWriter_fourcc('H', '2', '6', '4'), frame_rate, frame_size)

    for msg in reader:
        if msg.HasField('image'):
            frame = cv2.imdecode(np.asarray(bytearray(msg.image.image_data)), cv2.IMREAD_COLOR)
            writer.write(frame)

    writer.release()


@click.command()
@click.option('--video', type=str, help="Extract video frames from log")
@click.argument('logfile', required=True)
def main(video, logfile):
    """A utility for processing log files

    Currently provides only the --video flag, which can be used to extract the video frames from the log file.
    """
    if video is not None:
        print(f"Extracting video to {video}")
        extract_video(logfile, video)

if __name__ == '__main__':
    main()