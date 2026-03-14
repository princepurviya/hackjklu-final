import cv2
import numpy as np
from detector import DamageDetector

print("Testing crack detection...")

# Initialize detector
detector = DamageDetector()

# Test with the captured frame
frame = cv2.imread('test_frame.jpg')
if frame is None:
    print("Error: Could not load test_frame.jpg")
    exit()

print(f"Frame shape: {frame.shape}")

# Test crack detection with different sensitivities
for sensitivity in ['low', 'medium', 'high']:
    print(f"\n--- Testing with {sensitivity} sensitivity ---")
    
    annotated, crack_found, crack_count = detector.detect_cracks(
        frame, sensitivity=sensitivity
    )
    
    print(f"Cracks found: {crack_found}")
    print(f"Crack count: {crack_count}")
    
    # Save result
    output_file = f'test_crack_result_{sensitivity}.jpg'
    cv2.imwrite(output_file, annotated)
    print(f"Result saved as: {output_file}")

# Also test the edge mask directly
print("\n--- Testing edge mask computation ---")
edge_mask = DamageDetector.compute_edge_mask(frame, sensitivity='high')
print(f"Edge mask shape: {edge_mask.shape}")
print(f"Non-zero pixels in edge mask: {cv2.countNonZero(edge_mask)}")

cv2.imwrite('test_edge_mask.jpg', edge_mask)
print("Edge mask saved as: test_edge_mask.jpg")

# Create a simple test image with artificial cracks
print("\n--- Testing with artificial crack image ---")
test_img = np.ones((400, 600, 3), dtype=np.uint8) * 255

# Add some crack-like lines
cv2.line(test_img, (100, 200), (500, 210), (0, 0, 0), 2)  # horizontal line
cv2.line(test_img, (300, 50), (310, 350), (0, 0, 0), 3)   # vertical line
cv2.line(test_img, (150, 100), (450, 300), (0, 0, 0), 1)  # diagonal line

annotated, crack_found, crack_count = detector.detect_cracks(
    test_img, sensitivity='high'
)
print(f"Artificial cracks found: {crack_found}, count: {crack_count}")
cv2.imwrite('test_artificial_cracks.jpg', annotated)
print("Artificial crack test saved as: test_artificial_cracks.jpg")
