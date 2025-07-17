# Claude Classroom Management System

This is a comprehensive classroom management system built with Python. It features a web-based teacher dashboard and a native Windows client for students.

## 🚀 Features

* **Student Monitoring**: Live thumbnails and status updates.
* **Remote Control**: Full keyboard and mouse control.
* **Remote Commands**: Send messages, shutdown, restart, etc.
* **File Manager**: Browse, upload, download, and manage files on client machines.
* **Remote Execution**: Run programs on client machines remotely.

## 🛠️ Setup and Installation

### Prerequisites

* Python 3.8+
* pip (Python package installer)

### 1. Clone the Repository

```bash
git clone [https://github.com/your-username/claude-classroom.git](https://github.com/your-username/claude-classroom.git)
cd claude-classroom
```

### 2. Install Dependencies

Install the required Python packages for both the server and the client:

```bash
pip install -r requirements.txt
```

Create a `requirements.txt` file with the following content:

```
flask
flask-socketio
websockets
pyjwt
pywin32
pyautogui
pillow
pyinstaller
```

### 3. Running the Teacher Server

1.  Navigate to the `teacher_server` directory.
2.  Run the `app.py` script:

    ```bash
    python app.py
    ```

3.  Open your web browser and go to `http://<your-ip-address>:8080`.

### 4. Building the Student Client

1.  Navigate to the `student_client` directory.
2.  Run the `build.py` script:

    ```bash
    python build.py
    ```

3.  The `ClassroomClient.exe` will be created in the `dist` folder.

### 5. Installing the Student Client

1.  Copy the `ClassroomClient.exe` to the student's machine.
2.  Open a command prompt **as an administrator**.
3.  Navigate to the directory where you saved the `.exe`.
4.  Install the service:

    ```bash
    ClassroomClient.exe install
    ```

5.  Start the service:

    ```bash
    ClassroomClient.exe start
    ```

The client will now run in the background and connect to the teacher's server automatically.

## ⚙️ Configuration

You can customize the settings in `shared/config.py`. The most important settings are:

* `SERVER_HOST`: The IP address of the teacher's machine.
* `WEBSOCKET_PORT`: The port for WebSocket communication.
* `SECRET_KEY`: A secret key for authentication. **Change this in a production environment!**