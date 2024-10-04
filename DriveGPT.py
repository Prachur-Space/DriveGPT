import os
import time
import json
import google.generativeai as genai
from PIL import Image
import mss
import pyautogui

genai.configure(api_key='API_KEY')

model = genai.GenerativeModel("gemini-1.5-flash")

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

PROMPT = (
    "You are controlling a 2018 Honda Civic Type-R in Forza Horizon 5 using the WASD keys. Your objective is to drive efficiently on a public road in Mexico, focusing on speed, aggressive cornering, and obstacle avoidance while staying on the road. "
    "The car has high acceleration, top speed, and a tendency to oversteer at high speeds. Analyze the screenshot to determine the optimal driving actions, and take into account previous screenshots to estimate the car’s speed and heading."

    "\n\n1. **Acceleration (W):** Use 'W' to accelerate the car. If the road ahead is straight, hold 'W' to gain speed. If approaching a curve or obstacle, reduce acceleration or release 'W' to maintain control. Consider the car's current speed (from the digital speedometer in the lower right) and how the speed has changed since the previous screenshot. Longer presses of 'W' should be used for accelerating on straight stretches, while shorter taps or no acceleration should be used when preparing for sharp turns."

    "\n\n2. **Braking (S):** Use 'S' to slow down or stop. Braking is essential when the car is going too fast into a turn, facing an obstacle, or approaching a sharp curve. Estimate how much braking is required by observing the car's speed and direction in the previous screenshot. If speed has dramatically increased over multiple frames, press 'S' for a longer duration to prevent loss of control."

    "\n\n3. **Turning (A and D):** Use 'A' to turn left and 'D' to turn right. For gentle curves, brief taps are sufficient. For sharper turns, press 'A' or 'D' for longer, especially at higher speeds. Base your turning decision on the car's previous heading: if the car was already turning in a prior screenshot, adjust the duration of your turn to complete or correct it. Avoid oversteering by checking if the car has turned too far in the last screenshot and correcting course accordingly."

    "\n\n4. **Handling 3-second Screenshot Intervals:** Since there is a 3-second delay between screenshots, make sure to account for the time gap by predicting what will happen in the next few seconds. If the car was moving in a straight line or gently turning, continue accelerating ('W') or turning ('A'/'D') with longer presses to maintain momentum. If you see a sharp turn or obstacle, anticipate it by starting to brake ('S') or ease off acceleration ('W') in advance, knowing that the car will have moved significantly before the next screenshot is taken."

    "\n\n5. **Using Context from Previous Screenshots:** Each new screenshot should be compared with the previous one to estimate changes in speed, direction, and position. For example, if the car was accelerating in the last screenshot and the road ahead is still straight, you can hold 'W' to keep accelerating. If the car started turning left in the previous frame but hasn't fully completed the turn, continue holding 'A' until the car straightens. Use the direction and speed from the last frame to adjust your actions in the current frame."

    "\n\n6. **Speed and Heading Adjustments Over Time:** Watch for gradual changes in speed and heading over multiple screenshots. If you notice that speed has increased over several frames, expect the car to be going faster and adjust accordingly—apply lighter turns and brake earlier. If the car has drifted off course slightly in previous frames, apply corrective steering to bring it back on track. Use these continuous adjustments to minimize reaction time and stay in control during the 3-second intervals."

    "\n\n7. **Anticipation and Prediction:** Since each screenshot represents a snapshot of the car's state after a 3-second interval, make conservative predictions about how much the car will have moved. For example, if you're approaching a turn in the current frame, anticipate that the car will have started turning by the time you get the next screenshot and hold 'A' or 'D' for longer. If you see an obstacle or traffic ahead, start braking ('S') or adjusting steering ('A'/'D') earlier, considering the high speed at which the car moves."
    
    "\n\n8. **Formatting the Response:** Provide the driving instructions in the following JSON format: "
    "{ 'actions': [ {'key': '<char keyboard key>', 'duration': <floating point time in sec>}, {'key': '<keyboard key>', 'duration': <floating point time in sec>}, ... } "
)


MAX_SCREENSHOT_AGE = 3600
MAX_SCREENSHOT_COUNT = 20

def capture_screenshot(save_path):
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        img.save(save_path)

def send_to_gemini(image_path, prompt):
    try:
        image = Image.open(image_path)
        response = model.generate_content([prompt, image])

        print("✅ Gemini API Response (Debug):", response)

        response_text = response.text.strip()

        print("✅ Gemini API Text Response (Debug):", response_text)

        response_text = response_text.replace('```json', '').replace('```', '').strip()

        return response_text
    except Exception as e:
        print(f"❌ Error communicating with Gemini API: {e}")
        return None

def parse_actions(response_text):
    try:
        if not response_text:
            print("❌ Response text is empty or None.")
            return []

        response_text = response_text.replace("'", '"')

        response_json = json.loads(response_text)
        actions = response_json.get('actions', [])

        if not isinstance(actions, list):
            print("⚠️ Actions are not in the expected format.")
            return []
        
        return actions
    except json.JSONDecodeError as e:
        print(f"❌ JSON decoding error: {e}")
        print(f"❌ Response Text: {response_text}")
        return []
    except Exception as e:
        print(f"❌ Error parsing actions: {e}")
        return []


def perform_key_presses(actions):
    for action in actions:
        key = action.get('key')
        duration = action.get('duration', 0)

        if key and duration > 0:
            print(f"🎮 Pressing '{key}' for {duration} seconds.")
            try:
                pyautogui.keyDown(key.lower())
                time.sleep(duration)
                pyautogui.keyUp(key.lower())
            except Exception as e:
                print(f"❌ Error performing key press '{key}': {e}")
        else:
            print(f"⚠️ Invalid action: {action}")

def delete_old_screenshots():
    current_time = time.time()
    cutoff_time = current_time - MAX_SCREENSHOT_AGE

    screenshots = [os.path.join(SCREENSHOT_DIR, f) for f in os.listdir(SCREENSHOT_DIR) if f.endswith('.png')]

    for screenshot in screenshots:
        try:
            file_mtime = os.path.getmtime(screenshot)
            if file_mtime < cutoff_time:
                os.remove(screenshot)
                print(f"🗑️ Deleted old screenshot: {screenshot}")
        except Exception as e:
            print(f"❌ Error deleting screenshot '{screenshot}': {e}")

    if MAX_SCREENSHOT_COUNT:
        screenshots_sorted = sorted(screenshots, key=lambda x: os.path.getmtime(x))
        excess_count = len(screenshots_sorted) - MAX_SCREENSHOT_COUNT
        if excess_count > 0:
            for i in range(excess_count):
                try:
                    os.remove(screenshots_sorted[i])
                    print(f"🗑️ Deleted excess screenshot: {screenshots_sorted[i]}")
                except Exception as e:
                    print(f"❌ Error deleting screenshot '{screenshots_sorted[i]}': {e}")

def main_loop():
    interval = 3

    while True:
        start_time = time.time()
        timestamp = int(start_time)
        screenshot_path = os.path.join(SCREENSHOT_DIR, f"screenshot_{timestamp}.png")

        print("📸 Capturing screenshot...")
        capture_screenshot(screenshot_path)

        print("📤 Sending screenshot to Gemini API...")
        response_text = send_to_gemini(screenshot_path, PROMPT)

        if response_text:
            print("📥 Received response from Gemini API.")
            actions = parse_actions(response_text)

            if actions:
                print(f"🔧 Performing actions: {actions}")
                perform_key_presses(actions)
            else:
                print("⚠️ No valid actions found in the response.")
        else:
            print("⚠️ No response received from Gemini API.")

        delete_old_screenshots()

        elapsed_time = time.time() - start_time
        sleep_time = max(interval - elapsed_time, 0)
        print(f"⏳ Waiting for {sleep_time:.2f} seconds before next iteration.\n")
        time.sleep(sleep_time)

if __name__ == "__main__":
    try:
        print("🚀 Starting AI driving assistant...")
        main_loop()
    except KeyboardInterrupt:
        print("\n🛑 Program terminated by user.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")