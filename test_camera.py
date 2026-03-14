import cv2

print('OpenCV version:', cv2.__version__)

# Test camera access
cap = cv2.VideoCapture(0)
print('Camera opened:', cap.isOpened())

if cap.isOpened():
    ret, frame = cap.read()
    print('Frame captured:', ret)
    if ret:
        print('Frame shape:', frame.shape)
        # Save a test frame
        cv2.imwrite('test_frame.jpg', frame)
        print('Test frame saved as test_frame.jpg')
    else:
        print('Failed to capture frame')
    cap.release()
else:
    print('Failed to open camera')
    
# Try different camera indices
for i in range(3):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f'Camera {i} is available')
        cap.release()
    else:
        print(f'Camera {i} not available')
