# VoxGuard

**Real-Time Voice Cloning Detection & Active Prevention Engine**

VoxGuard is a comprehensive system designed to analyze live audio streams and detect synthetic voice artifacts in real-time. It uses a combination of deterministic DSP (Digital Signal Processing) heuristics and optional lightweight machine learning (ONNX model inference) to provide robust protection against voice cloning and deepfakes.

This project was built for the **Smart India Hackathon (SIH)**.

## 🏗️ Architecture

The project is structured as a monorepo with two main components:

- **Frontend (`voxguard-frontend`)**: A modern Next.js web application that serves as the dashboard. It provides real-time telemetry, visualizes live audio analysis, and displays detection statistics.
- **Backend (`voxguard-backend`)**: A high-performance FastAPI Python application that processes the audio streams via WebSockets, runs DSP algorithms and ONNX inferences, and exposes telemetry REST APIs.

## ✨ Features

- **Real-Time Audio Analysis**: Process incoming audio streams via WebSockets with minimal latency.
- **Hybrid Detection Engine**: Utilizes both deterministic DSP heuristics and ML inference (ONNX) to accurately identify synthetic voice artifacts.
- **Live Telemetry & Dashboard**: Monitor detection events, system health, and processing metrics live via the Next.js dashboard.
- **Challenge Verification**: Integrated with Speech-to-Text (Whisper) for challenge-response verification workflows.

## 🚀 Getting Started

### Prerequisites
- [Node.js](https://nodejs.org/) (v18+)
- [Python](https://www.python.org/) (3.10+)

### 1. Backend Setup (FastAPI)

Navigate to the backend directory:
```bash
cd voxguard-backend
```

Create a virtual environment and activate it:
```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate
```

Install the required dependencies:
```bash
pip install -r requirements.txt
```

Start the FastAPI server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The backend API will be available at `http://localhost:8000`.

### 2. Frontend Setup (Next.js)

Open a new terminal and navigate to the frontend directory:
```bash
cd voxguard-frontend
```

Install the required Node packages:
```bash
npm install
```

Start the Next.js development server:
```bash
npm run dev
```
The dashboard will be available at `http://localhost:3000`.
