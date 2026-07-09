<<<<<<< HEAD
# Gesture Controller

Gesture Controller is an intuitive client-server application that allows you to control your PC's mouse using your mobile device. By leveraging your smartphone's touch screen as a remote trackpad, you can perform smooth mouse movements, clicks, scrolling, and dragging seamlessly over your local network.

## Features

- **Automatic Server Discovery:** The mobile app automatically finds and connects to the PC server via UDP broadcast, eliminating the need for manual IP configuration.
- **Smooth Mouse Movement:** Implements exponential smoothing for precise and fluid cursor control.
- **Full Mouse Simulation:** Supports left click, right click, double click, scrolling, and drag-and-drop actions.
- **Cross-Platform PC Support:** The server runs on Python and works across Windows, macOS, and Linux (thanks to `pyautogui`).
- **Modern Mobile App:** The client application is built with React Native, offering smooth performance for both iOS and Android.

## Project Structure

The repository is divided into two main components:

1. `pc-server/`: The Python-based WebSocket server that receives input and executes the simulated mouse commands.
2. `MobileApp/`: The React Native mobile client that captures touch gestures and sends them to the server.

## Prerequisites

### For PC Server
- Python 3.8+
- `pip` (Python package manager)

### For Mobile App
- Node.js (v20+)
- React Native environment setup (Android Studio for Android / Xcode for iOS)

## Getting Started

### 1. Running the PC Server

1. Navigate to the `pc-server` directory:
   ```bash
   cd pc-server
   ```
2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   python main.py
   ```
   The server will start listening on port 8765 and broadcast its presence on port 8766.

### 2. Running the Mobile App

1. Navigate to the `MobileApp` directory:
   ```bash
   cd MobileApp
   ```
2. Install the required Node modules:
   ```bash
   npm install
   ```
3. Start the application:
   - **For Android:**
     ```bash
     npm run android
     ```
   - **For iOS:**
     ```bash
     npm run ios
     ```

## Usage

1. Ensure both your PC and mobile device are connected to the **same local Wi-Fi network**.
2. Start the PC Server.
3. Open the Mobile App on your device. It should automatically detect the server and connect.
4. Use the app interface as a remote trackpad to control your computer's mouse!
=======
﻿# Hand-Gesture-Recognition-using-Python

*Instruction --> 1:use USB cable to connect Laptop and Mobile and need to run the folders. 
                 2:Laptop network,need to connect same network to mobile Wifi .
                 3:Laptop Wifi properities network type should as (*private).

#To run (pc-server) terminal command----> 1: cd pc-server
                                          2: venv/Scripts/Activate.ps1
                                          3: python main.py

#To run MobileApp terrminal command---->  1: cd MobileApp
                                          2: npx react-native start --reset-cache
                   open send terminal-->  1: cd MobileApp
                                          2: npx react-native run-android
>>>>>>> 4f74667a270dfdc5b6ed3cdf6996904f5af9b5f7
