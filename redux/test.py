import tkinter as tk
from tkinter import filedialog
import cv2
import numpy as np
from gaze_tracking import GazeTracking
import time
import csv

class GazeCalibrationTest:
    def __init__(self, root):
        print("Initializing GazeCalibrationTest")
        self.root = root
        self.root.title("Gaze Calibration Test")
        self.canvas_width = 1280
        self.canvas_height = 720
        self.margin = 50
        self.active_width = self.canvas_width - 2 * self.margin
        self.active_height = self.canvas_height - 2 * self.margin - 50
        self.canvas = tk.Canvas(root, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack(pady=10)
        self.gaze = GazeTracking()
        self.webcam = cv2.VideoCapture(0)
        print(f"Webcam initialized: {self.webcam.isOpened()}")
        self.test_running = False
        self.gaze_data = []
        self.dot = None
        self.dot_radius = max(10, self.canvas_width * 0.01)
        self.calibrate_button = tk.Button(root, text="Calibrate", command=self.calibrate)
        self.calibrate_button.pack(pady=5)
        print("Calibration button created")

    def calibrate(self):
        print("Starting calibration")
        calibration_points = [
            (self.margin + self.active_width * 0.1, self.margin + self.active_height * 0.1),
            (self.margin + self.active_width * 0.9, self.margin + self.active_height * 0.1),
            (self.margin + self.active_width * 0.9, self.margin + self.active_height * 0.9),
            (self.margin + self.active_width * 0.1, self.margin + self.active_height * 0.9)
        ]
        for point in calibration_points:
            self.canvas.delete("all")
            self.canvas.create_oval(
                point[0] - self.dot_radius, point[1] - self.dot_radius,
                point[0] + self.dot_radius, point[1] + self.dot_radius,
                fill="blue"
            )
            self.root.update()
            time.sleep(2)
            ret, frame = self.webcam.read()
            if ret:
                self.gaze.refresh(frame)
            print(f"Calibration point: {point}, Pupils: {self.gaze.pupils_located}")
        self.canvas.delete("all")
        self.calibrate_button.destroy()
        print("Calibration complete")
        self.start_test()

    def start_test(self):
        print("Starting gaze visualization")
        self.test_running = True
        self.dot = self.canvas.create_oval(
            self.canvas_width / 2 - self.dot_radius, self.canvas_height / 2 - self.dot_radius,
            self.canvas_width / 2 + self.dot_radius, self.canvas_height / 2 + self.dot_radius,
            fill="green"
        )
        self.exit_button = tk.Button(self.root, text="Exit", command=self.save_results)
        self.exit_button.pack(pady=5)
        self.update()

    def update(self):
        if self.test_running:
            ret, frame = self.webcam.read()
            if ret:
                self.gaze.refresh(frame)
                gaze_x, gaze_y = None, None
                if self.gaze.pupils_located:
                    left_coords = self.gaze.pupil_left_coords()
                    right_coords = self.gaze.pupil_right_coords()
                    print(f"Raw left: {left_coords}, Raw right: {right_coords}")
                    if left_coords and right_coords:
                        # Normalize by webcam resolution and flip x-coordinate
                        webcam_width, webcam_height = self.webcam.get(3), self.webcam.get(4)
                        gaze_x = 1 - (left_coords[0] + right_coords[0]) / 2 / webcam_width  # Flip x
                        gaze_y = (left_coords[1] + right_coords[1]) / 2 / webcam_height
                    elif left_coords:
                        gaze_x = 1 - left_coords[0] / self.webcam.get(3)  # Flip x
                        gaze_y = left_coords[1] / self.webcam.get(4)
                    elif right_coords:
                        gaze_x = 1 - right_coords[0] / self.webcam.get(3)  # Flip x
                        gaze_y = right_coords[1] / self.webcam.get(4)
                    # Scale normalized coordinates to canvas
                    if gaze_x is not None and gaze_y is not None:
                        gaze_x = max(0, min(1, gaze_x)) * self.canvas_width
                        gaze_y = max(0, min(1, gaze_y)) * self.canvas_height
                        # Update green dot position
                        self.canvas.coords(
                            self.dot,
                            gaze_x - self.dot_radius, gaze_y - self.dot_radius,
                            gaze_x + self.dot_radius, gaze_y + self.dot_radius
                        )
                        self.gaze_data.append([time.time(), gaze_x, gaze_y])
                    print(f"Normalized gaze: ({gaze_x}, {gaze_y})")
            self.root.after(16, self.update)

    def save_results(self):
        print("Saving results")
        self.test_running = False
        self.webcam.release()
        self.canvas.delete(self.dot)
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp (s)", "Gaze X (pixels)", "Gaze Y (pixels)"])
                for data in self.gaze_data:
                    writer.writerow(data)
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = GazeCalibrationTest(root)
    root.mainloop()
