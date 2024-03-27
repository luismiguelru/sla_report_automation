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
import json
from urllib.parse import unquote,quote

from connect.client import ConnectClient, R
from connect.eaas.core.decorators import (
    account_settings_page,
    module_pages,
    router,
    variables,
    web_app,
)
from connect.eaas.core.decorators import unauthorized, guest
from connect.eaas.core.extension import WebApplicationBase
from connect.eaas.core.inject.common import get_call_context, get_config
from connect.eaas.core.inject.models import Context
from connect.eaas.core.inject.synchronous import get_installation, get_installation_client
from fastapi import Depends,Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from connect_ext.application import shared_router

from connect_ext.schemas import Marketplace, Settings, Requests, Conversations, Messages
from connect_ext import report

logging.basicConfig(level=logging.DEBUG)
router.include_router(shared_router)

@variables([
    {
        'name': 'VAR_NAME_1',
        'initial_value': 'VAR_VALUE_1',
        'secure': False,
    },
    {
        'name': 'VAR_NAME_N',
        'initial_value': 'VAR_VALUE_N',
        'secure': True,
    },
])
@web_app(router)
@account_settings_page('SLA Report settings', '/static/settings.html')
@module_pages('Report Generation', '/static/index.html')

class SlaReportAutomationWebApplication(WebApplicationBase):
    @unauthorized()
    @router.get('/test', response_class=HTMLResponse)
    def test_ito(self, request: Request):
        encoded_param1 = request.query_params.get('param1')

        if encoded_param1:
            # If param1 is provided, decode it and process accordingly
            decoded_param1 = json.loads(unquote(encoded_param1))
            html_content = """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>My Wizard hola aqui</title>
                    </head>
                    <body>
                        <p>Somebody help me</p>
                        <h1>Here is some random PR:</h1>
                        <ul>
                    """
            for r in decoded_param1:
                html_content += f"<li>{r['id']}</li>"
                html_content += f"<li>{r['status']}</li>"
                html_content += f"<li>{r['created']}</li>"

            html_content += """
                        </ul>
                    </body>
                    </html>
                """
        else:
            # If param1 is not provided, handle the request accordingly
            html_content = """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>My Wizard hola aqui</title>
                    </head>
                    <body>
                        <p>No parameters provided</p>
                    </body>
                    </html>
                """
        return html_content

    @router.get('/wizardo', response_class=HTMLResponse)
    #injectt config & client & installation
    def my_endpoint_test(self, config: dict = Depends(get_config),
                         client: ConnectClient = Depends(get_installation_client)):
        # api_token = config['API_TOKEN']
        requestardos = client.requests.all().values_list('id', 'status', 'created')

        # Convert requestardos to a list of dictionaries
        requestardos_list = []
        for r in requestardos:
            requestardos_list.append({
                'id': r['id'],
                'status': r['status'],
                'created': r['created'],
            })
        # Convert the list to JSON and URL encode it
        encoded_request = quote(json.dumps(requestardos_list))
        return RedirectResponse(
            url=f'https://srvc-1859-1074-ein-4355-7359-3864.ext.conn.rocks/guest/test?param1={encoded_request}')

    @router.get(
        '/requests/',
        summary='List all available PRs',
        response_model=List[Requests],
    )
    def list_purchase_request(
            self,
            client: ConnectClient = Depends(get_installation_client),
    ):
        return [
            Requests(**requests)
            for requests in client.requests.all().values_list(
                'id', 'status', 'created', 'asset', 'events', 'asset_environment',
            )
        ]

    @router.get(
        '/conversations/',
        summary='List all available conversations',
        response_model=List[Conversations],
    )
    def list_conversation(
            self,
            client: ConnectClient = Depends(get_installation_client),
    ):
        return [
            Conversations(**conversations)
            for conversations in client.conversations.all().values_list(
                'id', 'type', 'topic',
            )

        ]

    @router.get(
        '/conversations/{id}',
        summary='List conversations according specific id',
        response_model=List[Conversations],
    )
    def list_conversation_id(
            self,
            id: str,
            client: ConnectClient = Depends(get_installation_client),
    ):
        return [
            Conversations(**conversations)
            for conversations in client.conversations.filter(instance_id=id).all().values_list(
                'id', 'type', 'topic',
            )

        ]

    @router.post(
        '/generateExcel',
        summary='Generate Excel Report',
    )
    def generate_report(self,
            client: ConnectClient = Depends(get_installation_client),
            config: dict = Depends(get_config),
    ):
        api_token = config['API_TOKEN']
        pr_request_dict_list = []  # Initialize an empty list for dictionaries

        pr_request = client.requests.filter(status='pending').all().values_list('id', 'status',)
        for row in pr_request:
            message = client.conversations[row['id']].messages.filter(type='message').all().values_list(
                'id', 'type', 'text', 'events',
            )
            for message_value in message:
                text_message = message_value['text']
                created_by_name = message_value['events']['created']['by'][
                    'name'] if 'events' in message_value and 'created' in message_value['events'] else None

                if text_message is not None and created_by_name == "Luis Miguel Rodriguez Ugarte":
                    pr_dict = {'ID': row['id'], 'Notes': text_message}
                    pr_request_dict_list.append(pr_dict)
                    break
        # Group dictionaries based on similarity in 'Notes' field
        grouped_dict = defaultdict(list)
        first_common_part = None
        for pr_dict in pr_request_dict_list:
            found_group = False
            similarity_threshold = 0.9  # Adjust the threshold as needed

            for group_notes, group_ids in grouped_dict.items():
                similarity = report.Report.calculate_similarity(pr_dict['Notes'], group_notes)
                if similarity >= similarity_threshold:
                    found_group = True
                    common_part_length = int(min(len(pr_dict['Notes']), len(group_notes)) * similarity)
                    common_part = pr_dict['Notes'][:common_part_length]

                    if first_common_part is None:
                        first_common_part = common_part
                    break
                # If no similar group is found, create a new group
            if found_group and common_part:
                # Append to the existing group with common_part
                if group_notes != first_common_part:  # Check if key needs to be updated
                    grouped_dict[first_common_part] = grouped_dict.pop(group_notes, [])  # Update key to common_part
                grouped_dict[first_common_part].append(pr_dict['ID'])  # Append ID to the group
            else:
                # Create a new group with the common_part
                grouped_dict[pr_dict['Notes']].append(pr_dict['ID'])

        # Use the generated report for Jira updates

        report_generation = report.Report.convert_list_jira_info(grouped_dict,api_token)

        report.Report.generate_excel(report_generation)
        for item in report_generation:
            id_list = item['ID'].split(', ')
            jira_tickets_str = item.get('JIRA TICKET', "")
            jira_tickets = [ticket.strip() for ticket in jira_tickets_str.split(',')] if jira_tickets_str else []

            for id_str in id_list:
                jira_ticket_found = False

                for jira_ticket in jira_tickets:

                    # Replace conversation_id with the actual conversation ID from your data
                    messages = (client.conversations[id_str]
                    .messages.filter(type='message')
                    .all().values_list('id', 'type', 'text', 'events'))

                    for message_value in messages:
                        text_message = message_value['text']

                        if jira_ticket in text_message:
                            jira_ticket_found = True
                            break

                    if jira_ticket_found:
                        break

                if not jira_ticket_found:
                    message_data = {"text": f"We have created a ticket {jira_ticket}"}
                    client.conversations[id_str].messages.create(json=message_data)

        return report_generation

    @router.get(
        '/conversations/{id}/messages',
        summary='List conversations messages according specific id',
        response_model=List[Messages],
    )
    def list_conversation_id_messages(
            self,
            id: str,
            client: ConnectClient = Depends(get_installation_client),
    ):
        return [
            Messages(**conversations)
            for conversations in
            client.conversations[id].messages.filter(type='message').all().values_list(
                'id', 'type', 'text', 'events',
            )
        ]

    @router.get(
        '/marketplaces',
        summary='List all available marketplaces',
        response_model=List[Marketplace],
    )
    def list_marketplaces(
        self,
        client: ConnectClient = Depends(get_installation_client),
    ):
        return [
            Marketplace(**marketplace)
            for marketplace in client.marketplaces.all().values_list(
                'id', 'name', 'description', 'icon',
            )
        ]

    @router.get(
        '/settings',
        summary='Retrive charts settings',
        response_model=Settings,
    )
    def retrieve_settings(
        self,
        installation: dict = Depends(get_installation),
    ):
        return Settings(marketplaces=installation['settings'].get('marketplaces', []))

    @router.post(
        '/settings',
        summary='Save charts settings',
        response_model=Settings,
    )
    def save_settings(
        self,
        settings: Settings,
        context: Context = Depends(get_call_context),
        client: ConnectClient = Depends(get_installation_client),
    ):
        client('devops').installations[context.installation_id].update(
            payload={
                'settings': settings.dict(),
            },
        )
        return settings

    @router.get(
        '/chart',
        summary='Generate chart data',
    )
    def generate_chart_data(
        self,
        installation: dict = Depends(get_installation),
        client: ConnectClient = Depends(get_installation_client),
    ):
        data = {}
        for mp in installation['settings'].get('marketplaces', []):
            active_assets = client('subscriptions').assets.filter(
                R().marketplace.id.eq(mp['id']) & R().status.eq('active'),
            ).count()
            data[mp['id']] = active_assets

        return {
            'type': 'bar',
            'data': {
                'labels': list(data.keys()),
                'datasets': [
                    {
                        'label': 'Subscriptions',
                        'data': list(data.values()),
                    },
                ],
            },
        }
