Sure, here's the complete `README.md` file with the additional content about the images referencing the Boom Open and Boom Closed states:

```markdown
# Project Setup and Instructions

## Getting Started

1. **Navigate to the Directory**:
   ```bash
   cd tk_directory
   ```

2. **Create a Virtual Environment**:
   ```bash
   virtualenv john
   ```

3. **Activate the Virtual Environment**:
   ```bash
   john\scripts\activate
   ```

4. **Install Required Packages**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Project

5. **Ensure you have an Internet Connection**: The project requires an internet connection to connect to the Roboflow API for the pretrained model for number plate detection.

6. **Run the Application**:
   ```bash
   python app.py
   ```
   This will display the URL:
   ```
   127.0.0.1:5000
   ```

## Flask Application

7. **For the Boom**: Ensure all connections are properly done; otherwise, the boom will not open. Match the COM Ports with those in `arduino_control.py`.

8. **Enjoy**: Once everything is set up, enjoy using the application!

## Reports

- The application generates reports that include timestamps of vehicle entries, number plates, owners, and attempts to access the entrance point.

## Admin Credentials
- **Username:** admin
- **Password:** admin123

## Images

Below are some images related to the project:

### Boom Open
![Boom Open](20240517_093255.heic)

### Boom Closed
![Boom Closed](20240517_093257.heic)
```

