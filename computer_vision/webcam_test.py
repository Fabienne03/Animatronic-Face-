import cv2 # Load OpenCV so Python can work with the webcam.
# Camera number 0 usually means the laptop's default webcam.
camera = cv2.VideoCapture(0)
# Stop with a helpful message if the camera cannot open.
if not camera.isOpened():
 raise RuntimeError("Camera not found. Check permissions.")
# Keep taking new pictures (frames) until the user quits.
while True:
 success, frame = camera.read() # Get one camera frame.
 if not success: # Stop if the camera did not return a frame.
         break
 frame = cv2.flip(frame, 1) # Mirror the image like a selfie.
 cv2.imshow("OpenCV Webcam Test", frame) # Show the frame.
 # Wait briefly for a key; Q closes the window.
 if cv2.waitKey(1) & 0xFF == ord("q"):
         break
camera.release() # Give the camera back to other applications.
cv2.destroyAllWindows() # Close OpenCV's windows.
