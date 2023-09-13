import streamlit as st
import pandas as pd
from streamlit_calendar import calendar
from datetime import datetime
import streamlit_tags as stt
import os
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import pandas as pd
import yaml

SCHEMAS_DIR = "schemas"
EMPLOYER_LIST_FILE = "employer_list.csv"

# def generate_yaml_from_csv(csv_file, yaml_file):
#     # Read the CSV
#     df = pd.read_csv(csv_file)
#
#     # Prepare the data for the YAML
#     credentials = {}
#     for index, row in df.iterrows():
#         username = "_".join(row["name"].lower().split())  # Convert name to username format (e.g., John Doe -> john_doe)
#         credentials[username] = {
#             "email": row["email"],
#             "name": row["name"],
#             "password": "placeholder_password"  # Placeholder for the password
#         }
#
#     # Construct the data for the YAML file
#     data = {
#         "credentials": {
#             "usernames": credentials
#         }
#     }
#
#     # Write to the YAML file
#     with open(yaml_file, "w") as file:
#         yaml.dump(data, file)
#
# # Usage
# generate_yaml_from_csv("employer_list.csv", "credentials.yaml")

# Load employer names from employer_list.csv
employer_names = load_employer_list()

with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)
name, authentication_status, username = authenticator.login('Login', 'main')

# Create the schemas directory if it doesn't exist
if not os.path.exists(SCHEMAS_DIR):
    os.makedirs(SCHEMAS_DIR)

def load_employer_list():
    try:
        df = pd.read_csv(EMPLOYER_LIST_FILE)
        return df['name'].tolist()
    except FileNotFoundError:
        st.error("The employer_list.csv file is missing!")
        return []

def check_or_create_file():
    try:
        df = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        df = pd.DataFrame(columns=["name", "date", "status"])
        df.to_csv(DATA_FILE, index=False)

def get_employee_file_path(name):
    """
    Convert name to the format firstname_lastname.csv and return the full path.
    """
    filename = "_".join(name.lower().split()) + ".csv"
    return os.path.join(SCHEMAS_DIR, filename)

def add_entry(name, date, status):
    file_path = get_employee_file_path(name)

    # If file doesn't exist, create it with headers
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            f.write("name,date,status\n")

    df = pd.read_csv(file_path)
    new_entry = pd.DataFrame({"name": [name], "date": [date], "status": [status]})
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv(file_path, index=False)

def get_employee_details(name):
    file_path = get_employee_file_path(name)
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        return pd.DataFrame(columns=["name", "date", "status"])

def get_all_entries():
    all_entries = pd.DataFrame(columns=["name", "date", "status"])
    for file in os.listdir(SCHEMAS_DIR):
        if file.endswith(".csv"):
            df = pd.read_csv(os.path.join(SCHEMAS_DIR, file))
            all_entries = pd.concat([all_entries, df], ignore_index=True)
    return all_entries

def get_calendar_events(name):
    details = get_employee_details(name)
    events = []
    for index, row in details.iterrows():
        events.append({
            "title": row["status"],
            "start": row["date"],
            "end": row["date"],
        })
    return events


st.title("Employee Status Manager")

df_employees = pd.read_csv('employee_list.csv')
manager_emails = df_employees[df_employees['Role'] == 'Manager']['Email'].tolist()
employer_emails = df_employees['Email'].tolist()

# Initialize authentication
name, authentication_status, username = authenticator.login('Login', 'main')

if not authentication_status:  # If the user is not authenticated
    if st.button("Register"):
        email = st.text_input("Enter Email")
        password = st.text_input("Enter Password", type="password")

        # Check if the email already exists
        if email not in config['credentials']['usernames']:
            hashed_password = stauth.Hasher([password]).generate()[0]  # Assuming the Hasher returns a list
            # Add the user's hashed password to the credentials
            config['credentials']['usernames'][email] = {
                "email": email,
                "name": "",  # or ask for a name in the registration form
                "password": hashed_password
            }
            # Save the updated config to the YAML file (this may need additional security checks)
            with open('config.yaml', 'w') as file:
                yaml.dump(config, file)
            st.success("Registration successful!")
        else:
            st.warning("This email is already registered. Please log in.")

if username in manager_emails:
    st.header("Manager Dashboard")
    df = get_all_entries()
    unique_names = df['name'].unique().tolist()

    # Dropdown to select employee name
    selected_name = st.selectbox("Select an employee", [""] + unique_names)

    calendar_events = get_calendar_events(selected_name)

    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay",
        },
        "initialView": "dayGridMonth",
    }

    st_calendar = calendar(events=calendar_events, options=calendar_options)

    if st.checkbox("Show full record report"):
        st.subheader("Time-management Records")

        # Fetch the details for the selected employee
        employee_details = df[df["name"] == selected_name]

        # Display the data in an editable format
        edited_data = st.data_editor(employee_details, hide_index=True)

    # Display reference tags
    reference_tags = ["H - Holiday", "OS - Offshore", "DO - Day Off", "TR - Training", "CE - Certification",
                      "CO - Conference"]
    st.subheader("Reference Tags")
    st.write(", ".join(reference_tags))


elif username in employer_names:

    st.header("Update your status")
    name = st.selectbox("Select an employee", [""] + employer_names, placeholder="Choose an employee...")
    status = st.selectbox("Status",
                          ["H - Holiday", "OS - Offshore", "DO - Day Off", "TR - Training", "CE - Certification", "CO - Conference"])
    selected_status = status.split(' ')[0]

    selected_dates = st.date_input("Select the date(s)", [datetime.now(), datetime.now()])

    if st.button("Update Status"):
        if isinstance(selected_dates, list) or isinstance(selected_dates, tuple):
            for selected_date in pd.date_range(selected_dates[0], selected_dates[1]):
                add_entry(name, selected_date.strftime('%Y-%m-%d'), selected_status)
            st.success(f"Status updated for {name} for selected dates to {status}")
        else:
            add_entry(name, selected_dates.strftime('%Y-%m-%d'), selected_status)
            st.success(f"Status updated for {name} on {selected_dates.strftime('%Y-%m-%d')} to {status}")


elif authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')

if authentication_status:
    authenticator.logout('Logout', 'main')
