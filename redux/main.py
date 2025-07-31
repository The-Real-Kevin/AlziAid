import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from gaze_tracking import GazeTracking
import time
import csv
import random

class SmoothPursuitTest:
    def __init__(self, root):
        print("Initializing SmoothPursuitTest")
        self.root = root
        self.root.title("Alzheimer's Eye Tracking Test")
        # Fixed canvas size (720p) with 50px margins
        self.canvas_width = 1280
        self.canvas_height = 720
        self.margin = 50
        self.active_width = self.canvas_width - 2 * self.margin
        self.active_height = self.canvas_height - 2 * self.margin - 50  # Space for button
        self.canvas = tk.Canvas(root, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack(pady=10)
        self.gaze = GazeTracking()
        self.webcam = cv2.VideoCapture(0)
        print(f"Webcam initialized: {self.webcam.isOpened()}")
        self.test_running = False
        self.start_time = 0
        self.dot_pos = [self.canvas_width / 2, self.canvas_height / 2]
        self.target_pos = self.dot_pos.copy()
        self.gaze_data = []
        self.blink_count = 0
        self.dot = None
        self.next_button = None
        self.move_start_time = 0
        self.move_duration = 0.5
        self.dot_radius = max(10, self.canvas_width * 0.01)
        self.calibrate_button = tk.Button(root, text="Calibrate", command=self.show_start_instructions)
        self.calibrate_button.pack(pady=5)
        print("Calibration button created")

    def show_start_instructions(self):
        """Show popup with test instructions before calibration."""
        instructions = (
            "Welcome to the Alzheimer's Eye Tracking Test\n\n"
            "Instructions:\n"
            "- Please sit comfortably in front of your webcam.\n"
            "- Ensure your face is well-lit and centered in the camera view.\n"
            "- Follow the blue dot with your eyes during calibration.\n"
            "- During the test, track the red dot as it moves across the screen.\n"
            "- The test will last approximately 30 seconds.\n"
            "- Do not move your head; only move your eyes to follow the dot.\n\n"
            "Click 'OK' to begin calibration."
        )
        messagebox.showinfo("Test Instructions", instructions)
        self.calibrate()

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
            print(f"Calibration point: {point}")
        self.canvas.delete("all")
        self.calibrate_button.destroy()
        print("Calibration complete")
        self.start_test()

    def start_test(self):
        print("Starting test")
        self.test_running = True
        self.start_time = time.time()
        self.dot = self.canvas.create_oval(
            self.dot_pos[0] - self.dot_radius, self.dot_pos[1] - self.dot_radius,
            self.dot_pos[0] + self.dot_radius, self.dot_pos[1] + self.dot_radius,
            fill="red"
        )
        self.next_button = tk.Button(self.root, text="Next", command=self.show_save_instructions)
        self.next_button.pack(pady=5)
        self.move_start_time = time.time()
        self.target_pos = self.dot_pos.copy()
        self.move_dot()
        self.update()

    def move_dot(self):
        if self.test_running:
            current_time = time.time()
            if current_time - self.move_start_time >= 2:
                self.dot_pos = self.target_pos.copy()
                self.target_pos = [
                    random.randint(int(self.margin + self.active_width * 0.1), int(self.margin + self.active_width * 0.9)),
                    random.randint(int(self.margin + self.active_height * 0.1), int(self.margin + self.active_height * 0.9))
                ]
                self.move_start_time = current_time
                print(f"New target: {self.target_pos}")

            elapsed = current_time - self.move_start_time
            t = min(elapsed / self.move_duration, 1.0)
            if t < 1:
                eased_t = t * t * (3 - 2 * t)
                x = self.dot_pos[0] + (self.target_pos[0] - self.dot_pos[0]) * eased_t
                y = self.dot_pos[1] + (self.target_pos[1] - self.dot_pos[1]) * eased_t
                self.dot_pos = [x, y]
                self.canvas.coords(
                    self.dot,
                    x - self.dot_radius, y - self.dot_radius,
                    x + self.dot_radius, y + self.dot_radius
                )
            self.root.after(16, self.move_dot)

    def update(self):
        if self.test_running and (time.time() - self.start_time) < 30:
            ret, frame = self.webcam.read()
            if ret:
                self.gaze.refresh(frame)
                if self.gaze.pupils_located:
                    left_coords = self.gaze.pupil_left_coords()
                    right_coords = self.gaze.pupil_right_coords()
                    print(f"Raw left: {left_coords}, Raw right: {right_coords}")
                    if left_coords and right_coords:
                        webcam_width, webcam_height = self.webcam.get(3), self.webcam.get(4)
                        gaze_x = 1 - (left_coords[0] + right_coords[0]) / 2 / webcam_width  # Flip x
                        gaze_y = (left_coords[1] + right_coords[1]) / 2 / webcam_height
                    elif left_coords:
                        gaze_x = 1 - left_coords[0] / self.webcam.get(3)  # Flip x
                        gaze_y = left_coords[1] / self.webcam.get(4)
                    elif right_coords:
                        gaze_x = 1 - right_coords[0] / self.webcam.get(3)  # Flip x
                        gaze_y = right_coords[1] / self.webcam.get(4)
                    else:
                        gaze_x, gaze_y = None, None
                    if gaze_x is not None and gaze_y is not None:
                        gaze_x = max(0, min(1, gaze_x)) * self.canvas_width
                        gaze_y = max(0, min(1, gaze_y)) * self.canvas_height
                        distance = np.sqrt((gaze_x - self.dot_pos[0])**2 + (gaze_y - self.dot_pos[1])**2)
                        self.gaze_data.append([time.time() - self.start_time, distance])
                    if self.gaze.is_blinking():
                        self.blink_count += 1
                    print(f"Normalized gaze: ({gaze_x}, {gaze_y}), Distance: {distance if gaze_x is not None else 'None'}")
            self.root.after(16, self.update)
        elif self.test_running:
            self.test_running = False
            self.canvas.delete(self.dot)
            self.next_button.focus_set()
            print("Test complete")

    def show_save_instructions(self):
        """Show popup with instructions for saving and submitting results."""
        instructions = (
            "Test Complete!\n\n"
            "Instructions for Saving Results:\n"
            "- Click 'OK' to open a file save dialog.\n"
            "- Choose a location to save the results as a CSV file.\n"
            "- Name the file clearly, e.g., 'EyeTracking_YourName_Date.csv'.\n"
            "- After saving, please upload the file to our Google Drive link: [Insert Google Drive Link Here]\n"
            "- Alternatively, email the file to: [Insert Email Address Here]\n"
            "- Ensure the file is sent within 24 hours for analysis.\n\n"
            "Thank you for participating!"
        )
        messagebox.showinfo("Save Results", instructions)
        self.save_results()

    def save_results(self):
        print("Saving results")
        self.test_running = False
        self.webcam.release()
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp (s)", "Gaze-Dot Distance (pixels)", "Blink Count"])
                for data in self.gaze_data:
                    writer.writerow([data[0], data[1], self.blink_count])
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = SmoothPursuitTest(root)
    root.mainloop()