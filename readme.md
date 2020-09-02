This is a command line utility to backup and compress directories and
upload to google drive.


# requirements


```
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```


# install

before starting you have to enable google drive api follow the description here:

    https://developers.google.com/drive/api/v3/quickstart/python



# usage

```shell
python upload.py --local-path=/home/john/project --drive-path=my-backups --num-backups=2
```

* `--local-path` fully path on  your computer.
* `--drive-path`  name of directory on google drive to put the files.
* `--num-backups` number of backups to keep on google drive.