from ultralytics import YOLO
import cv2
import math

def video_detection(path_x):
    video_capture = path_x
    # Create a Video Capture Object
    cap = cv2.VideoCapture(video_capture)
    
    if not cap.isOpened():
        print(f"Error: Cannot open video source: {video_capture}")
        return
    
    model = YOLO("best.pt")
    classNames = ["pothole"] 
    
    while True:
        success, img = cap.read()
        
        if not success:
            print("End of video or cannot read frame")
            break
        
        results = model(img, stream=True)
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                print(x1, y1, x2, y2)
                cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
                conf = math.ceil((box.conf[0] * 100)) / 100
                cls = int(box.cls[0])
                class_name = classNames[cls]
                label = f'{class_name} {conf}'
                t_size = cv2.getTextSize(label, 0, fontScale=1, thickness=2)[0]
                print(t_size)
                c2 = x1 + t_size[0], y1 - t_size[1] - 3
                cv2.rectangle(img, (x1, y1), c2, [255, 0, 255], -1, cv2.LINE_AA)  # filled
                cv2.putText(img, label, (x1, y1 - 2), 0, 1, [255, 255, 255], thickness=1, lineType=cv2.LINE_AA)
        
        # yield img
        cv2.imshow("Pothole Detection", img) #frame
        
        # Press 'q' to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cv2.destroyAllWindows()
    
    cap.release()


# Main execution
if __name__ == "__main__":
   
    video_path = "tested.mp4"  # Replace with your video file path or use 0 for webcam
    video_detection(video_path)
    print("Detection completed!")
    