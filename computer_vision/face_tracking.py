import cv2 # OpenCV captures webcam images and draws dots.
import mediapipe as mp # MediaPipe detects facial features.
from mediapipe.tasks import python # Tools for loading the model.
from mediapipe.tasks.python import vision # Face Landmarker tools.
# Tell MediaPipe where the downloaded model is stored.
# VIDEO mode processes a series of camera frames.
options = vision.FaceLandmarkerOptions(
 base_options=python.BaseOptions(
	 model_asset_path="face_landmarker.task"
 ),
 running_mode=vision.RunningMode.VIDEO,
 num_faces=1 # We will track one person at a time.
)
# Load the model into the facial landmark detector.
landmarker = vision.FaceLandmarker.create_from_options(options)
# Connect to the computer's default camera.
camera = cv2.VideoCapture(0)
if not camera.isOpened():
 landmarker.close() # Clean up before stopping.
 raise RuntimeError("Could not open webcam.")
# Video mode requires timestamps that increase each frame.
timestamp_ms = 0
print("Face tracking is running. Press Q to quit.")
try:
 while True: # Repeat while the webcam is running.
	 success, frame = camera.read() # Capture a new frame.
	 if not success:
		 break # Stop if no picture was captured.
	 frame = cv2.flip(frame, 1) # Mirror the webcam image.
	 # OpenCV uses BGR color; MediaPipe expects RGB.
	 rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
	 # Wrap the image in MediaPipe's image format.
	 mp_image = mp.Image(
		 image_format=mp.ImageFormat.SRGB,
		 data=rgb_frame
	 )
	 timestamp_ms += 33 # Approximate a 30-fps video clock.
	 # Ask MediaPipe to find landmarks in this frame.
	 result = landmarker.detect_for_video(
		 mp_image, timestamp_ms
	 )
	 # If a face is found, draw each landmark as a dot.
	 if result.face_landmarks:
		 height, width = frame.shape[:2] # Image size in pixels.
		 for point in result.face_landmarks[0]:
			 # Landmark positions are relative to image size.
			 x = int(point.x * width)
			 y = int(point.y * height)
			 # Draw a small green circle at that position.
			 cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)
	 # Show the original camera image with dots added.
	 cv2.imshow("Animatronic Face Landmarks", frame)
	 # Exit when Q is pressed in the camera window.
	 if cv2.waitKey(1) & 0xFF == ord("q"):
		 break
finally:
 camera.release() # Release webcam even if something fails.
 cv2.destroyAllWindows() # Close camera windows.
 landmarker.close() # Release MediaPipe resources

