import cv2, numpy as np, joblib, collections
import mediapipe as mp
import time

# Load model
#clf = joblib.load('lip_model_rf.pkl')

clf = joblib.load('lip_model_webcam.pkl')
WORDS = ['begin','choose','connection','navigation',
         'next','previous','start','stop','hello','web']
SEQ_LEN = 5
LIP_IDX = [
    61, 185, 40, 39, 37, 0, 267, 269, 270, 409,
    291, 78, 95, 88, 178, 87, 14, 317, 402, 318
]

# Setup MediaPipe
BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='face_landmarker.task'),
    running_mode=VisionRunningMode.IMAGE,
    num_faces=1
)
face_landmarker = FaceLandmarker.create_from_options(options)

# State
buffer = []
pred_word = "Ready..."
confidence = 0.0
last_capture_time = time.time()
CAPTURE_INTERVAL = 0.3  # capture 1 frame every 0.3s (not every frame)
is_recording = False
countdown = 0

cap = cv2.VideoCapture(0)
print("Starting... Press SPACE to start recording a word, Q to quit")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = face_landmarker.detect(mp_image)

    face_detected = False
    coords = None

    if result.face_landmarks:
        face_detected = True
        lm = result.face_landmarks[0]
        coords = []
        for idx in LIP_IDX:
            coords.extend([lm[idx].x, lm[idx].y])

        # Draw lip dots on screen so user knows face is detected
        h, w = frame.shape[:2]
        for idx in LIP_IDX:
            x = int(lm[idx].x * w)
            y = int(lm[idx].y * h)
            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

    # Capture frames at intervals when recording
    now = time.time()
    if is_recording and face_detected and coords:
        if now - last_capture_time >= CAPTURE_INTERVAL:
            buffer.append(coords)
            last_capture_time = now
            countdown = SEQ_LEN - len(buffer)
            print(f"Captured frame {len(buffer)}/{SEQ_LEN}")

        # When buffer is full, predict
        if len(buffer) >= SEQ_LEN:
            seq = np.array(buffer[:SEQ_LEN]).flatten().reshape(1, -1)
            pred = clf.predict(seq)
            prob = clf.predict_proba(seq).max()
            pred_word = WORDS[pred[0]]
            confidence = prob
            print(f"Predicted: {pred_word} ({confidence:.0%})")
            buffer = []
            is_recording = False

    # Draw UI
    # Background bar
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 90), (0, 0, 0), -1)

    # Face detection status
    status_color = (0, 255, 0) if face_detected else (0, 0, 255)
    status_text = "Face detected" if face_detected else "No face detected"
    cv2.putText(frame, status_text, (15, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 1)

    # Recording status
    if is_recording:
        frames_left = SEQ_LEN - len(buffer)
        cv2.putText(frame, f"Recording... {len(buffer)}/{SEQ_LEN} frames",
                    (15, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
    else:
        cv2.putText(frame, "Press SPACE to record a word", (15, 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 1)

    # Prediction
    color = (0, 255, 100) if confidence > 0.7 else (0, 200, 255)
    cv2.putText(frame, f"{pred_word}  ({confidence:.0%})" if confidence > 0 else pred_word,
                (15, 78), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

    cv2.imshow('Lip Reading Demo  [SPACE=record, Q=quit]', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord(' '):  # spacebar
        if not is_recording and face_detected:
            print("\nStarting recording — mouth your word now!")
            buffer = []
            is_recording = True
            last_capture_time = time.time()
        elif not face_detected:
            print("No face detected! Move closer to camera.")

cap.release()
cv2.destroyAllWindows()