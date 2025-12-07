import asyncio
import websockets
import json
import pyautogui
import socket

# --- CONFIGURATION ---
WEBSOCKET_PORT = 8765
BROADCAST_PORT = 8766
BROADCAST_MESSAGE = "GESTURE_SERVER_HERE"
# Adjust these values to change speed and smoothness
JOYSTICK_SENSITIVITY = 1.0 # How fast the cursor moves.
SCROLL_SENSITIVITY = 20
SMOOTHING_FACTOR = 0.4      # How smooth the cursor is. 0.4 is "medium".
                            # (Lower = smoother, Higher = more responsive)

# --- SETUP ---
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0
SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size() # Get screen dimensions once

def get_local_ip():
    """Finds the local IP address of the PC."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

async def broadcast_server_presence():
    """Periodically sends a UDP broadcast message so clients can find the server."""
    local_ip = get_local_ip()
    loop = asyncio.get_running_loop()
    try:
        transport, _ = await loop.create_datagram_endpoint(
            lambda: asyncio.DatagramProtocol(),
            local_addr=('0.0.0.0', 0),
            allow_broadcast=True)
        
        broadcast_address = ('255.255.255.255', BROADCAST_PORT)
        
        print(f"📢 Starting automatic discovery broadcast...")
        while True:
            message = f"{BROADCAST_MESSAGE}:{local_ip}".encode()
            transport.sendto(message, broadcast_address)
            await asyncio.sleep(2)
    except Exception as e:
        print(f"⚠️ Broadcast error (often normal on close): {e}")
    finally:
        if 'transport' in locals():
            transport.close()

async def handler(websocket): # Added 'path' for library compatibility
    """Handles incoming WebSocket connections and all mouse actions."""
    print(f"✅ Mobile client connected from: {websocket.remote_address}")
    
    # Initialize the smoothed position for THIS client connection
    # This prevents the cursor from jumping when a new client connects.
    smooth_x, smooth_y = pyautogui.position()
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                action = data.get('action')

                if action == 'move':
                    dx = data.get('x', 0.0)
                    dy = data.get('y', 0.0)
                    
                    # --- UPDATED MOVEMENT LOGIC WITH SMOOTHING ---
                    # 1. Calculate the 'raw' next position based on the LAST smoothed position.
                    # This creates a more intuitive and less "drifty" feel.
                    raw_target_x = smooth_x + (dx * JOYSTICK_SENSITIVITY)
                    raw_target_y = smooth_y + (dy * JOYSTICK_SENSITIVITY)
                    
                    # 2. Apply exponential smoothing using the new factor
                    smooth_x = SMOOTHING_FACTOR * raw_target_x + (1 - SMOOTHING_FACTOR) * smooth_x
                    smooth_y = SMOOTHING_FACTOR * raw_target_y + (1 - SMOOTHING_FACTOR) * smooth_y

                    # 3. Clamp the SMOOTHED values to stay within screen boundaries
                    final_x = max(0, min(SCREEN_WIDTH - 1, smooth_x))
                    final_y = max(0, min(SCREEN_HEIGHT - 1, smooth_y))
                    
                    # 4. IMPORTANT: Update the smooth variables to the clamped values.
                    # This prevents the smoothed position from accumulating "off-screen".
                    smooth_x, smooth_y = final_x, final_y

                    # 5. Move to the safe, final smoothed position
                    pyautogui.moveTo(final_x, final_y, duration=0)
                    # --- END OF UPDATED LOGIC ---

                elif action == 'left_click':
                    pyautogui.click()
                    print("Action: Left Click")
                elif action == 'right_click':
                    pyautogui.rightClick()
                    print("Action: Right Click")
                elif action == 'double_click':
                    pyautogui.doubleClick()
                    print("Action: Double Click")
                elif action == 'scroll':
                    scroll_dy = data.get('y', 0.0)
                    pyautogui.scroll(-int(scroll_dy * SCROLL_SENSITIVITY))
                elif action == 'drag_start':
                    pyautogui.mouseDown()
                    print("Action: Drag Start")
                elif action == 'drag_end':
                    pyautogui.mouseUp()
                    print("Action: Drag End")

            except pyautogui.FailSafeException:
                print("⚠️ Fail-safe triggered! Resetting. Avoid moving to corners.")
                pass
            except Exception as e:
                print(f"❌ Error processing message: {e}")

    except websockets.exceptions.ConnectionClosed:
        print(f"🔌 Client {websocket.remote_address} disconnected.")

async def main():
    local_ip = get_local_ip()
    print("--- Ultimate Mouse Control Server (Medium Smooth Version) ---")
    print(f"✅ Server IP for manual connection: {local_ip}")
    print(f"📡 WebSocket server listening on port {WEBSOCKET_PORT}")
    print(f"🖥️ Screen dimensions: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

    server_task = websockets.serve(handler, "0.0.0.0", WEBSOCKET_PORT)
    broadcast_task = asyncio.create_task(broadcast_server_presence())
    
    await asyncio.gather(server_task, broadcast_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer shutting down.")