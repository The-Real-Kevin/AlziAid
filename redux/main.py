import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from gaze_tracking import GazeTracking
import time
import csv
import random
import logging

class SmoothPursuitTest:
    def __init__(self, root):
        # Configure logging
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler('app_error.log', mode='w')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logging.debug("Initializing SmoothPursuitTest")
        self.root = root
        self.root.title("Alzheimer's Eye Tracking Test")
        # Canvas size (720p) with 50px margins
        self.canvas_width = 1280
        self.canvas_height = 720
        self.margin = 50
        self.active_width = self.canvas_width - 2 * self.margin
        self.active_height = self.canvas_height - 2 * self.margin - 50  # Space for button
        self.canvas = tk.Canvas(root, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack(pady=10)
        # Draw black border
        self.canvas.create_rectangle(
            self.margin, self.margin,
            self.canvas_width - self.margin, self.canvas_height - self.margin - 50,
            outline="black", width=2
        )
        self.gaze = GazeTracking()
        self.webcam = cv2.VideoCapture(0)
        logging.debug(f"Webcam initialized: {self.webcam.isOpened()}")
        self.test_running = False
        self.start_time = 0
        self.dot_pos = [self.canvas_width / 2, self.canvas_height / 2]
        self.dot_velocity = [0, 0]  # [vx, vy] in pixels per second
        self.gaze_data = []
        self.blink_count = 0
        self.dot = None
        self.next_button = None
        self.dot_radius = max(10, int(self.canvas_width * 0.01))
        self.last_log_time = 0
        self.calibrated = False  # Track calibration state
        self.calibrate_button = tk.Button(root, text="Calibrate", command=self.show_start_instructions)
        self.calibrate_button.pack(pady=5)
        logging.debug("Calibration button created")

    def show_start_instructions(self):
        """Show popup with test instructions and disable button."""
        if self.calibrated:
            return  # Prevent multiple calibrations
        self.calibrate_button.config(state='disabled')  # Disable button immediately
        instructions = (
            "Welcome to the Alzheimer's Eye Tracking Test\n\n"
            "Instructions:\n"
            "- Please sit comfortably in front of your webcam.\n"
            "- Ensure your face is well-lit and centered in the camera view.\n"
            "- Follow the blue dot with your eyes during calibration.\n"
            "- During the test, track the red dot as it moves across the screen.\n"
            "- The test will last approximately 60 seconds.\n"
            "- Do not move your head; only move your eyes to follow the dot.\n\n"
            "Click 'OK' to begin calibration."
        )
        messagebox.showinfo("Test Instructions", instructions)
        self.calibrate()

    def calibrate(self):
        if self.calibrated:
            return  # Prevent re-running calibration
        logging.debug("Starting calibration")
        calibration_points = [
            (self.margin + self.active_width * 0.1, self.margin + self.active_height * 0.1),
            (self.margin + self.active_width * 0.9, self.margin + self.active_height * 0.1),
            (self.margin + self.active_width * 0.9, self.margin + self.active_height * 0.9),
            (self.margin + self.active_width * 0.1, self.margin + self.active_height * 0.9)
        ]
        for point in calibration_points:
            self.canvas.delete("all")
            # Redraw black border
            self.canvas.create_rectangle(
                self.margin, self.margin,
                self.canvas_width - self.margin, self.canvas_height - self.margin - 50,
                outline="black", width=2
            )
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
            logging.debug(f"Calibration point: {point}")
        self.canvas.delete("all")
        # Redraw black border
        self.canvas.create_rectangle(
            self.margin, self.margin,
            self.canvas_width - self.margin, self.canvas_height - self.margin - 50,
            outline="black", width=2
        )
        self.calibrate_button.destroy()
        self.calibrated = True
        logging.debug("Calibration complete")
        self.start_test()

    def start_test(self):
        logging.debug("Starting test")
        self.test_running = True
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.dot_pos = [self.canvas_width / 2, self.canvas_height / 2]  # Start at center
        self.dot = self.canvas.create_oval(
            self.dot_pos[0] - self.dot_radius, self.dot_pos[1] - self.dot_radius,
            self.dot_pos[0] + self.dot_radius, self.dot_pos[1] + self.dot_radius,
            fill="red"
        )
        self.next_button = tk.Button(self.root, text="Next", command=self.show_save_instructions)
        self.next_button.pack(pady=5)
        self.set_new_velocity()
        self.move_dot()
        self.update()

    def set_new_velocity(self):
        """Set a new random velocity for the dot."""
        speed = random.uniform(300, 400)  # Pixels per second
        angle = random.uniform(0, 2 * np.pi)
        self.dot_velocity = [speed * np.cos(angle), speed * np.sin(angle)]
        logging.debug(f"New velocity: {self.dot_velocity}")

    def move_dot(self):
        if self.test_running:
            # Update position with fixed time step
            dt_frame = 0.016  # ~16ms per frame
            x = self.dot_pos[0] + self.dot_velocity[0] * dt_frame
            y = self.dot_pos[1] + self.dot_velocity[1] * dt_frame

            # Define active boundaries (touching the border)
            min_x = self.margin
            max_x = self.canvas_width - self.margin
            min_y = self.margin
            max_y = self.canvas_height - self.margin - 50

            # Check for border collision and reverse axis to bounce
            if x <= min_x:
                self.dot_velocity[0] = abs(self.dot_velocity[0])  # Reverse x to move right
                x = min_x
                logging.debug(f"Bounced off left border at x={x}")
            elif x >= max_x:
                self.dot_velocity[0] = -abs(self.dot_velocity[0])  # Reverse x to move left
                x = max_x
                logging.debug(f"Bounced off right border at x={x}")
            if y <= min_y:
                self.dot_velocity[1] = abs(self.dot_velocity[1])  # Reverse y to move down
                y = min_y
                logging.debug(f"Bounced off top border at y={y}")
            elif y >= max_y:
                self.dot_velocity[1] = -abs(self.dot_velocity[1])  # Reverse y to move up
                y = max_y
                logging.debug(f"Bounced off bottom border at y={y}")

            self.dot_pos = [x, y]
            self.canvas.coords(
                self.dot,
                x - self.dot_radius, y - self.dot_radius,
                x + self.dot_radius, y + self.dot_radius
            )
            self.root.after(16, self.move_dot)

    def update(self):
        if self.test_running and (time.time() - self.start_time) < 60:
            current_time = time.time()
            ret, frame = self.webcam.read()
            gaze_x, gaze_y, distance = None, None, None
            if ret:
                self.gaze.refresh(frame)
                if self.gaze.pupils_located:
                    left_coords = self.gaze.pupil_left_coords()
                    right_coords = self.gaze.pupil_right_coords()
                    logging.debug(f"Raw left: {left_coords}, Raw right: {right_coords}")
                    if left_coords and right_coords:
                        webcam_width, webcam_height = self.webcam.get(3), self.webcam.get(4)
                        gaze_x = 1 - (left_coords[0] + right_coords[0]) / 2 / webcam_width
                        gaze_y = (left_coords[1] + right_coords[1]) / 2 / webcam_height
                    elif left_coords:
                        gaze_x = 1 - left_coords[0] / self.webcam.get(3)
                        gaze_y = left_coords[1] / self.webcam.get(4)
                    elif right_coords:
                        gaze_x = 1 - right_coords[0] / self.webcam.get(3)
                        gaze_y = right_coords[1] / self.webcam.get(4)
                    if gaze_x is not None and gaze_y is not None:
                        gaze_x = max(0, min(1, gaze_x)) * self.canvas_width
                        gaze_y = max(0, min(1, gaze_y)) * self.canvas_height
                        distance = np.sqrt((gaze_x - self.dot_pos[0])**2 + (gaze_y - self.dot_pos[1])**2)
                    if self.gaze.is_blinking():
                        self.blink_count += 1
                    logging.debug(f"Normalized gaze: ({gaze_x}, {gaze_y}), Distance: {distance if distance is not None else 'None'}")

            # Log data every second
            if current_time - self.last_log_time >= 1.0:
                self.gaze_data.append([current_time - self.start_time, distance if distance is not None else -1, self.blink_count])
                self.last_log_time = current_time
                logging.debug(f"Logged data: {self.gaze_data[-1]}")

            self.root.after(16, self.update)
        elif self.test_running:
            self.test_running = False
            self.canvas.delete(self.dot)
            self.next_button.focus_set()
            logging.debug("Test complete")

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
        logging.debug("Saving results")
        self.test_running = False
        self.webcam.release()
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp (s)", "Gaze-Dot Distance (pixels)", "Blink Count"])
                for data in self.gaze_data:
                    writer.writerow([f"{data[0]:.2f}", f"{data[1]:.2f}" if data[1] != -1 else "N/A", data[2]])
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = SmoothPursuitTest(root)
    root.mainloop()
