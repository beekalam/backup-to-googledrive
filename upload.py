from __future__ import print_function
import pickle
import os
import getopt
import os.path
import sys
import time
import zipfile
import shutil
from datetime import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

DIRECTORY_TYPE='application/vnd.google-apps.folder'
ZIP_MIME = "application/zip"

SCOPES = ['https://www.googleapis.com/auth/drive']
def drive_service():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    return service

def search(service, query):
    # search for the file
    result = []
    page_token = None
    while True:
        response = service.files().list(q=query,
                                        spaces="drive",
                                        fields="nextPageToken, files(id, name, mimeType)",
                                        pageToken=page_token).execute()
        # iterate over filtered files
        for file in response.get("files", []):
            result.append((file["id"], file["name"], file["mimeType"]))
        page_token = response.get('nextPageToken', None)
        if not page_token:
            # no more files
            break
    return result

def get_directory(service,directory_name):
    return search(service,query="mimeType='{}' and name='{}'".format(DIRECTORY_TYPE,directory_name))

def create_folder(service,directory_name):
    file_metadata = {
        'name': directory_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    file = service.files().create(body=file_metadata,
                                        fields='id').execute()
    print ('Folder ID: %s' % file.get('id'))
    return file

def create_folder_if_does_not_exist(service, directory_name):
    res = get_directory(service,directory_name)
    if res:
        return res[0][0]
    else:
        file = create_folder(service, directory_name)
        return file.get('id')
    return None

def dir_zip_listing(service,dir_id):
    query="mimeType='{}' and parents='{}'".format(ZIP_MIME,dir_id)
    dir_files = search(service,query)
    return dir_files

def upload_file(service,file_path,mimetype,dir_id=None):
	file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [dir_id]
    }

	media = MediaFileUpload(file_path, mimetype=mimetype,resumable=True)
	file = service.files().create(body=file_metadata,
	                                    media_body=media,
	                                    fields='id').execute()
	print ('File ID: %s' % file.get('id'))

def delete_file(service, file_id):
    res = service.files().delete(fileId=file_id).execute()
    return res
def clean_dir(service,dir_id, max_num_backups_to_keep):
    dir_files = dir_zip_listing(service, dir_id)
    # sort by file name
    dir_files.sort(key= lambda x: x[1])
    # _ = [print(i) for i in dir_files]
    if len(dir_files) > max_num_backups_to_keep:
        to_remove_count = len(dir_files) - max_num_backups_to_keep
        for i in range(to_remove_count):
            print("going to delete {}".format(dir_files[i][0]))
            delete_file(service, dir_files[i][0])

def unix_ts():
    return int(time.time())

def today_str():
	today = datetime.now()
	return today.strftime("%y-%m-%d-%H-%M-%S")

def backup(service,gdrive_dir,local_path,num_backups,local_backup_path):
    dir_id = create_folder_if_does_not_exist(service,gdrive_dir)

    # backup_name = os.path.basename(path) + "_" + today_str()
    shutil.make_archive(local_backup_path,'zip', local_path)
    upload_file(service = service,
                file_path = local_backup_path + ".zip",
                mimetype= ZIP_MIME,
                dir_id=dir_id)
    os.remove(local_backup_path + ".zip")
    clean_dir(service,dir_id,num_backups)

def pars_args(argv):
   current_file = os.path.basename(__file__)
   local_path, drive_path, num_backups = None, None, None
   help = "{} --local-path=<some_local_path> --drive-path=<gdrive_folder> --num-backups=<number_of_backups_to_keep".format(current_file)
   try:
       opts, args = getopt.getopt(argv,"hl:d:n:",["local-path=","drive-path=","num-backups="])
   except getopt.GetoptError:
       print (help)
       sys.exit(2)
   for opt,arg in opts:
       if opt == '-h':
           print (help)
           sys.exit(1)
       elif opt in ('-l','--local-path'):
           local_path = arg
       elif opt in ('-d','--drive-path'):
           drive_path = arg
       elif opt in ('-n','--num-backups'):
           num_backups = 3
   if local_path is None or drive_path is None or num_backups is None:
       print("all params must have have value")
       print(help)
       sys.exit(1)
   return [local_path, drive_path,num_backups]

def create_backup_folders_if_not_exists(name='__gdrive_bakcups__'):
   path = os.path.join("/","tmp", name)
   print (path)
   if os.path.exists(path):
       return path
   else: #this is optional if you want to create a directory if doesn't exist.
      os.mkdir(path)
   return path

if __name__ == '__main__':
    local_path,drive_path, num_backups = pars_args(sys.argv[1:])
    print(
        "creating backups from {} to gdrive folder: {} with number of backups: {}".format(
            local_path,drive_path,num_backups))
    local_backup_folder = create_backup_folders_if_not_exists()

    backup_name = str(unix_ts())
    local_backup_path = os.path.join(local_backup_folder ,backup_name)

    service = drive_service()
    backup(service,drive_path, local_path, num_backups,local_backup_path)

