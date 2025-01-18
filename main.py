"""
Project Summary:
The "Job Scrapper" project automates the process of extracting job postings from Upwork based on specified search terms. The system integrates Selenium for web scraping, Airtable for data storage, and Slack for notifications.

Key Features:
1. Searches and extracts job details such as job title, post time, and activity information.
2. Filters jobs posted recently (within minutes or hours).
3. Avoids duplicate entries by cross-referencing existing Airtable records.
4. Sends notifications to specific Slack channels with job details and links.
5. Runs continuously to provide up-to-date job postings.
"""

import time
from dotenv import load_dotenv

load_dotenv()
from scrapper_ud import WebScraper
from selenium.webdriver.common.by import By
import os
from airtable import Airtable_Service
from slack_notification import notification

# Initialize Airtable service
# Fetches the Airtable base ID from environment variables
db = Airtable_Service(os.getenv('BASE_ID'))


def job_scrapper(search: dict, web_driver: any) -> None:
    """
    Scrapes job postings from Upwork and sends notifications for new job listings.

    Args:
        search (dict): A dictionary containing the search term and Slack channel ID.
            Example: {"search": "python", "channel_id": "C12345"}
        web_driver (WebScraper): An instance of the WebScraper class for browser interactions.

    Returns:
        None
    """
    # Fetch all existing job records from Airtable
    all_al_job = db.get_all_data(os.getenv('TABLE_JOB'))

    # Open the Upwork search URL based on the given search term
    web_driver.open_url(f"https://www.upwork.com/nx/search/jobs/?from_recent_search=true&q={search['search']}")
    time.sleep(3)  # Allow page to load

    # Find all job postings on the page
    jobs = web_driver.find_element_by(find_by='tag', what_to_find='article', multi=True)

    for job in jobs:
        # Extract job details
        job_id = job.get_attribute('data-ev-job-uid')
        job_body = job.find_element(By.CLASS_NAME, 'text-body-sm')
        job_title = job.find_element(By.CLASS_NAME, 'job-tile-title')
        url_get = job_title.find_element(By.TAG_NAME, 'a')
        job_url = url_get.get_attribute('href')
        job_time_and_title = job.find_element(By.CLASS_NAME, 'job-tile-header-line-height').text
        job_time_and_title = job_time_and_title.split("\n")
        job_time_post = job_time_and_title[0]

        # Skip jobs posted within minutes or hours
        if "minutes" in job_time_post or "hour" in job_time_post:
            continue

        # Open job details in a new tab
        web_driver.open_new_tab()
        web_driver.open_url(job_url)

        # Extract additional job details
        try:
            activity_info = web_driver.find_element_by(find_by="class_name", what_to_find='client-activity-items',
                                                       multi=False).text
            activity_info = activity_info.replace("\n", " ")
        except:
            activity_info = ''

        try:
            features = web_driver.find_element_by(find_by="class_name", what_to_find='features', multi=False).text
            features = features.replace("\n", " ")
        except:
            features = ''

        web_driver.close_tab()  # Close the job details tab

        # Check if the job already exists in Airtable
        check_job = [cj for cj in all_al_job if cj['fields']['job id'] == str(job_id)]
        if len(check_job) > 0:
            continue

        # Format the Slack notification message
        msg = [
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{job_title.text}*\n\n{job_time_post}\n\n{features}\n\n{activity_info}\n\n{job_body.text}"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View",
                        "emoji": True
                    },
                    "value": job_url,
                    "url": job_url,
                    "action_id": "button-action"
                }
            },
            {"type": "divider"},
        ]

        # Send the notification to Slack
        notification(channel_id=search['channel_id'], message=msg)

        # Add the job record to Airtable
        db.add_record(os.getenv('TABLE_JOB'), data={
            "job id": str(job_id),
            "title": job_title.text,
            "search term": search['search']
        })


if __name__ == "__main__":
    # Initialize the web scraper
    web_driver = WebScraper()
    web_driver.setup_driver()  # Set up the web driver

    # Define the search terms and associated Slack channels
    search_terms = [
        {"search": "python", "channel_id": "C076LLKMPE3"},
        {"search": "scraping", "channel_id": "C076LHX0NTH"},
        {"search": "react js", "channel_id": "C076UJ9DPFG"},
    ]

    # Continuously scrape jobs for the given search terms
    while True:
        for search_term in search_terms:
            job_scrapper(search_term, web_driver)
