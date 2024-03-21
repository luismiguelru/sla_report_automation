# -*- coding: utf-8 -*-
#
# Copyright (c) 2023, Development_Practices_Team
# All rights reserved.
#
import logging
import Levenshtein
import requests
import pandas as pd
from requests.auth import HTTPBasicAuth
import re
from collections import defaultdict
from typing import List

from connect.client import ConnectClient, R
from connect.eaas.core.decorators import (
    account_settings_page,
    module_pages,
    router,
    variables,
    web_app,
)
from connect.eaas.core.extension import WebApplicationBase
from connect.eaas.core.inject.common import get_call_context, get_config
from connect.eaas.core.inject.models import Context
from connect.eaas.core.inject.synchronous import get_installation, get_installation_client
from fastapi import Depends

from connect_ext.schemas import Conversations, Messages

class Report():
    @staticmethod
    def convert_list_jira_info(data,api_token):
        result_list = []
        print(data)
        for notes, ids in data.items():
            new_data = {'ID': ', '.join(ids), 'Notes': notes}
            result_list.append(Report.update_jira_info(new_data,api_token))
        return result_list

    @staticmethod
    def update_jira_info(data,api_token):

        all_ids = data['ID'].split(', ')
        jira_tickets = {}
        jira_statuses = {}
        ids_not_in_jira = []

        for id_str in all_ids:
            id_str = id_str.strip()
            id_match = re.match(r'PR-\d{4}-\d{4}-\d{4}-\d{3}', id_str)

            if not id_match:
                print(f"Invalid ID format: {id_str}")
                continue
            jira_ticket, jira_status = Report.search_in_jira(id_str,api_token)


            if jira_ticket == 'No ticket':
                ids_not_in_jira.append(id_str)
                jira_tickets[id_str] = None
                jira_statuses[id_str] = None
            else:
                jira_tickets[id_str] = jira_ticket
                jira_statuses[id_str] = jira_status


        if ids_not_in_jira:
            # Create a Jira issue for IDs that do not exist in Jira
            logging.debug("IDs not in Jira: %s", ids_not_in_jira)
            created_tickets = Report.create_jira_issue(data['Notes'], ids_not_in_jira,username,api_token)

            if created_tickets:
                # Update jira_tickets and jira_statuses based on created_tickets information
                for ticket_key in created_tickets:
                    for id_str in ids_not_in_jira:
                        jira_tickets[id_str] = ticket_key
                        jira_statuses[id_str] = 'Open'

        # If all IDs exist in Jira, print the ticket number; otherwise, print 'No ticket'
        data['JIRA TICKET'] = [jira_tickets[id_str] for id_str in all_ids] if all(
            ticket != 'No ticket' for ticket in jira_tickets.values()) else ['No ticket']
        data['JIRA STATUS'] = [jira_statuses[id_str] for id_str in all_ids] if all(
            status is not None for status in jira_statuses.values()) else ['N/A']

        print("Final data after Jira update:", data)

        return data

    @staticmethod
    def search_in_jira(pr_id,api_token):
        # Replace this with your actual JIRA API endpoint and authentication method
        jira_url = f"https://jira.int.zone/rest/api/2/search"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        search_word = pr_id

        query = {
            'jql': f'text ~ "{search_word}"'
        }
        try:
            response = requests.post(jira_url, headers=headers, json=query)
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
            issues = response.json()

            if 'issues' in issues and issues['issues']:
                # Assuming that you want to get details from the first issue if there are multiple matches
                issue = issues['issues'][0]
                jira_ticket = issue['key']
                jira_status = issue['fields'].get('status', {}).get('name', '')
                return jira_ticket, jira_status
            else:
                return 'No ticket', 'N/A'
        except requests.exceptions.RequestException as e:
            print("Error occurred while searching issues:", e)
            return 'No ticket', 'N/A'

    @staticmethod
    def create_jira_issue(notes, ids_not_in_jira,api_token):
        jira_url = "https://jira.int.zone/rest/api/2/issue"

        headers = {
             "Authorization": f"Bearer {api_token}",
              "Content-Type": "application/json"
        }

        data = {
            "fields": {
                "summary": "Ticket created by SLA Report Automation",
                "issuetype": {
                    "name": "3rd-line Ticket"
                },
                "duedate": "2024-02-25",
                "project": {
                    "key": "TRITS"
                },
                "description": f"This is being created automatically. The reason: {notes}\nID(s): {', '.join(ids_not_in_jira)}",
            }
        }

        response = requests.post(jira_url, headers=headers, json=data)

        if response.status_code == 201:
            print(f"Issue created successfully for IDs: {', '.join(ids_not_in_jira)}")
            print("Issue Key:", response.json()["key"])
            return [response.json()["key"]]
        else:
            print(f"Failed to create issue for IDs: {', '.join(ids_not_in_jira)}. Status code: {response.status_code}")
            print("Response content:", response.text)
            return [response.json()["key"]]

    @staticmethod
    def calculate_similarity(str1, str2):
        len_max = max(len(str1), len(str2))
        if len_max == 0:
            return 0.0
        distance = Levenshtein.distance(str1, str2)
        similarity = 1.0 - distance / len_max
        return similarity

    @staticmethod
    def generate_excel(data):
        for item in data:
            item['JIRA TICKET'] = ', '.join(item['JIRA TICKET'])
            item['JIRA STATUS'] = ', '.join(item['JIRA STATUS'])

        # Step 2: Convert the dict to a list and create a new row for each ID
        expanded_data = []
        for item in data:
            for i in range(len(item['ID'].split(','))):
                new_item = {
                    'ID': item['ID'].split(',')[i].strip(),
                    'Notes': item['Notes'],
                    'JIRA TICKET': item['JIRA TICKET'].split(',')[i].strip(),
                    'JIRA STATUS': item['JIRA STATUS'].split(',')[i].strip()
                }
                expanded_data.append(new_item)

        # Step 3: Create DataFrame
        df_expanded = pd.DataFrame(expanded_data)

        # Specify the file path for the Excel file
        output_file_path = 'output_grouped.xlsx'

        # Write the grouped DataFrame to an Excel file
        df_expanded.to_excel(output_file_path, sheet_name='SLA Report Automation', index=False)

        print(f"Excel file '{output_file_path}' created successfully.")



