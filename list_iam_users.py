# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 23:19:17 2020

@author: leagodoy
"""

import boto3
from botocore import exceptions
import pandas as pd


iam = boto3.client('iam')


list_to_export = {"User name": None, "Access key": None, "Status": None, "Access key created": None, "Last used": None, "Console access": None, "MFA": None} #Creating empty dictionary to be exported later as CSV
users_list = []
access_key_list = []
access_key_status = []
access_key_date_created = []
access_key_last_used = []
console_access = []
mfa_list = []
duplicated = False

# List users with the pagination interface
paginator = iam.get_paginator('list_users')

print("Getting users \n")

try:
	for page in paginator.paginate():
		for user in page['Users']:
			users_list.append(user['UserName']) #Adding the users to a list

	list_to_export["User name"] = users_list

	# List access keys through the pagination interface.
	paginator = iam.get_paginator('list_access_keys')

	print("Getting access key information \n")

	for user in users_list:
		#This is to avoid infinit loop when user has 2 access keys
		if duplicated == True:
			duplicated = False
			continue

		for response in paginator.paginate(UserName=user):
			#The user only has 1 access key
			if len(response['AccessKeyMetadata']) == 1:
				access_key_list.append(response['AccessKeyMetadata'][0]['AccessKeyId'])
				access_key_status.append(response['AccessKeyMetadata'][0]['Status'])
				access_key_date_created.append(response['AccessKeyMetadata'][0]['CreateDate'].strftime("%m-%d-%Y %H:%M"))

			#The user has 2 access keys
			elif len(response['AccessKeyMetadata']) == 2:
				index_element = users_list.index(user) #Identifying user's index from the list of users
				users_list.insert(index_element,user) #Duplicating the user in the list of users as it will have 2 access key
				access_key_list.append(response['AccessKeyMetadata'][0]['AccessKeyId'])
				access_key_status.append(response['AccessKeyMetadata'][0]['Status'])
				access_key_date_created.append(response['AccessKeyMetadata'][0]['CreateDate'].strftime("%m-%d-%Y %H:%M")) #Formatting date and time to MM-DD-YYYY HH:MM
				access_key_list.append(response['AccessKeyMetadata'][1]['AccessKeyId'])
				access_key_status.append(response['AccessKeyMetadata'][1]['Status'])
				access_key_date_created.append(response['AccessKeyMetadata'][1]['CreateDate'].strftime("%m-%d-%Y %H:%M")) #Formatting date and time to MM-DD-YYYY HH:MM
				duplicated = True
			
			#The user doesn't have any access key
			else:
				access_key_list.append("N/A")
				access_key_status.append("N/A")
				access_key_date_created.append("N/A")

	list_to_export["Access key"] = access_key_list
	list_to_export["Status"] = access_key_status
	list_to_export["Access key created"] = access_key_date_created

	# Get last use of access key
	for key in access_key_list:
		if key == "N/A":
			access_key_last_used.append("N/A")
		else:
			response = iam.get_access_key_last_used(AccessKeyId=key)
			try:
				access_key_last_used.append(response['AccessKeyLastUsed']['LastUsedDate'].strftime("%m-%d-%Y %H:%M")) #Formatting date and time to MM-DD-YYYY HH:MM
			except KeyError:
				access_key_last_used.append("N/A") #If the key wasn't used, then it won't have a date.

	list_to_export["Last used"] = access_key_last_used

	print("Getting console access \n")

	for user in users_list:
		try:
			response = iam.get_login_profile(UserName=user)
			if response:
				console_access.append("Yes")
		except iam.exceptions.NoSuchEntityException:
			console_access.append("No")

	list_to_export["Console access"] = console_access

	print("Getting MFA information \n")

	for user in users_list:
		index_element = users_list.index(user)
		if console_access[index_element] == "Yes":
			response = iam.list_mfa_devices(UserName=user)
			if response['MFADevices'] != [] and "mfa" in response['MFADevices'][0]['SerialNumber']:
				mfa_list.append("Enabled")
			else:
				mfa_list.append("Disabled")
		else:
			mfa_list.append("N/A")

	list_to_export["MFA"] = mfa_list

	print("Exporting report \n")

	#Converting the dictionary to a Pandas dataframe
	df = pd.DataFrame(list_to_export, columns = ['User name', 'Access key', 'Status', 'Access key created', 'Last used', 'Console access', 'MFA']) 
	df.to_csv('IAM_users_list.csv',index_label='Index')
	print("CSV file exported, now removing index column \n")
	df = pd.read_csv('IAM_users_list.csv')
	df.drop('Index', axis=1, inplace=True) #Removing index column
	df.to_csv('IAM_users_list.csv', index=False)

except exceptions.NoCredentialsError:
	print("ERROR! \n Unable to locate AWS credentials")

except exceptions.ClientError:
	print("ERROR! \n Invalid client token ID, kindly verify your access key. Is your access key active? Do you have permissions for IAM?")

