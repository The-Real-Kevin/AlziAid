import os
from setuptools import setup

# Collect all files in gaze_tracking folder
gaze_tracking_files = [
    os.path.join('gaze_tracking', f)
    for f in os.listdir('/Users/kevinsun/Documents/AlziAid/redux/gaze_tracking')
    if os.path.isfile(os.path.join('/Users/kevinsun/Documents/AlziAid/redux/gaze_tracking', f))
]

setup(
    app=['main.py'],
    data_files=[
        ('cv2/data', [
            '/Users/kevinsun/Documents/AlziAid/redux/venv/lib/python3.13/site-packages/cv2/data/haarcascade_frontalface_default.xml',
            '/Users/kevinsun/Documents/AlziAid/redux/venv/lib/python3.13/site-packages/cv2/data/haarcascade_eye.xml'
        ]),
        ('tcl', ['/opt/homebrew/Cellar/tcl-tk/9.0.2/lib/tcl9.0']),
        ('tk', ['/opt/homebrew/Cellar/tcl-tk/9.0.2/lib/tk9.0']),
        ('gaze_tracking', gaze_tracking_files),
        ('.', ['/opt/homebrew/Cellar/ffmpeg/7.1.1_3/lib/libavcodec.61.19.101.dylib']),
        ('.', ['/opt/homebrew/Cellar/ffmpeg/7.1.1_3/lib/libavformat.61.7.100.dylib']),
        ('.', ['/opt/homebrew/Cellar/ffmpeg/7.1.1_3/lib/libavutil.59.39.100.dylib'])
    ],
    options={
        'py2app': {
            'packages': ['numpy', 'cv2', 'tkinter'],
            'resources': ['/Users/kevinsun/Documents/AlziAid/redux/gaze_tracking'],
            'plist': {
                'NSCameraUsageDescription': 'This app requires camera access for eye tracking.'
            },
            'excludes': ['PyInstaller', 'PySide2']
        }
    },
    setup_requires=['py2app']
)
