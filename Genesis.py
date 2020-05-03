import requests
import json
from bs4 import BeautifulSoup
import smtplib
import ssl
from time import sleep

# Set up email info
sender_email = "****"
reciever_email = "****"
email_password = "****"
genesis_username = "****"
genesis_password = "****"

# Create a secure SSL context
context = ssl.create_default_context()

# URLs for Genesis, login info, headers
login_url = "https://parents.mtsd.k12.nj.us/genesis/sis/j_security_check"
weekly_summary_url = "https://parents.mtsd.k12.nj.us/genesis/parents?tab1=studentdata&tab2=gradebook&action=form&studentid=****"
list_assignments_url = "https://parents.mtsd.k12.nj.us/genesis/parents?tab1=studentdata&tab2=gradebook&tab3=listassignments&studentid=****&action=form&date=11/11/2019&dateRange=allMP&courseAndSection=&status="
login_info = {"j_username": genesis_username,
              "j_password": genesis_password}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36"}


def fetch_averages():
    with requests.Session() as session:
        post = session.post(login_url, data=login_info, headers=headers)
        weekly_summary_page = session.get(
            weekly_summary_url, headers=headers)
        weekly_summary = BeautifulSoup(weekly_summary_page.content, "lxml")

    unparsed_data = weekly_summary.find_all(
        "tr", {"class": ["listrowodd", "listroweven"]})
    class_grades = {}
    for Class in unparsed_data:
        class_name = Class.u.text.strip()
        class_grade = Class.div.text.strip()
        class_grades[class_name] = class_grade

    return class_grades


def fetch_assignments():
    with requests.Session() as session:
        post = session.post(login_url, data=login_info, headers=headers)
        list_assignments_page = session.get(
            list_assignments_url, headers=headers)
        list_assignments = BeautifulSoup(
            list_assignments_page.content, "lxml")

    assignment_list = set()

    for assignment in list_assignments.find_all(
            "tr", {"class": ["listrowodd", "listroweven"]}):

        # Get all necessary info for each assignment
        class_name = assignment.find_all("td", class_="cellLeft", height="25px")[
            1].find("div").text
        assignment_name = assignment.find(
            "td", class_="cellCenter", style="font-weight:bold;border: 1px solid black;").text
        grade_tag = assignment.find("div", style="font-weight: bold;")
        grade = grade_tag.text.strip(
        ) if grade_tag else "None"

        # Add to assignment list
        if grade_tag:
            assignment_list.add((class_name, assignment_name, grade))

    return assignment_list


with open("Assignments.json", "r") as infile:
    assignment_list = set([tuple(assignment)
                           for assignment in json.load(infile)])

while True:
    new_assignment_list = fetch_assignments()
    if assignment_list != new_assignment_list:
        changed_assignments = assignment_list ^ new_assignment_list

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, email_password)

            for update in changed_assignments:
                new_class_average = fetch_averages()[update[0]]
                msg_string = f"Name - {update[1]}\nClass - {update[0]}\nGrade - {update[2]}\nNew Average: {new_class_average}"
                server.sendmail(sender_email, reciever_email, msg_string)

        assignment_list = new_assignment_list
        with open("Assignments.json", "w") as outfile:
            json.dump(list(new_assignment_list), outfile)

    sleep(300)
