# Reddit Auto-Commenter and Rosint Integration Bot

A robust, multi-threaded Python automation tool built with Tkinter and Selenium WebDriver (Firefox). It integrates seamlessly with local intelligence trackers (such as Rosint) to automate commenting on user-targeted Reddit posts safely and efficiently.

![Main Application Interface](screenshots/main_interface.png)

---

## Key Features

### 1. Modern Cross-Platform GUI and Native Theming
* **Adaptive Design:** Automatically detects your Operating System (Windows, macOS, or Linux) and applies native styles.
* **Dark Mode Support:** Features a clean, dark-themed interface on Linux environments with customized entry boxes and distinct action buttons.
* **Custom Dialogs:** Replaces standard OS dialog boxes with theme-matching popups for alerts, confirmations, and password inputs.

### 2. Automated Environment and Dependency Setup
* **Rosint Server Detection:** Automatically checks if Node.js/NPM or Vite (`npm run dev`) is running for your local tracker.
* **Auto-Cloning and Installation:** If the local Rosint directory is missing, the tool can automatically clone the repository from GitHub and install all required packages.
* **Linux / Arch Linux Support:** Includes built-in support for Arch Linux (`yay`/`paru`) to verify and install system dependencies (`git`, `nodejs`, `npm`, `firefox`, `geckodriver`) securely with sudo password handling.

### 3. Strict VPN Security and Live IP Enforcement
* **Commercial VPN Verification:** Cross-references your active public IP against live, frequently updated open-source VPN IP lists and CIDR blocks (including ProtonVPN and major datacenter mirrors).
* **Auto-Fetch Mirrors:** Features a manual and automatic fetch system to update cached VPN subnets (`vpn_ips.txt`).
* **Instant Warnings:** Automatically blocks execution and prompts you with operating-system-specific download links if an unmasked, non-VPN IP is detected.

![Security and VPN Configuration](screenshots/vpn_settings.png)

### 4. Smart Reddit Targeting and Layout Bypassing
* **Classic Layout Routing:** Automatically rewrites scraped links to use Classic Reddit (`old.reddit.com`). This completely bypasses modern Reddit's closed Shadow DOM layout components (`shreddit-composer`), preventing false deleted or locked errors and ensuring reliable comment box access.
* **Local Dashboard Integration:** Seamlessly interfaces with your local tracking instance (`http://localhost:5173/?u=username`) to pull active target posts.
* **Duplicate Prevention:** Uses a persistent local caching mechanism (`post_cache.txt`) to ensure the bot never comments on the same post twice.

### 5. Advanced Session Management and Logging
* **Robust Error Recovery:** Automatically detects if the Firefox browser session or window has crashed or closed, safely re-initializing the WebDriver and prompting for reconnection without crashing the loop.
* **Popup and Alert Disruption Handling:** Automatically detects and dismisses intrusive native browser alert popups and page modal dialogs.
* **Automated Daily Activity Logs:** Generates and appends timestamped session logs to a daily log file formatted as `redditMM-DD.txt` (e.g., `reddit08-24.txt`), alongside a real-time scannable activity window.
* **Flexible Time Parsing:** Supports natural interval formatting inputs (e.g., `30s`, `1h30m`, `2d`) for scan pauses.

---

## Prerequisites

Before running the application, ensure you have the following installed on your system:
* Python 3.8 or higher
* Mozilla Firefox
* Geckodriver (required for Selenium Firefox automation)
* Node.js and NPM (if you plan to run the integrated Rosint server)

---

## Installation and Setup

1. Clone or download this project to your local machine.
2. Install the required Python dependencies:
   ```bash
   pip install selenium requests
   ```
3. Run the application script:
    ```bash
    python main.py
    ```
## How to Use

### Launch the Application: Run the script. The application will inspect your environment and offer to set up Rosint automatically if it is missing.

### Configure Targeting:

* Enter your target user in the Target User field (the username you want to monitor via your local tracker).

* Input your desired Comment Text.

* Set your preferred Scan Interval (e.g., 45s or 10m).

### Log In: Click 1. Open Browser & Log In, then sign into your Reddit account manually inside the automated Firefox window.

### Start Automation: Once logged in, click 2. Start Bot to begin the background automation loop. Use 3. Stop Bot at any time to safely halt execution.