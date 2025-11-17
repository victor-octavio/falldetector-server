from flask import Flask, Response, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
import time
import threading
import requests

app = Flask(__name__)
CORS(app)

# imports das configs do media pipe para detecção de pose 
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils

camera = cv2.VideoCapture(0)
fall_detected = False
fall_time = 0
frame_output = None

@app.route('/video_feed')
def video_feed():
    def generate():
        global frame_output
        while True:
            if frame_output is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_output + b'\r\n')
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    return jsonify({"fall_detected": fall_detected})

def trigger_webhook():
    try:
        requests.get('http://localhost:5678/webhook-test/queda', timeout=3)
    except:
        pass

def process_video():
    global frame_output, fall_detected, fall_time

    while True:
        success, frame = camera.read()
        if not success:
            break

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image)

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            # vale a pena depois explorar algumas outras landmarks para melhorar a detecção
            # neste caso apenas usamos ombro e quadril para detectar se a pessoa esta deitada 
            landmarks = results.pose_landmarks.landmark
            shoulder_y = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y
            hip_y = landmarks[mp_pose.PoseLandmark.LEFT_HIP].y

            vertical_diff = abs(shoulder_y - hip_y)

            if vertical_diff < 0.1: # acho que da pra melhorar esse valor aqui
                if not fall_detected:
                    fall_time = time.time()
                    fall_detected = True
            else:
                fall_detected = False

            # trigger se a pose ficou deitada por mais de 2 segundos
            if fall_detected and time.time() - fall_time > 2:
                cv2.putText(frame, "QUEDA DETECTADA!", (50, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                threading.Thread(target=trigger_webhook).start()  

        # manda o frame atual para streaming MJPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_output = buffer.tobytes()

threading.Thread(target=process_video, daemon=True).start()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
