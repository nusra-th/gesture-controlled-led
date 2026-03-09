import cv2
import mediapipe as mp
import serial
import time

# === CONFIG ===
SERIAL_PORT = "COM10"       # <- change to your serial port
BAUD = 115200
SEND_EVERY = 0.12          # seconds, how often to send mask
# ==============

# Open serial
try:
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=0.1)
    time.sleep(2)  # allow Arduino to reset
except Exception as e:
    print("Failed to open serial port:", e)
    ser = None

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(static_image_mode=False,
                       max_num_hands=1,
                       min_detection_confidence=0.6,
                       min_tracking_confidence=0.5)

cap = cv2.VideoCapture(0)

def fingers_up(hand_landmarks, handedness_label):
    # return tuple: (thumb, index, middle, ring, pinky) each 1 or 0
    lm = hand_landmarks.landmark
    # Tip landmark indices
    TIP_IDS = [4, 8, 12, 16, 20]
    # PIP or lower joint indices to compare for fingers (index..pinky)
    PIP_IDS = [2, 6, 10, 14, 18]  # note: for thumb we'll use a different logic

    fingers = [0]*5

    # For fingers index->pinky: compare y of tip < y of pip (camera coords: top is smaller y)
    for i in range(1,5):
        tip_y = lm[TIP_IDS[i]].y
        pip_y = lm[PIP_IDS[i]].y
        fingers[i] = 1 if tip_y < pip_y else 0

    # Thumb: detect by comparing x coordinates (works best when palm faces camera)
    # handedness_label is "Left" or "Right" from MediaPipe
    # For right hand, thumb tip x < ip x => thumb open (to left of IP) (mirror depending on camera)
    # For left hand, invert
    thumb_tip_x = lm[TIP_IDS[0]].x
    thumb_ip_x  = lm[PIP_IDS[0]].x
    if handedness_label == "Right":
        fingers[0] = 1 if thumb_tip_x < thumb_ip_x else 0
    else:
        fingers[0] = 1 if thumb_tip_x > thumb_ip_x else 0

    return fingers  # [thumb,index,middle,ring,pinky]

last_sent = 0
print("Starting camera. Press 'q' to quit.")
while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = hands.process(frame_rgb)

    mask = 0
    if res.multi_hand_landmarks:
        for hand_landmarks, handedness in zip(res.multi_hand_landmarks, res.multi_handedness):
            label = handedness.classification[0].label  # "Left" or "Right"
            f = fingers_up(hand_landmarks, label)      # [thumb,index,middle,ring,pinky]
            # Map to pins: bit0 -> index (pin2), bit1 -> middle (pin3), bit2 -> ring (pin4), bit3 -> pinky (pin5), bit4 -> thumb (pin6)
            # BUT our Arduino expects bits 0..4 mapping to pins in order defined there (pins[0]=2 ... pins[4]=6)
            # We'll order bits as: index->bit0, middle->bit1, ring->bit2, pinky->bit3, thumb->bit4
            idx_order = [1,2,3,4,0]
            for bitpos, finger_idx in enumerate(idx_order):
                if f[finger_idx]:
                    mask |= (1 << bitpos)
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            # show read fingers
            cv2.putText(frame, f"Mask: {mask} ({bin(mask)})", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            break
    else:
        cv2.putText(frame, "No hand", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

    cv2.imshow("Gesture LED Control", frame)

    now = time.time()
    if ser and now - last_sent > SEND_EVERY:
        try:
            # send as ASCII int followed by newline, Arduino uses Serial.parseInt()
            ser.write((str(mask) + "\n").encode('ascii'))
        except Exception as e:
            print("Serial write error:", e)
            ser = None
        last_sent = now

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if ser:
    ser.close()
cv2.destroyAllWindows()
